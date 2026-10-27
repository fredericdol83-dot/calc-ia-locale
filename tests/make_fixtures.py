# -*- coding: utf-8 -*-
"""Fabrique les fichiers d'essai variés dans tests/fixtures/ (via LibreOffice headless).
Données entièrement inventées. python3 tests/make_fixtures.py"""
import os, random, datetime as dt
import uno
from test_actions import connect

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")
random.seed(7)


def new_doc(desktop):
    pv = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    pv.Name, pv.Value = "Hidden", True
    return desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (pv,))


def put(sheet, col, row, rows):
    """rows : liste de listes ; un datetime.date devient une vraie date Calc."""
    for r, line in enumerate(rows):
        for c, v in enumerate(line):
            cell = sheet.getCellByPosition(col + c, row + r)
            if isinstance(v, dt.date):
                cell.setValue((v - dt.date(1899, 12, 30)).days)
                cell.NumberFormat = 37  # format date court
            elif isinstance(v, (int, float)):
                cell.setValue(v)
            elif v is not None:
                cell.setString(v)


def save(doc, name):
    path = os.path.join(OUT, name)
    pv = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    pv.Name, pv.Value = "FilterName", "calc8"
    doc.storeToURL(uno.systemPathToFileUrl(path), (pv,))
    doc.close(True)
    print("créé", name)


def main():
    os.makedirs(OUT, exist_ok=True)
    d = connect()

    # 1. Budget : titre au-dessus du tableau (qui commence en B3), vraies dates,
    #    catégories mal écrites, quelques montants saisis comme du texte
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    put(s, 0, 0, [["Budget du foyer 2026"]])
    cats = ["Alimentation", "Transport", "Logement", "Loisirs", "Santé"]
    rows = [["Date", "Catégorie", "Libellé", "Montant"]]
    for i in range(120):
        c = random.choice(cats)
        c = random.choice([c, c, c.upper(), " " + c.lower()])
        m = round(random.uniform(5, 300), 2)
        rows.append([dt.date(2026, 1, 1) + dt.timedelta(days=random.randint(0, 290)), c,
                     "Dépense %d" % i, m if i % 15 else ("%.2f" % m).replace(".", ",")])
    put(s, 1, 2, rows)
    save(doc, "budget.ods")

    # 2. Inventaire : références en codes (à ne jamais « mettre en forme »), fournisseurs mal écrits
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    four = ["Dupont SA", "Martin & Fils", "Nordis", "Alpha Pro"]
    rows = [["Référence", "Produit", "Stock", "Prix unitaire", "Fournisseur"]]
    for i in range(80):
        f = random.choice(four)
        rows.append(["AB-%04d" % i, "Article %d" % i, random.randint(0, 500),
                     round(random.uniform(1, 90), 2), random.choice([f, f, f.lower(), f + " "])])
    put(s, 0, 0, rows)
    save(doc, "inventaire.ods")

    # 3. Adhérents : téléphones +33, emails en double, lignes vides au milieu
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    rows = [["Nom", "Prénom", "Courriel", "Tél portable", "Cotisation"]]
    people = [("Durand", "Anne"), ("Petit", "Marc"), ("Roux", "Lina"), ("Blanc", "Omar"), ("Faure", "Zoé")]
    for i in range(60):
        n, p = random.choice(people)
        tel = "06%08d" % random.randint(0, 99999999)
        tel = random.choice([tel, "+33 " + tel[1:], ".".join(tel[k:k+2] for k in range(0, 10, 2))])
        rows.append([n, p, "%s.%s%d@exemple.org" % (p.lower(), n.lower(), i % 40), tel, random.choice([20, 35, 50])])
        if i in (10, 30):
            rows.append([None] * 5)
    put(s, 0, 0, rows)
    save(doc, "adherents.ods")

    # 4. Ventes : 5 000 lignes, pour la rapidité
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    regs = ["Nord", "Sud", "Est", "Ouest", "Centre"]
    rows = [["Région", "Vendeur", "Mois", "CA"]]
    for i in range(5000):
        rows.append([random.choice(regs), "Vendeur %d" % random.randint(1, 40),
                     random.choice(["janv.", "févr.", "mars", "avr."]), random.randint(100, 9000)])
    sheet_rng = s.getCellRangeByPosition(0, 0, 3, 5000)
    sheet_rng.setDataArray(tuple(tuple(r) for r in rows))
    save(doc, "ventes-5000.ods")

    # 5. Colonnes sans titre
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    rows = [["Ville", "", "Montant"]]
    for i in range(30):
        rows.append([random.choice(["Lyon", "LYON", "Lille"]), "x%d" % i, random.randint(10, 99)])
    put(s, 0, 0, rows)
    save(doc, "sans-titre.ods")

    # 7. Fichier réaliste : titre fusionné, formules, second tableau à droite, filtre, feuille protégée
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    put(s, 0, 0, [["Suivi des commandes"]])
    s.getCellRangeByName("A1:E1").merge(True)
    rows = [["Client", "Ville", "Email", "HT", "TTC"]]
    for i in range(40):
        v = random.choice(["Lyon", "LYON", "Lille", " lille "])
        rows.append(["Client %d" % (i % 30), v, "c%d@exemple.fr" % (i % 30), random.randint(50, 900), None])
    put(s, 0, 2, rows)
    for r in range(3, 43):
        s.getCellByPosition(4, r).setFormula("=D%d*1.2" % (r + 1))   # TTC calculé
    s.getCellByPosition(1, 5).setFormula('=PROPER("lyon")')          # une ville calculée par formule
    put(s, 7, 2, [["Notes", "Valeur"]] + [["note %d" % i, i] for i in range(40)])  # second tableau à droite
    rng = s.getCellRangeByName("A3:E43")
    fd = rng.createFilterDescriptor(True)
    rng.filter(fd)  # filtre automatique vide sur l'en-tête
    doc.Sheets.insertNewByName("Protégée", 1)
    p2 = doc.Sheets.getByName("Protégée")
    put(p2, 0, 0, [["Ville", "Montant"], ["Lyon", 1], ["LYON", 2]])
    p2.protect("")
    save(doc, "realiste.ods")

    # 6. En-têtes en anglais
    doc = new_doc(d); s = doc.Sheets.getByIndex(0)
    rows = [["Customer", "Email", "City", "Amount"]]
    for i in range(50):
        c = random.choice(["London", "Paris", "Berlin"])
        rows.append(["Client %d" % (i % 35), "client%d@example.com" % (i % 35),
                     random.choice([c, c.upper()]), random.randint(100, 5000)])
    put(s, 0, 0, rows)
    save(doc, "english.ods")


if __name__ == "__main__":
    main()
