# -*- coding: utf-8 -*-
"""Idées d'actions repérées dans le tableau, calculées sur l'ordinateur, sans IA.

Les colonnes sont reconnues par leur contenu (adresses mail, téléphones, nombres,
dates, texte répétitif), pas par leur nom : ça marche sur n'importe quel tableau."""
import re

from calc_ia import actions

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
PHONE_TEXT = re.compile(r"^\+?[\d .\-()]{9,18}$")
SKIP_NUM_NAMES = re.compile(r"code|post|\bcp\b|zip|\bid\b|réf|ref|année|year|num|n°|siret|siren|tél|tel", re.I)
PERSON_NAMES = re.compile(r"^(nom|prénom|prenom|name|first name|last name|libellé|libelle|description|"
                          r"commentaire|produit|article|client|customer)\b", re.I)
NON_ADDITIVE = re.compile(r"unitaire|unit|taux|rate|%|moyenne|average|âge|age\b", re.I)
PREFER_NUM_NAMES = re.compile(r"montant|prix|total|\bca\b|chiffre|amount|€|cotisation|coût|cout|budget|"
                              r"valeur|price|sales|recette|dépense|depense", re.I)


def profile(table, name):
    vals = [v for v in table.column(name) if v != ""]
    n = len(vals)
    p = {"name": name, "n": n, "kind": "vide"}
    if not n:
        return p
    texts = [v for v in vals if isinstance(v, str)]
    emails = sum(1 for v in texts if EMAIL.match(v.strip()))
    phones = sum(1 for v in texts if PHONE_TEXT.match(v.strip()) and actions._phone(v) is not None)
    numbers = sum(1 for v in vals if isinstance(v, float)) + \
        sum(1 for v in texts if actions.to_number(v) is not None)
    if emails >= 0.6 * n:
        p["kind"] = "email"
    elif phones >= 0.6 * n:
        p["kind"] = "telephone"
    elif name in table.date_cols:
        p["kind"] = "date"
    elif numbers >= 0.8 * n:
        p["kind"] = "nombre"
    else:
        p["kind"] = "texte"
        groups = {}
        for v in texts:
            groups.setdefault(re.sub(r"\s+", " ", v.strip()).lower(), set()).add(v)
        p["groupes"] = len(groups)
        p["repetitif"] = len(groups) <= max(30, 0.3 * n) and len(groups) < n
        # cellules qui ne sont pas écrites comme la variante majoritaire de leur groupe
        majority = actions._majority_map(texts)
        p["mal_ecrites"] = sum(1 for v in texts if majority.get(re.sub(r"\s+", " ", v.strip()).lower()) != v)
    return p


def _formats(values):
    return {re.sub(r"\d", "9", v.strip()) for v in values if isinstance(v, str) and v.strip()}


def suggestions(sheet, limit=5):
    """Liste de dict : titre, detail, choice (action prête à préparer, sans passer par le modèle)."""
    table = actions.Table(sheet)
    if not table.rows:
        return []
    profs = [profile(table, h) for h in table.headers]
    harm, phones, dups, pivots = [], [], [], []

    for p in sorted(profs, key=lambda p: -p.get("mal_ecrites", 0)):
        if p["kind"] == "texte" and p.get("repetitif") and p.get("mal_ecrites"):
            harm.append({"titre": "Harmoniser l'écriture de « %s »" % p["name"],
                        "detail": "%d valeur(s) écrites différemment (majuscules, espaces)" % p["mal_ecrites"],
                        "choice": {"action": "normaliser_texte", "colonne": p["name"], "casse": ""}})

    for p in profs:
        if p["kind"] == "telephone":
            fmts = _formats(table.column(p["name"]))
            if len(fmts) > 1:
                phones.append({"titre": "Harmoniser les numéros de « %s »" % p["name"],
                            "detail": "%d formats différents, mise au format 06 12 34 56 78" % len(fmts),
                            "choice": {"action": "formater_telephone", "colonne": p["name"]}})

    for p in profs:
        if p["kind"] == "email":
            plan = actions.prepare_supprimer_doublons(table, p["name"])
            if plan.changes:
                dups.append({"titre": "Supprimer les doublons sur « %s »" % p["name"],
                            "detail": "%d ligne(s) en double" % plan.changes,
                            "choice": {"action": "supprimer_doublons", "colonne": p["name"]}})
            break

    cats = [p for p in profs if p["kind"] == "texte" and 2 <= p.get("groupes", 0) <= 30 and p.get("repetitif")
            and not PERSON_NAMES.search(p["name"])]
    cats.sort(key=lambda p: p["groupes"])  # les catégories les plus larges (secteur, région) d'abord
    nums = [p for p in profs if p["kind"] == "nombre" and not SKIP_NUM_NAMES.search(p["name"])]
    nums.sort(key=lambda p: (bool(NON_ADDITIVE.search(p["name"])), not PREFER_NUM_NAMES.search(p["name"])))
    if cats and nums:
        c, v = cats[0], nums[0]
        pivots.append({"titre": "Graphique de « %s » par « %s »" % (v["name"], c["name"]),
                       "detail": "Graphique en barres dans une nouvelle feuille",
                       "choice": {"action": "graphique", "colonne": c["name"], "colonne_valeurs": v["name"],
                                  "type_graphique": "barres", "operation": "somme"}})
        pivots.insert(0, {"titre": "Total de « %s » par « %s »" % (v["name"], c["name"]),
                    "detail": "Tableau croisé dynamique dans une nouvelle feuille",
                    "choice": {"action": "tableau_croise", "colonne": c["name"],
                               "colonne_valeurs": v["name"], "operation": "somme"}})
    elif cats:
        c = cats[0]
        pivots.append({"titre": "Nombre de lignes par « %s »" % c["name"],
                    "detail": "Tableau croisé dynamique dans une nouvelle feuille",
                    "choice": {"action": "tableau_croise", "colonne": c["name"], "operation": "nombre"}})
    for i in harm + phones + dups:
        i["groupe"] = "Nettoyer"
    for i in pivots:
        i["groupe"] = "Analyser"
    # jusqu'à 3 idées de nettoyage (une de chaque sorte d'abord), puis 2 d'analyse
    clean = (harm[:1] + phones[:1] + dups[:1] + harm[1:] + phones[1:])[:3]
    return (clean + pivots[:2])[:limit]


def capabilities(sheet):
    """Ce que l'outil sait faire, avec des exemples construits sur les colonnes du tableau ouvert."""
    try:
        t = actions.Table(sheet)
        profs = [profile(t, h) for h in t.headers]
    except Exception:
        profs = []
    def first(kind, default):
        for p in profs:
            if p["kind"] == kind:
                return p["name"]
        return default
    texte = first("texte", "Ville")
    nombre = next((p["name"] for p in profs if p["kind"] == "nombre" and not SKIP_NUM_NAMES.search(p["name"])), "Montant")
    email = first("email", texte)
    tel = first("telephone", "Téléphone")
    return {
        "Nettoyer": [
            ("Harmoniser l'écriture d'une colonne", "uniformise la colonne %s" % texte),
            ("Mettre en majuscules ou minuscules", "mets la colonne %s en majuscules" % texte),
            ("Formater des téléphones français", "mets la colonne %s au format 06 12 34 56 78" % tel),
            ("Supprimer les doublons", "supprime les doublons sur la colonne %s" % email),
            ("Trier le tableau", "trie par %s du plus grand au plus petit" % nombre),
        ],
        "Analyser": [
            ("Tableau croisé (total, moyenne, nombre)", "total de %s par %s" % (nombre, texte)),
            ("Graphique en barres, courbe ou camembert", "camembert de %s par %s" % (nombre, texte)),
        ],
        "Pas encore": "rédiger ou traduire du texte, écrire des formules, fusionner des fichiers, "
                      "envoyer des mails. L'assistant le dira si votre demande sort de ces actions.",
    }


def describe(sheet):
    t = actions.Table(sheet)
    n = sum(1 for r in t.rows if any(v != "" for v in r))
    return "%s · %d lignes · %d colonnes" % (sheet.getName(), n, len(t.headers))
