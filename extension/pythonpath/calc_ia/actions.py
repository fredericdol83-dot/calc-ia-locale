# -*- coding: utf-8 -*-
"""Actions de tableur exécutées par l'extension, jamais par le modèle.

Chaque action se fait en deux temps :
  1. prepare_*() lit la feuille et renvoie un Plan (texte d'aperçu + fonction apply) ;
  2. Plan.apply() modifie le document, dans un seul pas d'annulation (Ctrl+Z).
Le modèle d'IA se contente de choisir l'action et ses paramètres.
"""
import re
import uno

# ---------------------------------------------------------------------------
# Lecture de la feuille
# ---------------------------------------------------------------------------

def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


class Table:
    """Zone utilisée de la feuille, en-têtes sur la première ligne."""

    def __init__(self, sheet):
        self.sheet = sheet
        cur = sheet.createCursor()
        cur.gotoStartOfUsedArea(False)
        cur.gotoEndOfUsedArea(True)
        a = cur.getRangeAddress()
        self.c0, self.r0, self.c1, self.r1 = a.StartColumn, a.StartRow, a.EndColumn, a.EndRow
        self.range = sheet.getCellRangeByPosition(self.c0, self.r0, self.c1, self.r1)
        data = self.range.getDataArray()
        raw = [str(v).strip() if v != "" else "" for v in data[0]]
        self.headers = []
        for i, h in enumerate(raw):
            name = h or "Colonne " + col_letter(self.c0 + i)
            while name in self.headers:
                name += " (bis)"
            self.headers.append(name)
        self.rows = [list(r) for r in data[1:]]

    def idx(self, name):
        if name not in self.headers:
            raise ActionError("La colonne « %s » n'existe pas dans ce tableau." % name)
        return self.headers.index(name)

    def column(self, name):
        i = self.idx(name)
        return [r[i] for r in self.rows]


class ActionError(Exception):
    pass


class Plan:
    def __init__(self, title, details, apply_fn, changes=0):
        self.title = title          # une phrase : ce qui va être fait
        self.details = details      # lignes d'aperçu
        self._apply = apply_fn
        self.changes = changes      # 0 = rien à faire

    def apply(self, doc):
        um = doc.getUndoManager()
        um.enterUndoContext("IA locale : " + self.title)
        try:
            return self._apply()
        finally:
            um.leaveUndoContext()


def _fmt_num(v):
    if isinstance(v, float):
        if v == int(v):
            v = int(v)
        else:
            return ("%.2f" % v).replace(".", ",")
    return "{:,}".format(v).replace(",", " ")


def _write_column(table, i, values):
    col = table.c0 + i
    rng = table.sheet.getCellRangeByPosition(col, table.r0 + 1, col, table.r1)
    rng.setDataArray(tuple((v,) for v in values))


def _examples(pairs, n=3):
    out = []
    for old, new in pairs[:n]:
        out.append("  « %s »  →  « %s »" % (old, new))
    return out

# ---------------------------------------------------------------------------
# 1. Nettoyer une colonne de texte
# ---------------------------------------------------------------------------

def _proper(s):
    # « saint-étienne » -> « Saint-Étienne », « l'isle » -> « L'Isle »
    return re.sub(r"[^\s\-']+", lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), s)


CASSES = {
    "nom_propre": ("première lettre de chaque mot en majuscule", _proper),
    "majuscules": ("tout en majuscules", lambda s: s.upper()),
    "minuscules": ("tout en minuscules", lambda s: s.lower()),
    "": ("casse inchangée", lambda s: s),
}


def prepare_normaliser_texte(table, colonne, casse=""):
    i = table.idx(colonne)
    label, fn = CASSES.get(casse or "", CASSES[""])
    old = table.column(colonne)
    new, pairs = [], []
    for v in old:
        if isinstance(v, str) and v:
            n = fn(re.sub(r"\s+", " ", v.strip()))
            if n != v:
                pairs.append((v, n))
            new.append(n)
        else:
            new.append(v)
    title = "Nettoyer la colonne %s (espaces superflus retirés, %s)" % (colonne, label)
    details = ["%d cellule(s) sur %d seront modifiées." % (len(pairs), len(old))]
    details += _examples(pairs)
    return Plan(title, details, lambda: _write_column(table, i, new), len(pairs))

# ---------------------------------------------------------------------------
# 2. Formater des téléphones français
# ---------------------------------------------------------------------------

def _phone(v):
    if isinstance(v, float):
        d = str(int(v))
    else:
        d = re.sub(r"\D", "", str(v))
    if d.startswith("0033"):
        d = "0" + d[4:]
    elif d.startswith("33") and len(d) == 11:
        d = "0" + d[2:]
    elif len(d) == 9 and not d.startswith("0"):
        d = "0" + d
    if len(d) == 10 and d.startswith("0"):
        return " ".join(d[k:k + 2] for k in range(0, 10, 2))
    return None


def prepare_formater_telephone(table, colonne):
    i = table.idx(colonne)
    old = table.column(colonne)
    new, pairs, unknown = [], [], []
    for v in old:
        if v == "":
            new.append(v)
            continue
        p = _phone(v)
        if p is None:
            unknown.append(v)
            new.append(v)
        else:
            if p != v:
                pairs.append((v if not isinstance(v, float) else _fmt_num(v), p))
            new.append(p)
    title = "Mettre la colonne %s au format 06 12 34 56 78" % colonne
    details = ["%d numéro(s) sur %d seront reformatés." % (len(pairs), len(old))]
    details += _examples(pairs)
    if unknown:
        details.append("%d valeur(s) non reconnue(s) resteront telles quelles, par exemple « %s »."
                       % (len(unknown), unknown[0]))
    return Plan(title, details, lambda: _write_column(table, i, new), len(pairs))

# ---------------------------------------------------------------------------
# 3. Supprimer les doublons
# ---------------------------------------------------------------------------

def _key(v):
    if isinstance(v, float):
        return _fmt_num(v)
    return re.sub(r"\s+", " ", str(v)).strip().lower()


def prepare_supprimer_doublons(table, colonne):
    i = table.idx(colonne)
    seen, dup = {}, []
    for n, r in enumerate(table.rows):
        k = _key(r[i])
        if not k:
            continue
        if k in seen:
            dup.append(n)
        else:
            seen[k] = n

    def apply():
        rows = table.sheet.getRows()
        # suppression du bas vers le haut, par blocs contigus
        abs_rows = [table.r0 + 1 + n for n in dup]
        for start, count in reversed(_blocks(abs_rows)):
            rows.removeByIndex(start, count)

    title = "Supprimer les lignes en double selon la colonne %s" % colonne
    details = ["%d ligne(s) en double seront supprimées, %d resteront."
               % (len(dup), len(table.rows) - len(dup)),
               "Deux valeurs identiques aux majuscules et aux espaces près comptent comme un doublon.",
               "La première occurrence est conservée."]
    if dup:
        ex = table.rows[dup[0]][i]
        details.append("  Exemple de doublon : « %s » (ligne %d)" % (ex, table.r0 + dup[0] + 2))
    return Plan(title, details, apply, len(dup))


def _blocks(sorted_rows):
    out = []
    for r in sorted_rows:
        if out and out[-1][0] + out[-1][1] == r:
            out[-1][1] += 1
        else:
            out.append([r, 1])
    return [tuple(b) for b in out]

# ---------------------------------------------------------------------------
# 4. Tableau croisé dynamique (et 5. graphique, qui s'appuie dessus)
# ---------------------------------------------------------------------------

OPERATIONS = {"somme": ("SUM", "Somme"), "moyenne": ("AVERAGE", "Moyenne"), "nombre": ("COUNT", "Nombre")}


def _aggregate(table, colonne, colonne_valeurs, operation):
    gi = table.idx(colonne)
    vi = table.idx(colonne_valeurs) if colonne_valeurs else gi
    acc = {}
    for r in table.rows:
        g = r[gi]
        if g == "":
            continue
        g = _fmt_num(g) if isinstance(g, float) else g
        a = acc.setdefault(g, [0.0, 0])
        v = r[vi]
        if operation == "nombre":
            a[1] += 1
        elif isinstance(v, float):
            a[0] += v
            a[1] += 1
    res = {}
    for g, (s, n) in acc.items():
        res[g] = n if operation == "nombre" else (s / n if operation == "moyenne" and n else s)
    return sorted(res.items(), key=lambda kv: -kv[1])


def _new_sheet(doc, base):
    sheets = doc.getSheets()
    name, k = base[:31], 2
    while sheets.hasByName(name):
        name = ("%s %d" % (base[:28], k))
        k += 1
    sheets.insertNewByName(name, sheets.getCount())
    return sheets.getByName(name), name


def _insert_pivot(doc, table, colonne, colonne_valeurs, operation, sheet_title, grand_total=True):
    func = OPERATIONS[operation][0]
    target, name = _new_sheet(doc, sheet_title)
    tables = table.sheet.getDataPilotTables()
    desc = tables.createDataPilotDescriptor()
    desc.setSourceRange(table.range.getRangeAddress())
    fields = desc.getDataPilotFields()
    gi = table.idx(colonne)
    vi = table.idx(colonne_valeurs) if colonne_valeurs else gi
    row_orient = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "ROW")
    data_orient = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "DATA")
    if vi == gi:
        # compter les lignes : on compte les cellules non vides de la colonne la plus remplie
        filled = [(sum(1 for r in table.rows if r[k] != ""), k) for k in range(len(table.headers)) if k != gi]
        vi = max(filled)[1] if filled else gi
        fields.getByIndex(gi).Orientation = row_orient
        d = fields.getByIndex(vi)
        d.Orientation = data_orient
        d.Function = uno.Enum("com.sun.star.sheet.GeneralFunction", "COUNT")
    else:
        fields.getByIndex(gi).Orientation = row_orient
        d = fields.getByIndex(vi)
        d.Orientation = data_orient
        d.Function = uno.Enum("com.sun.star.sheet.GeneralFunction", func)
    for prop, val in (("ShowFilterButton", False), ("RowGrand", grand_total), ("ColumnGrand", grand_total)):
        try:
            desc.setPropertyValue(prop, val)
        except Exception:
            pass
    pos = uno.createUnoStruct("com.sun.star.table.CellAddress")
    pos.Sheet = target.getRangeAddress().Sheet
    pos.Column, pos.Row = 0, 0
    tname = "IA_" + name.replace(" ", "_")
    tables.insertNewByName(tname, pos, desc)
    pivot = target.getDataPilotTables().getByName(tname)
    return target, pivot


def pivot_sheet_index(doc, sheet):
    # les noms d'objets graphiques doivent être uniques dans tout le document
    return sheet.getRangeAddress().Sheet


def _activate(doc, sheet):
    try:
        doc.getCurrentController().setActiveSheet(sheet)
    except Exception:
        pass


def _check_values(table, colonne_valeurs, operation):
    if operation in ("somme", "moyenne"):
        if not colonne_valeurs:
            raise ActionError("Précisez sur quelle colonne calculer la %s." % operation)
        vals = [v for v in table.column(colonne_valeurs) if v != ""]
        if vals and sum(isinstance(v, float) for v in vals) < len(vals) / 2:
            raise ActionError("La colonne %s contient surtout du texte : impossible d'en faire la %s."
                              % (colonne_valeurs, operation))


def _distinct_warning(table, colonne):
    vals = [v for v in table.column(colonne) if isinstance(v, str) and v]
    lowered = {}
    for v in vals:
        lowered.setdefault(re.sub(r"\s+", " ", v).strip().lower(), set()).add(v)
    messy = [k for k, s in lowered.items() if len(s) > 1]
    if messy:
        return ("Attention : la colonne %s contient des variantes d'écriture (par exemple « %s »). "
                "Nettoyez-la d'abord pour éviter des groupes en double."
                % (colonne, " », « ".join(sorted(lowered[messy[0]])[:2])))
    return None


def prepare_tableau_croise(doc, table, colonne, colonne_valeurs="", operation=""):
    operation = operation or ("somme" if colonne_valeurs else "nombre")
    if operation == "nombre":
        colonne_valeurs = colonne_valeurs or ""
    _check_values(table, colonne_valeurs, operation)
    agg = _aggregate(table, colonne, colonne_valeurs, operation)
    what = "%s de %s" % (OPERATIONS[operation][1].lower(), colonne_valeurs) if operation != "nombre" else "nombre de lignes"
    title = "Créer un tableau croisé dynamique : %s par %s, dans une nouvelle feuille" % (what, colonne)
    details = ["%d groupe(s). Aperçu des premiers :" % len(agg)]
    details += ["  %s : %s" % (g, _fmt_num(v)) for g, v in agg[:4]]
    w = _distinct_warning(table, colonne)
    if w:
        details.append(w)

    def apply():
        sheet, _ = _insert_pivot(doc, table, colonne, colonne_valeurs, operation,
                                 "TCD %s" % colonne)
        _activate(doc, sheet)

    return Plan(title, details, apply, len(agg))


CHARTS = {"barres": ("en barres", None), "courbe": ("en courbe", "com.sun.star.chart.LineDiagram"),
          "camembert": ("en camembert", "com.sun.star.chart.PieDiagram")}


def prepare_graphique(doc, table, colonne, colonne_valeurs="", type_graphique="", operation=""):
    type_graphique = type_graphique or "barres"
    operation = operation or ("somme" if colonne_valeurs else "nombre")
    _check_values(table, colonne_valeurs, operation)
    agg = _aggregate(table, colonne, colonne_valeurs, operation)
    label = CHARTS[type_graphique][0]
    what = "%s de %s" % (OPERATIONS[operation][1].lower(), colonne_valeurs) if operation != "nombre" else "nombre de lignes"
    title = "Créer un graphique %s : %s par %s, dans une nouvelle feuille" % (label, what, colonne)
    details = ["%d catégorie(s) sur le graphique." % len(agg)]
    if len(agg) > 25:
        details.append("Attention : avec plus de 25 catégories, le graphique sera peu lisible.")
    w = _distinct_warning(table, colonne)
    if w:
        details.append(w)

    def apply():
        sheet, pivot = _insert_pivot(doc, table, colonne, colonne_valeurs, operation,
                                     "Graphique %s" % colonne, grand_total=False)
        out = pivot.getOutputRange()
        rect = uno.createUnoStruct("com.sun.star.awt.Rectangle")
        rect.X, rect.Y, rect.Width, rect.Height = 9000, 500, 16000, 10000
        charts = sheet.getCharts()
        cname = "IA_graphique_%d" % pivot_sheet_index(doc, sheet)
        charts.addNewByName(cname, rect, (out,), True, True)
        chart = charts.getByName(cname).getEmbeddedObject()
        diag = CHARTS[type_graphique][1]
        if diag:
            chart.setDiagram(chart.createInstance(diag))
        try:
            chart.HasMainTitle = True
            chart.getTitle().String = "%s par %s" % (what[:1].upper() + what[1:], colonne)
        except Exception:
            pass
        _activate(doc, sheet)

    return Plan(title, details, apply, len(agg))

# ---------------------------------------------------------------------------
# 6. Trier
# ---------------------------------------------------------------------------

DATE_TEXT = re.compile(r"^\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}$")


def prepare_trier(table, colonne, ordre=""):
    i = table.idx(colonne)
    asc = ordre != "decroissant"
    vals = [v for v in table.column(colonne) if v != ""]

    def apply():
        props = []
        f = uno.createUnoStruct("com.sun.star.table.TableSortField")
        f.Field = i
        f.IsAscending = asc
        f.IsCaseSensitive = False
        pv = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        pv.Name, pv.Value = "SortFields", uno.Any("[]com.sun.star.table.TableSortField", (f,))
        props.append(pv)
        pv2 = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        pv2.Name, pv2.Value = "ContainsHeader", True
        props.append(pv2)
        uno.invoke(table.range, "sort", (tuple(props),))

    sens = "croissant (du plus petit au plus grand, de A à Z)" if asc else "décroissant (du plus grand au plus petit, de Z à A)"
    title = "Trier le tableau par %s, ordre %s" % (colonne, sens)
    details = ["%d ligne(s) seront réordonnées. La ligne d'en-tête reste en haut." % len(table.rows)]
    texts = [v for v in vals if isinstance(v, str)]
    if texts and sum(bool(DATE_TEXT.match(v)) for v in texts) > len(texts) / 2:
        details.append("Attention : ces dates sont saisies comme du texte. Le tri sera alphabétique, "
                       "pas chronologique.")
    return Plan(title, details, apply, len(table.rows))

# ---------------------------------------------------------------------------
# Aiguillage
# ---------------------------------------------------------------------------

def prepare(doc, sheet, choice):
    """choice : dictionnaire renvoyé par le modèle (action + paramètres)."""
    table = Table(sheet)
    if not table.rows:
        raise ActionError("La feuille active ne contient pas de tableau (il faut une ligne d'en-têtes et des données).")
    a = choice.get("action", "aucune")
    col = choice.get("colonne", "")
    if a == "aucune":
        raise ActionError("Je ne sais pas faire ça. Je peux nettoyer une colonne, formater des téléphones, "
                          "supprimer des doublons, créer un tableau croisé, un graphique ou trier.")
    if not col:
        raise ActionError("Je n'ai pas compris sur quelle colonne travailler. Reformulez en citant son nom.")
    if a == "normaliser_texte":
        return prepare_normaliser_texte(table, col, choice.get("casse", ""))
    if a == "formater_telephone":
        return prepare_formater_telephone(table, col)
    if a == "supprimer_doublons":
        return prepare_supprimer_doublons(table, col)
    if a == "tableau_croise":
        return prepare_tableau_croise(doc, table, col, choice.get("colonne_valeurs", ""), choice.get("operation", ""))
    if a == "graphique":
        return prepare_graphique(doc, table, col, choice.get("colonne_valeurs", ""),
                                 choice.get("type_graphique", ""), choice.get("operation", ""))
    if a == "trier":
        return prepare_trier(table, col, choice.get("ordre", ""))
    raise ActionError("Action inconnue : %s" % a)
