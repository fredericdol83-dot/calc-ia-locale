# -*- coding: utf-8 -*-
"""Fenêtre de l'assistant : une demande, une proposition, une validation."""
import json
import os
import traceback

import uno
import unohelper
from com.sun.star.awt import XActionListener

from calc_ia import actions, llm

CONFIG = os.path.join(os.path.expanduser("~"), ".calc-ia-locale.json")
DEFAULTS = {"url": "http://localhost:11434", "model": "qwen3:4b"}

TEAL, TEAL_LIGHT, GREY, RED, GREEN = 0x0E7C66, 0xE6F4F0, 0x5B6E6A, 0xB42318, 0x0E7C66

# raccourcis : libellé du bouton -> phrase pré-remplie (« … » est sélectionné pour être remplacé)
RACCOURCIS = [
    ("Nettoyer une colonne", "nettoie la colonne …"),
    ("Formater téléphones", "mets les téléphones au format 06 12 34 56 78"),
    ("Supprimer doublons", "supprime les doublons sur la colonne …"),
    ("Tableau croisé", "fais le total de … par …"),
    ("Graphique", "fais un graphique en barres de … par …"),
    ("Trier", "trie par … du plus grand au plus petit"),
]
GENERATED_PREFIXES = ("TCD ", "Graphique ")
PLACEHOLDER = ("La proposition de l'IA s'affichera ici, avec un aperçu des changements.\n\n"
               "Rien ne sera modifié tant que vous n'aurez pas cliqué sur Appliquer.")

_open = []  # garde la fenêtre en vie tant qu'elle est ouverte (fenêtre non bloquante)


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class Assistant(unohelper.Base, XActionListener):

    W = 262

    def __init__(self, ctx, doc):
        self.ctx, self.doc, self.plan = ctx, doc, None
        self.data_sheet = None
        self.created_sheet = None  # feuille créée par la dernière action (TCD, graphique)
        self.cfg = load_config()
        smgr = ctx.ServiceManager
        self.toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
        model.Title = "IA locale pour Calc"
        model.Width, model.Height = self.W, 262
        self.model = model
        W = self.W

        # bandeau
        self._label("bandeau", 0, 0, W, 18, "   IA locale  ·  100 % libre et local, rien ne quitte votre ordinateur",
                    color=0xFFFFFF, bg=TEAL, bold=True, middle=True)

        self._label("lbl_demande", 8, 25, W - 16, 10, "Votre demande", bold=True)
        self._edit("demande", 8, 36, W - 16, 26, multi=True)

        self._label("lbl_raccourcis", 8, 66, W - 16, 9, "Ou partez d'un raccourci :", color=GREY)
        bw, gap = (W - 16 - 8) // 3, 4
        for k, (lab, _) in enumerate(RACCOURCIS):
            x = 8 + (k % 3) * (bw + gap)
            y = 76 + (k // 3) * 15
            self._button("rac%d" % k, x, y, bw, 13, lab)

        self._label("statut", 8, 113, W - 92, 10, "", color=TEAL)
        self._button("proposer", W - 80, 109, 72, 16, "Proposer", default=True)

        self._label("titre_plan", 8, 132, W - 16, 20, "Proposition", bold=True)
        self._edit("apercu", 8, 154, W - 16, 66, multi=True, readonly=True, bg=TEAL_LIGHT)

        self._button("appliquer", 8, 226, 76, 16, "Appliquer")
        self._button("annuler", 88, 226, 92, 16, "Annuler la dernière action")
        self._button("fermer", W - 76, 226, 68, 16, "Fermer")

        self._label("lbl_modele", 8, 249, 28, 10, "Modèle :", color=GREY)
        self._combo("modele", 36, 247, 92, 12)
        self._label("connexion", 134, 249, W - 142, 10, "", color=GREY)

        self.dlg = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        self.dlg.setModel(model)
        self.dlg.getControl("apercu").setText(PLACEHOLDER)
        self.model.getByName("appliquer").Enabled = False
        self.model.getByName("annuler").Enabled = False
        names = ["proposer", "appliquer", "annuler", "fermer"] + ["rac%d" % k for k in range(len(RACCOURCIS))]
        for name in names:
            b = self.dlg.getControl(name)
            b.setActionCommand(name)
            b.addActionListener(self)
        self._check_ollama()

    # -- construction des contrôles -----------------------------------------
    def _add(self, kind, name, x, y, w, h):
        m = self.model.createInstance("com.sun.star.awt.UnoControl%sModel" % kind)
        m.Name = name
        m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
        self.model.insertByName(name, m)
        return m

    def _label(self, name, x, y, w, h, text, bold=False, color=None, bg=None, middle=False):
        m = self._add("FixedText", name, x, y, w, h)
        m.Label = text
        m.MultiLine = True
        if bold:
            m.FontWeight = 150
        if color is not None:
            m.TextColor = color
        if bg is not None:
            m.BackgroundColor = bg
        if middle:
            try:
                m.VerticalAlign = uno.Enum("com.sun.star.style.VerticalAlignment", "MIDDLE")
            except Exception:
                pass

    def _edit(self, name, x, y, w, h, multi=False, readonly=False, bg=None):
        m = self._add("Edit", name, x, y, w, h)
        m.MultiLine = multi
        if multi:
            m.VScroll = True
        m.ReadOnly = readonly
        if bg is not None:
            m.BackgroundColor = bg

    def _combo(self, name, x, y, w, h):
        m = self._add("ComboBox", name, x, y, w, h)
        m.Dropdown = True
        m.LineCount = 8
        m.Text = self.cfg["model"]

    def _button(self, name, x, y, w, h, label, default=False):
        m = self._add("Button", name, x, y, w, h)
        m.Label = label
        m.DefaultButton = default

    # -- état ----------------------------------------------------------------
    def _check_ollama(self):
        lab = self.model.getByName("connexion")
        try:
            models = llm.installed_models(self.cfg["url"], timeout=2)
        except llm.LLMError:
            lab.Label = "● Ollama non détecté, lancez-le"
            lab.TextColor = RED
            return
        self.model.getByName("modele").StringItemList = tuple(sorted(models))
        lab.Label = "● Ollama connecté, en local"
        lab.TextColor = GREEN

    def show(self):
        self.dlg.createPeer(self.toolkit, None)
        try:
            # place la fenêtre sur la droite pour garder le tableau visible
            frame = self.doc.getCurrentController().getFrame().getContainerWindow().getPosSize()
            ps = self.dlg.getPosSize()
            self.dlg.setPosSize(frame.X + max(frame.Width - ps.Width - 40, 0), frame.Y + 120, 0, 0,
                                uno.getConstantByName("com.sun.star.awt.PosSize.POS"))
        except Exception:
            pass
        self.dlg.setVisible(True)
        self.dlg.getControl("demande").setFocus()
        _open.append(self)

    def _status(self, text):
        self.dlg.getControl("statut").setText(text)
        for method in ("processEventsToIdle", "reschedule"):
            try:
                getattr(self.toolkit, method)()
                break
            except Exception:
                continue

    def _show(self, title, body):
        self.model.getByName("titre_plan").Label = title
        self.dlg.getControl("apercu").setText(body)

    # -- actions -------------------------------------------------------------
    def actionPerformed(self, ev):
        cmd = ev.ActionCommand
        try:
            if cmd.startswith("rac"):
                self.on_raccourci(int(cmd[3:]))
            else:
                getattr(self, "on_" + cmd)()
        except Exception:
            self._status("")
            self._show("Erreur inattendue", traceback.format_exc())

    def on_raccourci(self, k):
        text = RACCOURCIS[k][1]
        ctl = self.dlg.getControl("demande")
        ctl.setText(text)
        ctl.setFocus()
        sel = uno.createUnoStruct("com.sun.star.awt.Selection")
        i = text.find("…")
        sel.Min, sel.Max = (i, i + 1) if i >= 0 else (len(text), len(text))
        try:
            ctl.setSelection(sel)
        except Exception:
            pass

    def on_fermer(self):
        self.dlg.setVisible(False)
        self.dlg.dispose()
        if self in _open:
            _open.remove(self)

    def _target_sheet(self):
        sheet = self.doc.getCurrentController().getActiveSheet()
        if sheet.getName().startswith(GENERATED_PREFIXES) and self.data_sheet is not None:
            return self.data_sheet  # on revient sur les données, pas sur un résultat créé par l'assistant
        self.data_sheet = sheet
        return sheet

    def on_proposer(self):
        self.plan = None
        self.model.getByName("appliquer").Enabled = False
        demande = self.dlg.getControl("demande").getText().strip()
        if not demande or "…" in demande:
            self._show("Proposition", "Écrivez votre demande, ou complétez le raccourci (remplacez les « … »).")
            return
        modele = self.dlg.getControl("modele").getText().strip() or DEFAULTS["model"]
        if modele != self.cfg["model"]:
            self.cfg["model"] = modele
            save_config(self.cfg)
        sheet = self._target_sheet()
        try:
            table = actions.Table(sheet)
        except Exception:
            self._show("Proposition", "Impossible de lire la feuille active.")
            return
        self._show("Proposition", "")
        self._status("Le modèle local réfléchit…")
        try:
            choice = llm.choose_action(self.cfg["url"], modele, table.headers, demande)
            plan = actions.prepare(self.doc, sheet, choice)
        except (llm.LLMError, actions.ActionError) as e:
            self._status("")
            self._show("Je ne peux pas faire ça", str(e))
            return
        self._status("")
        lines = ["Feuille : %s" % sheet.getName(), ""] + plan.details
        if plan.changes == 0:
            lines += ["", "Rien à modifier."]
        else:
            lines += ["", "Vérifiez, puis cliquez sur Appliquer."]
            self.plan = plan
            self.model.getByName("appliquer").Enabled = True
        self._show(plan.title + ".", "\n".join(lines))

    def on_appliquer(self):
        if not self.plan:
            return
        self.model.getByName("appliquer").Enabled = False
        self._status("Application en cours…")
        try:
            result = self.plan.apply(self.doc)
            self.created_sheet = result if isinstance(result, str) else None
        except Exception as e:
            self._status("")
            self._show("L'action a échoué", str(e))
            return
        self._status("Fait.")
        self.model.getByName("annuler").Enabled = True
        self._show("Fait : " + self.plan.title + ".",
                   "Vous pouvez annuler avec le bouton « Annuler la dernière action », "
                   "ou faire une nouvelle demande.")
        self.plan = None

    def on_annuler(self):
        sheets = self.doc.getSheets()
        if self.created_sheet and sheets.hasByName(self.created_sheet):
            # une feuille créée (tableau croisé, graphique) se retire en la supprimant
            if self.data_sheet is not None:
                self.doc.getCurrentController().setActiveSheet(self.data_sheet)
            sheets.removeByName(self.created_sheet)
            self.created_sheet = None
            self._status("Action annulée.")
            self._show("Proposition", PLACEHOLDER)
        else:
            um = self.doc.getUndoManager()
            if um.isUndoPossible():
                um.undo()
                self._status("Action annulée.")
                self._show("Proposition", PLACEHOLDER)
        self.model.getByName("annuler").Enabled = False


def open_assistant(ctx):
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.getCurrentComponent()
    if doc is None or not doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
        return
    Assistant(ctx, doc).show()
