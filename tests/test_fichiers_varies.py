# -*- coding: utf-8 -*-
"""Banc d'essai : l'extension doit fonctionner sur des tableaux variés (tests/fixtures/).
LibreOffice headless sur le port 2002, puis : python3 tests/test_fichiers_varies.py"""
import os, sys, shutil, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "extension", "pythonpath"))
import test_actions as t  # noqa: E402
from calc_ia import actions, suggest  # noqa: E402

FIX = os.path.join(HERE, "fixtures")
check = t.check


def open_copy(desktop, name):
    tmp = os.path.join(tempfile.mkdtemp(), name)
    shutil.copy(os.path.join(FIX, name) if name != "contacts-fictifs.ods"
                else os.path.join(HERE, "..", "exemples", name), tmp)
    doc = t.load(desktop, tmp)
    return doc, doc.Sheets.getByIndex(0)


def show(name, sheet):
    print("\n=== %s : %s" % (name, suggest.describe(sheet)))
    ideas = suggest.suggestions(sheet)
    for i in ideas:
        print("  idée : %s (%s)" % (i["titre"], i["detail"]))
    return ideas


def kinds(ideas):
    return [i["choice"]["action"] for i in ideas]


def main():
    d = t.connect()

    doc, s = open_copy(d, "contacts-fictifs.ods")
    ideas = show("contacts", s)
    check(kinds(ideas) == ["normaliser_texte", "formater_telephone", "supprimer_doublons", "tableau_croise", "graphique"],
          "contacts : villes, téléphones, doublons, tableau croisé, graphique")
    check(any("Ville" in i["titre"] for i in ideas), "contacts : la colonne Ville est repérée")
    check(not any("Email" in i["titre"] and i["choice"]["action"] == "normaliser_texte" for i in ideas),
          "contacts : on ne propose pas de « mettre en forme » les emails")
    ville = [i for i in ideas if "Ville" in i["titre"]][0]
    plan = actions.prepare(doc, s, ville["choice"]); plan.apply(doc)
    villes = set(actions.Table(s).column("Ville"))
    check(len(villes) == 8, "contacts : 8 villes après harmonisation (%s)" % sorted(villes))
    doc.close(True)

    doc, s = open_copy(d, "budget.ods")
    tb = actions.Table(s)
    check(tb.headers == ["Date", "Catégorie", "Libellé", "Montant"], "budget : en-têtes trouvés sous le titre (%s)" % tb.headers)
    check("Date" in tb.date_cols, "budget : la colonne Date est reconnue comme des dates")
    ideas = show("budget", s)
    check("normaliser_texte" in kinds(ideas), "budget : catégories mal écrites repérées")
    check(any(i["choice"].get("colonne_valeurs") == "Montant" for i in ideas), "budget : total des montants par catégorie")
    p = actions.prepare(doc, s, {"action": "tableau_croise", "colonne": "Catégorie", "colonne_valeurs": "Montant", "operation": "somme"})
    check(any("saisies comme du texte" in x for x in p.details), "budget : avertit des montants saisis en texte")
    try:
        actions.prepare(doc, s, {"action": "tableau_croise", "colonne": "Catégorie", "colonne_valeurs": "Date", "operation": "somme"})
        check(False, "budget : refus de sommer des dates")
    except actions.ActionError:
        check(True, "budget : refus de sommer des dates")
    actions.prepare(doc, s, {"action": "trier", "colonne": "Montant", "ordre": "decroissant"}).apply(doc)
    m = [v for v in actions.Table(s).column("Montant") if isinstance(v, float)]
    check(m == sorted(m, reverse=True), "budget : tri d'un tableau qui ne commence pas en A1")
    check(s.getCellByPosition(0, 0).getString() == "Budget du foyer 2026", "budget : le titre au-dessus est intact")
    doc.close(True)

    doc, s = open_copy(d, "inventaire.ods")
    ideas = show("inventaire", s)
    check(not any("Référence" in i["titre"] for i in ideas), "inventaire : les codes article ne sont pas touchés")
    check(any("Fournisseur" in i["titre"] for i in ideas), "inventaire : fournisseurs mal écrits repérés")
    p = actions.prepare(doc, s, {"action": "normaliser_texte", "colonne": "Fournisseur", "casse": ""}); p.apply(doc)
    f = set(actions.Table(s).column("Fournisseur"))
    check(f == {"Dupont SA", "Martin & Fils", "Nordis", "Alpha Pro"}, "inventaire : « Dupont SA » garde ses majuscules (%s)" % sorted(f))
    doc.close(True)

    doc, s = open_copy(d, "adherents.ods")
    ideas = show("adhérents", s)
    check("formater_telephone" in kinds(ideas), "adhérents : téléphones +33 repérés")
    check("supprimer_doublons" in kinds(ideas), "adhérents : doublons de courriel repérés")
    actions.prepare(doc, s, {"action": "formater_telephone", "colonne": "Tél portable"}).apply(doc)
    import re
    tels = [v for v in actions.Table(s).column("Tél portable") if v != ""]
    check(all(re.fullmatch(r"0\d( \d\d){4}", v) for v in tels), "adhérents : +33 converti en 06…")
    doc.close(True)

    doc, s = open_copy(d, "ventes-5000.ods")
    t0 = time.time()
    ideas = show("ventes", s)
    p = actions.prepare(doc, s, {"action": "tableau_croise", "colonne": "Région", "colonne_valeurs": "CA", "operation": "somme"})
    p.apply(doc)
    dt = time.time() - t0
    check(dt < 15, "ventes : 5 000 lignes analysées et tableau croisé en %.1f s" % dt)
    doc.close(True)

    doc, s = open_copy(d, "sans-titre.ods")
    tb = actions.Table(s)
    check(tb.headers[1].startswith("Colonne"), "sans titre : la colonne vide reçoit un nom (%s)" % tb.headers)
    show("sans titre", s)
    doc.close(True)

    doc, s = open_copy(d, "english.ods")
    ideas = show("english", s)
    check(any("City" in i["titre"] for i in ideas), "anglais : City repérée")
    check(any(i["choice"]["action"] == "supprimer_doublons" for i in ideas), "anglais : doublons d'email repérés")
    doc.close(True)

    doc, s = open_copy(d, "realiste.ods")
    tb = actions.Table(s)
    check(tb.headers == ["Client", "Ville", "Email", "HT", "TTC"], "réaliste : en-têtes sous un titre fusionné (%s)" % tb.headers)
    ideas = show("réaliste", s)
    p = actions.prepare(doc, s, {"action": "normaliser_texte", "colonne": "Ville", "casse": ""})
    check(any("formule" in x for x in p.details), "réaliste : l'aperçu signale la formule qui ne sera pas modifiée")
    p.apply(doc)
    check(s.getCellByPosition(1, 5).getFormula().startswith("="), "réaliste : la formule de la colonne Ville est intacte")
    p = actions.prepare(doc, s, {"action": "supprimer_doublons", "colonne": "Email"})
    p.apply(doc)
    check(len([r for r in actions.Table(s).rows if r[2] != ""]) == 30, "réaliste : 30 clients après dédoublonnage")
    check(s.getCellByPosition(7, 3).getString() == "note 0" and s.getCellByPosition(7, 42).getString() == "note 39",
          "réaliste : le second tableau à droite n'a pas bougé")
    ttc = s.getCellByPosition(4, 3)
    check(ttc.getFormula().startswith("=D") and abs(ttc.getValue() - s.getCellByPosition(3, 3).getValue() * 1.2) < 1e-6,
          "réaliste : les formules TTC restent justes après suppression")
    try:
        actions.prepare(doc, doc.Sheets.getByName("Protégée"), {"action": "trier", "colonne": "Ville", "ordre": ""})
        check(False, "réaliste : feuille protégée refusée")
    except actions.ActionError as e:
        check("protégée" in str(e), "réaliste : feuille protégée refusée proprement")
    doc.close(True)

    print("\n%s" % ("TOUS LES TESTS PASSENT" if not check.failed else "%d échec(s)" % check.failed))
    sys.exit(1 if check.failed else 0)


if __name__ == "__main__":
    main()
