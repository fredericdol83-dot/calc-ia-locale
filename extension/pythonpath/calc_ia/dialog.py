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
DEFAULTS = {"url": "http://localhost:11434", "model": "qwen2.5:3b"}
EXEMPLES = ("Exemples : « supprime les doublons sur l'email », « total des devis par ville », "
            "« trie par montant décroissant »")

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

    def __init__(self, ctx, doc):
        self.ctx, self.doc, self.plan = ctx, doc, None
        self.cfg = load_config()
        smgr = ctx.ServiceManager
        self.toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
        model.Title = "IA locale pour Calc"
        model.Width, model.Height = 290, 236
        self.model = model

        self._label("intro", 8, 8, 274, 10, "Que voulez-vous faire sur la feuille active ?", bold=True)
        self._edit("demande", 8, 20, 274, 30, multi=True)
        self._label("exemples", 8, 52, 274, 18, EXEMPLES, small=True)
        self._button("proposer", 214, 72, 68, 15, "Proposer", default=True)
        self._label("statut", 8, 75, 200, 10, "")
        self._label("titre_apercu", 8, 94, 274, 10, "Proposition", bold=True)
        self._edit("apercu", 8, 106, 274, 88, multi=True, readonly=True)
        self._label("lbl_modele", 8, 202, 30, 10, "Modèle :", small=True)
        self._edit("modele", 38, 200, 80, 12)
        self._label("confidentialite", 124, 202, 160, 10,
                    "100 % local : rien ne quitte votre ordinateur", small=True)
        self._button("appliquer", 140, 216, 72, 15, "Appliquer")
        self._button("fermer", 216, 216, 66, 15, "Fermer")

        self.dlg = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        self.dlg.setModel(model)
        self.dlg.getControl("modele").setText(self.cfg["model"])
        self.model.getByName("appliquer").Enabled = False
        for name in ("proposer", "appliquer", "fermer"):
            b = self.dlg.getControl(name)
            b.setActionCommand(name)
            b.addActionListener(self)

    # -- construction des contrôles -----------------------------------------
    def _add(self, kind, name, x, y, w, h):
        m = self.model.createInstance("com.sun.star.awt.UnoControl%sModel" % kind)
        m.Name = name
        m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
        self.model.insertByName(name, m)
        return m

    def _label(self, name, x, y, w, h, text, bold=False, small=False):
        m = self._add("FixedText", name, x, y, w, h)
        m.Label = text
        m.MultiLine = True
        if bold:
            m.FontWeight = 150
        if small:
            m.TextColor = 0x5B6E6A

    def _edit(self, name, x, y, w, h, multi=False, readonly=False):
        m = self._add("Edit", name, x, y, w, h)
        m.MultiLine = multi
        if multi:
            m.VScroll = True
        m.ReadOnly = readonly

    def _button(self, name, x, y, w, h, label, default=False):
        m = self._add("Button", name, x, y, w, h)
        m.Label = label
        m.DefaultButton = default

    # -- comportement -----------------------------------------------------------
    def show(self):
        self.dlg.createPeer(self.toolkit, None)
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

    def _show_plan_text(self, text):
        self.dlg.getControl("apercu").setText(text)

    def actionPerformed(self, ev):
        try:
            getattr(self, "on_" + ev.ActionCommand)()
        except Exception:
            self._status("")
            self._show_plan_text("Erreur inattendue. Détail technique :\n" + traceback.format_exc())

    def on_fermer(self):
        self.dlg.setVisible(False)
        self.dlg.dispose()
        if self in _open:
            _open.remove(self)

    def on_proposer(self):
        self.plan = None
        self.model.getByName("appliquer").Enabled = False
        demande = self.dlg.getControl("demande").getText().strip()
        if not demande:
            self._show_plan_text("Écrivez d'abord votre demande.")
            return
        modele = self.dlg.getControl("modele").getText().strip() or DEFAULTS["model"]
        if modele != self.cfg["model"]:
            self.cfg["model"] = modele
            save_config(self.cfg)
        sheet = self.doc.getCurrentController().getActiveSheet()
        try:
            table = actions.Table(sheet)
        except Exception:
            self._show_plan_text("Impossible de lire la feuille active.")
            return
        self._show_plan_text("")
        self._status("Le modèle local réfléchit (quelques secondes)…")
        try:
            choice = llm.choose_action(self.cfg["url"], modele, table.headers, demande)
            plan = actions.prepare(self.doc, sheet, choice)
        except (llm.LLMError, actions.ActionError) as e:
            self._status("")
            self._show_plan_text(str(e))
            return
        self._status("")
        lines = [plan.title + ".", ""] + plan.details
        if plan.changes == 0:
            lines += ["", "Rien à modifier."]
        else:
            lines += ["", "Vérifiez, puis cliquez sur Appliquer. Ctrl+Z annulera si besoin."]
            self.plan = plan
            self.model.getByName("appliquer").Enabled = True
        self._show_plan_text("\n".join(lines))

    def on_appliquer(self):
        if not self.plan:
            return
        self.model.getByName("appliquer").Enabled = False
        self._status("Application en cours…")
        try:
            self.plan.apply(self.doc)
        except Exception as e:
            self._status("")
            self._show_plan_text("L'action a échoué : %s" % e)
            return
        self._status("")
        self._show_plan_text("Fait : %s.\n\nCtrl+Z dans la feuille pour annuler. "
                             "Vous pouvez faire une nouvelle demande." % self.plan.title)
        self.plan = None


def open_assistant(ctx):
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.getCurrentComponent()
    if doc is None or not doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
        return
    Assistant(ctx, doc).show()
