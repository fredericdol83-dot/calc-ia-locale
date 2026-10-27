# -*- coding: utf-8 -*-
"""Tests sans interface : lancer d'abord
  soffice --headless --accept="socket,host=localhost,port=2002;urp;"
puis : python3 tests/test_actions.py
Vérifie les actions sur exemples/contacts-fictifs.ods (aucun modèle d'IA nécessaire)."""
import os, sys, shutil, tempfile, time
import uno

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "extension", "pythonpath"))
from calc_ia import actions  # noqa: E402

EXPECTED_TOTALS = {"Bordeaux": 332200, "Lille": 230600, "Lyon": 321300, "Marseille": 272500,
                   "Nantes": 165300, "Paris": 193700, "Rennes": 270700, "Toulouse": 363200}


def connect():
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(20):
        try:
            ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
            return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        except Exception:
            time.sleep(1)
    raise SystemExit("LibreOffice headless introuvable sur le port 2002")


def load(desktop, path):
    pv = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    pv.Name, pv.Value = "Hidden", True
    return desktop.loadComponentFromURL(uno.systemPathToFileUrl(path), "_blank", 0, (pv,))


def check(cond, msg):
    print(("OK    " if cond else "ÉCHEC ") + msg)
    if not cond:
        check.failed += 1
check.failed = 0


def main():
    desktop = connect()
    tmp = os.path.join(tempfile.mkdtemp(), "contacts.ods")
    shutil.copy(os.path.join(HERE, "..", "exemples", "contacts-fictifs.ods"), tmp)
    doc = load(desktop, tmp)
    sheet = doc.getSheets().getByIndex(0)

    def run(choice):
        plan = actions.prepare(doc, sheet, choice)
        print("\n> " + plan.title)
        for d in plan.details:
            print("  " + d)
        plan.apply(doc)
        return plan

    n0 = len(actions.Table(sheet).rows)
    check(n0 == 305, "305 lignes au départ (%d)" % n0)

    # annulation : une action = un seul Ctrl+Z
    run({"action": "normaliser_texte", "colonne": "Ville", "casse": "premiere_lettre_majuscule"})
    um = doc.getUndoManager()
    check(um.isUndoPossible(), "annulation possible après une action")
    um.undo()
    villes = actions.Table(sheet).column("Ville")
    check(any(v != v.strip() or v.isupper() for v in villes), "Ctrl+Z restaure les villes d'origine")

    run({"action": "normaliser_texte", "colonne": "Ville", "casse": "premiere_lettre_majuscule"})
    villes = set(actions.Table(sheet).column("Ville"))
    check(villes == set(EXPECTED_TOTALS), "8 villes propres : %s" % sorted(villes))

    run({"action": "formater_telephone", "colonne": "Téléphone"})
    import re
    tels = actions.Table(sheet).column("Téléphone")
    check(all(re.fullmatch(r"0\d( \d\d){4}", t) for t in tels), "tous les téléphones au format 06 12 34 56 78")

    run({"action": "supprimer_doublons", "colonne": "Email"})
    n1 = len(actions.Table(sheet).rows)
    check(n1 == 201, "201 contacts après dédoublonnage (%d)" % n1)

    plan = actions.prepare(doc, sheet, {"action": "tableau_croise", "colonne": "Ville",
                                        "colonne_valeurs": "Montant devis (€)", "operation": "somme"})
    got = {g: int(v) for g, v in actions._aggregate(actions.Table(sheet), "Ville", "Montant devis (€)", "somme")}
    check(got == EXPECTED_TOTALS, "totaux par ville conformes au protocole")
    plan.apply(doc)
    tcd = doc.getSheets().getByName("TCD Ville")
    out = tcd.getDataPilotTables().getByIndex(0).getOutputRange()
    data = doc.getSheets().getByIndex(out.Sheet).getCellRangeByPosition(
        out.StartColumn, out.StartRow, out.EndColumn, out.EndRow).getDataArray()
    print("  sortie TCD :", data[:3], "...", data[-1])
    pv = {r[0]: r[1] for r in data if r[0] in EXPECTED_TOTALS}
    check({k: int(v) for k, v in pv.items()} == EXPECTED_TOTALS, "le TCD LibreOffice donne les mêmes totaux")

    sheet = doc.getSheets().getByIndex(0)
    run({"action": "graphique", "colonne": "Ville", "colonne_valeurs": "Montant devis (€)",
         "type_graphique": "barres", "operation": "somme"})
    g = doc.getSheets().getByName("Graphique Ville")
    check(g.getCharts().getCount() == 1, "graphique créé dans la feuille « Graphique Ville »")

    run({"action": "graphique", "colonne": "Secteur", "colonne_valeurs": "", "type_graphique": "camembert",
         "operation": "nombre"})
    check(doc.getSheets().hasByName("Graphique Secteur"), "camembert du nombre de contacts par secteur")

    run({"action": "trier", "colonne": "Montant devis (€)", "ordre": "decroissant"})
    m = [v for v in actions.Table(sheet).column("Montant devis (€)") if v != ""]
    check(m == sorted(m, reverse=True), "tri décroissant des montants")

    for bad in ({"action": "aucune", "colonne": ""}, {"action": "trier", "colonne": ""},
                {"action": "tableau_croise", "colonne": "Inconnue", "colonne_valeurs": "", "operation": "nombre"}):
        try:
            actions.prepare(doc, sheet, bad)
            check(False, "refus attendu pour %s" % bad)
        except actions.ActionError as e:
            check(True, "refus clair : %s" % str(e).splitlines()[0])

    p = actions.prepare(doc, sheet, {"action": "tableau_croise", "colonne": "Ville", "colonne_valeurs": "Email", "operation": "somme"})
    check("je compte donc les lignes" in p.details[0], "somme d'une colonne de texte : on compte et on l'explique")

    doc.close(True)
    print("\n%s" % ("TOUS LES TESTS PASSENT" if not check.failed else "%d échec(s)" % check.failed))
    sys.exit(1 if check.failed else 0)


if __name__ == "__main__":
    main()
