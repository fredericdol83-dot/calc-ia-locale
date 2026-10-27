# -*- coding: utf-8 -*-
"""Panneau latéral « IA locale » (à droite du tableur, comme Copilot dans Excel, mais 100 % local).

États : installation (Ollama ou modèle manquant), accueil (idées + demande), proposition, fait."""
import time
import traceback

import uno
import unohelper
from com.sun.star.awt import XActionListener, XWindowListener

from calc_ia import actions, llm, suggest
from calc_ia.dialog import load_config, save_config, DEFAULTS, GENERATED_PREFIXES

TEAL, TEAL_BG, GREY, RED, AMBER_BG, LIGHT = 0x0E7C66, 0xE3F3EE, 0x56686F, 0xB42318, 0xFFF7E6, 0xF4F7F6
OLLAMA_URL = "https://ollama.com/download"
MAX_IDEAS = 5
M = 6  # marge, en unités de dialogue


class AssistantPanel(unohelper.Base, XActionListener, XWindowListener):

    def __init__(self, ctx, frame, parent):
        self.ctx, self.frame, self.parent = ctx, frame, parent
        self.smgr = ctx.ServiceManager
        self.toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        self.cfg = load_config()
        self.state = "main"
        self.plan = None
        self.ideas = []
        self.history = []
        self.done_text = None
        self.data_sheet = None
        self.created_sheet = None
        self.height_px = 600
        self.c = {}

        self.cont = self.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainer", ctx)
        self.cont.setModel(self.smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainerModel", ctx))
        self.cont.createPeer(self.toolkit, parent)
        self.cont.setVisible(True)
        self.window = self.cont
        self._build()
        parent.addWindowListener(self)
        self.check_setup()

    # ------------------------------------------------------------ contrôles
    def _ctl(self, kind, name, **props):
        model = self.smgr.createInstanceWithContext("com.sun.star.awt.UnoControl%sModel" % kind, self.ctx)
        for k, v in props.items():
            setattr(model, k, v)
        ctl = self.smgr.createInstanceWithContext("com.sun.star.awt.UnoControl%s" % kind, self.ctx)
        ctl.setModel(model)
        self.cont.addControl(name, ctl)
        self.c[name] = ctl
        if kind == "Button":
            ctl.setActionCommand(name)
            ctl.addActionListener(self)
        return ctl

    def _label(self, name, text="", bold=False, color=None, bg=None, align=0):
        p = {"Label": text, "MultiLine": True, "Align": align}
        if bold:
            p["FontWeight"] = 150.0
        if color is not None:
            p["TextColor"] = color
        if bg is not None:
            p["BackgroundColor"] = bg
        return self._ctl("FixedText", name, **p)

    def _build(self):
        L, B = self._label, lambda n, t: self._ctl("Button", n, Label=t, MultiLine=True)
        L("etat", "", bold=True, color=TEAL)
        # installation
        L("setup_t", "", bold=True)
        L("setup_txt", "")
        B("btn_ollama", "Télécharger Ollama (site officiel)")
        B("btn_dl", "Télécharger le modèle")
        L("progress", "", color=TEAL)
        B("btn_verifier", "Vérifier à nouveau")
        # fait
        L("done_t", "✓ C'est fait", bold=True, color=TEAL, bg=TEAL_BG)
        L("done_txt", "", bg=TEAL_BG)
        B("btn_annuler", "Annuler cette action")
        # accueil
        L("table_k", "Tableau analysé", color=GREY)
        L("table", "", bold=True)
        L("idees_t", "Idées pour ce tableau", bold=True)
        B("btn_actualiser", "Actualiser")
        L("grp_n", "NETTOYER", color=GREY)
        L("grp_a", "ANALYSER", color=GREY)
        for k in range(MAX_IDEAS):
            B("idee%d" % k, "")
            self.c["idee%d" % k].getModel().Align = 0
            self.c["idee%d" % k].getModel().FontWeight = 150.0
            L("idee%d_d" % k, "", color=GREY)
        L("aucune", "Rien de particulier à corriger dans ce tableau.", color=GREY)
        L("q", "Ou décrivez votre demande", bold=True)
        self._ctl("Edit", "demande", MultiLine=True, VScroll=False)
        B("btn_proposer", "Proposer")
        self.c["btn_proposer"].getModel().DefaultButton = True
        L("statut", "", color=TEAL)
        L("cap_t", "Ce que je sais faire", bold=True, bg=LIGHT)
        L("cap_n", "", bg=LIGHT)
        L("cap_a", "", bg=LIGHT)
        L("cap_p", "", color=GREY, bg=LIGHT)
        # proposition
        L("vous", "", bg=LIGHT)
        L("prop_k", "Voici ce que je propose", color=GREY)
        L("prop_t", "", bold=True)
        self._ctl("Edit", "details", MultiLine=True, ReadOnly=True, VScroll=True)
        L("compris", "", color=GREY)
        L("prereq_t", "", bg=AMBER_BG)
        B("btn_prereq", "")
        L("safe", "Rien n'a encore été modifié. Vérifiez, puis appliquez.", bg=AMBER_BG)
        B("btn_appliquer", "Appliquer")
        B("btn_modifier", "Modifier ma demande")
        # historique et pied
        L("hist_t", "Historique de la session", bold=True)
        self._ctl("ListBox", "hist")
        L("modele_k", "Modèle :", color=GREY)
        self._ctl("ComboBox", "modele", Dropdown=True, LineCount=8, Text=self.cfg["model"])
        L("offline", "Hors ligne, rien n'est envoyé sur Internet", color=GREY)

    # ------------------------------------------------------------ mise en page
    def _rows(self, W):
        """Lignes à afficher selon l'état : (liste de (nom, x, largeur), hauteur)."""
        full = lambda n, h: ([(n, M, W - 2 * M)], h)
        rows = [full("etat", 12), (None, 2)]
        s = self.state
        if s == "setup":
            rows += [full("setup_t", 22), full("setup_txt", 44), full("btn_ollama", 16), (None, 3),
                     full("btn_dl", 16), full("progress", 20), full("btn_verifier", 16)]
        if s == "main" and self.done_text:
            rows += [full("done_t", 12), full("done_txt", 22),
                     ([("btn_annuler", M, 90)], 16), (None, 8)]
        if s == "main":
            rows += [full("table_k", 9), full("table", 12), (None, 4),
                     ([("idees_t", M, W - 2 * M - 52), ("btn_actualiser", W - M - 50, 50)], 13)]
            groups = {}
            for k, i in enumerate(self.ideas):
                groups.setdefault(i.get("groupe", "Nettoyer"), []).append(k)
            for g, lab in (("Nettoyer", "grp_n"), ("Analyser", "grp_a")):
                if g in groups:
                    rows.append(full(lab, 10))
                    for k in groups[g]:
                        rows += [full("idee%d" % k, 15), ([("idee%d_d" % k, M + 3, W - 2 * M - 3)], 12)]
            if not self.ideas:
                rows.append(full("aucune", 12))
            rows += [(None, 6), full("q", 11), full("demande", 30),
                     ([("statut", M, W - 2 * M - 62), ("btn_proposer", W - M - 60, 60)], 16), (None, 6),
                     full("cap_t", 11), full("cap_n", 30), full("cap_a", 22), full("cap_p", 30)]
        if s == "proposition":
            rows += [full("vous", 20), (None, 4), full("prop_k", 9), full("prop_t", 28)]
            if self.c["compris"].getModel().Label:
                rows.append(full("compris", 20))
            rows += [full("details", 84), (None, 3)]
            if self.plan is not None and self.plan.prereq:
                rows += [full("prereq_t", 22), full("btn_prereq", 16), (None, 4)]
            rows += [full("safe", 12), (None, 4),
                     ([("btn_appliquer", M, (W - 2 * M) * 0.55),
                       ("btn_modifier", M + (W - 2 * M) * 0.58, (W - 2 * M) * 0.42)], 18)]
        if s in ("main", "proposition") and self.history:
            rows += [(None, 8), full("hist_t", 11), full("hist", 40)]
        rows += [(None, 8), ([("modele_k", M, 32), ("modele", M + 32, W - 2 * M - 32)], 13), (None, 2),
                 full("offline", 10)]
        return rows

    def _px(self, x, y, w, h):
        Size = uno.createUnoStruct
        MU = uno.getConstantByName("com.sun.star.util.MeasureUnit.APPFONT")
        peer = self.cont.getPeer()
        a = peer.convertSizeToPixel(uno.createUnoStruct("com.sun.star.awt.Size", int(x), int(y)), MU)
        b = peer.convertSizeToPixel(uno.createUnoStruct("com.sun.star.awt.Size", int(w), int(h)), MU)
        return a.Width, a.Height, max(b.Width, 1), max(b.Height, 1)

    def layout(self):
        try:
            ps = self.parent.getPosSize()
            MU = uno.getConstantByName("com.sun.star.util.MeasureUnit.APPFONT")
            W = self.cont.getPeer().convertSizeToLogic(
                uno.createUnoStruct("com.sun.star.awt.Size", ps.Width, 10), MU).Width
        except Exception:
            ps, W = None, 160
        W = max(W, 140)
        visible, y = set(), M
        for items, h in self._rows(W):
            for it in items or []:
                name, x, w = it
                X, Y, Wd, Ht = self._px(x, y, w, h - 2)
                self.c[name].setPosSize(X, Y, Wd, Ht, uno.getConstantByName("com.sun.star.awt.PosSize.POSSIZE"))
                visible.add(name)
            y += h
        for name, ctl in self.c.items():
            ctl.setVisible(name in visible)
        self.height_px = self._px(0, y + M, 1, 1)[1]
        if ps is not None:
            self.cont.setPosSize(0, 0, ps.Width, max(ps.Height, self.height_px),
                                 uno.getConstantByName("com.sun.star.awt.PosSize.POSSIZE"))

    # XWindowListener
    def windowResized(self, ev):
        self.layout()

    def windowMoved(self, ev):
        pass

    def windowShown(self, ev):
        self.refresh_ideas()

    def windowHidden(self, ev):
        pass

    def disposing(self, ev):
        pass

    # ------------------------------------------------------------ état
    def _doc(self):
        return self.frame.getController().getModel()

    def _set(self, name, text):
        ctl = self.c[name]
        if hasattr(ctl, "setText") and ctl.getModel().supportsService("com.sun.star.awt.UnoControlEditModel"):
            ctl.setText(text)
        else:
            ctl.getModel().Label = text

    def _busy(self, text):
        self._set("statut", text)
        self._set("progress", text) if self.state == "setup" else None
        for m in ("processEventsToIdle", "reschedule"):
            try:
                getattr(self.toolkit, m)()
                break
            except Exception:
                continue

    def check_setup(self):
        model = self.c["modele"].getText().strip() or DEFAULTS["model"]
        remote = self.cfg.get("serveur_distant_autorise", False)
        try:
            models = llm.installed_models(self.cfg["url"], timeout=2, allow_remote=remote)
        except llm.LLMError as e:
            if not llm.is_local(self.cfg["url"]):
                self.state = "setup"
                self._set("etat", "● Adresse non locale refusée")
                self.c["etat"].getModel().TextColor = RED
                self._set("setup_t", "Connexion refusée par sécurité")
                self._set("setup_txt", str(e))
                self.layout()
                return
            self.state = "setup"
            self._set("etat", "● Ollama absent")
            self.c["etat"].getModel().TextColor = RED
            self._set("setup_t", "Il manque Ollama, le moteur qui fait tourner l'IA sur votre PC.")
            self._set("setup_txt", "Installez-le depuis son site officiel (gratuit, environ 5 minutes), "
                                   "lancez-le, puis cliquez sur « Vérifier à nouveau ».")
            self.c["btn_ollama"].getModel().Enabled = True
            self.c["btn_dl"].getModel().Enabled = False
            self.layout()
            return
        self.c["modele"].getModel().StringItemList = tuple(sorted(models))
        if model not in models and model + ":latest" not in models:
            self.state = "setup"
            self._set("etat", "● Modèle manquant")
            self.c["etat"].getModel().TextColor = RED
            self._set("setup_t", "Ollama est prêt. Il reste à télécharger le modèle d'IA.")
            self._set("setup_txt", "Le modèle %s pèse environ 3 Go. Une fois téléchargé, il fonctionne "
                                   "sans connexion Internet." % model)
            self._set("btn_dl", "Télécharger le modèle %s" % model)
            self.c["btn_ollama"].getModel().Enabled = False
            self.c["btn_dl"].getModel().Enabled = True
            self.layout()
            return
        if llm.is_local(self.cfg["url"]):
            self._set("etat", "● 100 % local, rien ne sort de ce PC")
            self.c["etat"].getModel().TextColor = TEAL
        else:
            self._set("etat", "● Attention : modèle sur un autre ordinateur (%s)" % self.cfg["url"])
            self.c["etat"].getModel().TextColor = RED
        self.state = "main"
        self.refresh_ideas()

    def _target_sheet(self):
        sheet = self._doc().getCurrentController().getActiveSheet()
        if sheet.getName().startswith(GENERATED_PREFIXES) and self.data_sheet is not None:
            return self.data_sheet
        self.data_sheet = sheet
        return sheet

    def refresh_ideas(self):
        if self.state != "main":
            self.layout()
            return
        try:
            sheet = self._target_sheet()
            self._set("table", suggest.describe(sheet))
            self.ideas = suggest.suggestions(sheet, MAX_IDEAS)
            cap = suggest.capabilities(sheet)
        except Exception:
            self.ideas, cap = [], suggest.capabilities(None)
            self._set("table", "Aucun tableau lisible sur cette feuille")
        for k in range(MAX_IDEAS):
            if k < len(self.ideas):
                self._set("idee%d" % k, self.ideas[k]["titre"])
                self._set("idee%d_d" % k, self.ideas[k]["detail"])
        self._set("cap_n", "Nettoyer · " + ", ".join(t.lower() for t, _ in cap["Nettoyer"]))
        self._set("cap_a", "Analyser · " + ", ".join(t.lower() for t, _ in cap["Analyser"]))
        self._set("cap_p", "Pas encore · " + cap["Pas encore"])
        self.c["demande"].getModel().HelpText = "Exemple : " + cap["Analyser"][0][1]
        self.layout()

    # ------------------------------------------------------------ actions
    def actionPerformed(self, ev):
        cmd = ev.ActionCommand
        try:
            if cmd.startswith("idee"):
                self.on_idea(int(cmd[4:]))
            else:
                getattr(self, "on_" + cmd[4:])()
        except Exception:
            self._show_error("Erreur inattendue", traceback.format_exc())

    def _show_error(self, title, text):
        self._busy("")
        self.state, self.plan = "proposition", None
        self._set("vous", "")
        self._set("compris", "")
        self._set("prop_k", "")
        self._set("prop_t", title)
        self._set("details", text)
        self.c["btn_appliquer"].getModel().Enabled = False
        self.layout()

    def _show_plan(self, echo, plan, seconds=None, choice=None, compris=""):
        self.plan = plan if plan.changes else None
        self.last = (echo, choice)
        self._set("compris", compris)
        if plan.prereq:
            col = plan.prereq["colonne"]
            self._set("prereq_t", "La colonne %s contient des variantes d'écriture (« Lyon », « LYON »…). "
                                  "Elles seraient comptées comme des valeurs différentes." % col)
            self._set("btn_prereq", "Harmoniser « %s » d'abord (conseillé)" % col)
        self.state = "proposition"
        self._set("vous", echo)
        self._set("prop_k", "Voici ce que je propose" + (" · en %.0f s" % seconds if seconds else ""))
        self._set("prop_t", plan.title + ".")
        lines = list(plan.details)
        if not plan.changes:
            lines += ["", "Rien à modifier."]
        self._set("details", "\n".join(lines))
        self.c["btn_appliquer"].getModel().Enabled = bool(plan.changes)
        self.layout()

    def on_idea(self, k):
        idea = self.ideas[k]
        try:
            plan = actions.prepare(self._doc(), self._target_sheet(), idea["choice"])
        except actions.ActionError as e:
            return self._show_error("Je ne peux pas faire ça", str(e))
        self._show_plan("Idée : " + idea["titre"], plan, choice=idea["choice"])

    def on_proposer(self):
        demande = self.c["demande"].getText().strip()
        if not demande:
            self._set("statut", "Écrivez d'abord votre demande.")
            return
        modele = self.c["modele"].getText().strip() or DEFAULTS["model"]
        if modele != self.cfg["model"]:
            self.cfg["model"] = modele
            save_config(self.cfg)
        sheet = self._target_sheet()
        self._busy("Le modèle local réfléchit…")
        t0 = time.time()
        try:
            table = actions.Table(sheet)
            choice = llm.choose_action(self.cfg["url"], modele, table.headers, demande,
                                       allow_remote=self.cfg.get("serveur_distant_autorise", False))
            plan = actions.prepare(self._doc(), sheet, choice)
        except (llm.LLMError, actions.ActionError) as e:
            self._busy("")
            return self._show_error("Je ne peux pas faire ça", str(e))
        self._busy("")
        self._show_plan("Vous : " + demande, plan, time.time() - t0, choice=choice, compris=_explain(choice))

    def on_appliquer(self):
        if not self.plan:
            return
        self.c["btn_appliquer"].getModel().Enabled = False
        result = self.plan.apply(self._doc())
        self.created_sheet = result if isinstance(result, str) else None
        self.history.insert(0, "%s  %s" % (time.strftime("%H:%M"), self.plan.title))
        self.c["hist"].getModel().StringItemList = tuple(self.history)
        self.done_text = self.plan.title + "."
        self._set("done_txt", self.done_text)
        self.c["btn_annuler"].getModel().Enabled = True
        self.plan = None
        self.state = "main"
        self.c["demande"].setText("")
        self.refresh_ideas()

    def on_prereq(self):
        """Applique l'harmonisation conseillée, puis recalcule la proposition initiale."""
        if not self.plan or not self.plan.prereq:
            return
        doc, sheet = self._doc(), self._target_sheet()
        fix = actions.prepare(doc, sheet, self.plan.prereq)
        fix.apply(doc)
        self.history.insert(0, "%s  %s" % (time.strftime("%H:%M"), fix.title))
        self.c["hist"].getModel().StringItemList = tuple(self.history)
        echo, choice = self.last
        plan = actions.prepare(doc, sheet, choice)
        self._show_plan(echo, plan, choice=choice, compris=self.c["compris"].getModel().Label)

    def on_modifier(self):
        self.state, self.plan = "main", None
        self.done_text = None
        self.refresh_ideas()

    def on_annuler(self):
        doc = self._doc()
        sheets = doc.getSheets()
        if self.created_sheet and sheets.hasByName(self.created_sheet):
            if self.data_sheet is not None:
                doc.getCurrentController().setActiveSheet(self.data_sheet)
            sheets.removeByName(self.created_sheet)
        else:
            um = doc.getUndoManager()
            if um.isUndoPossible():
                um.undo()
        self.created_sheet = None
        self.history.insert(0, "%s  Annulé : %s" % (time.strftime("%H:%M"), self.done_text or ""))
        self.c["hist"].getModel().StringItemList = tuple(self.history)
        self.done_text = None
        self.refresh_ideas()

    def on_actualiser(self):
        self.done_text = None
        self.refresh_ideas()

    def on_verifier(self):
        self.check_setup()

    def on_ollama(self):
        shell = self.smgr.createInstanceWithContext("com.sun.star.system.SystemShellExecute", self.ctx)
        shell.execute(OLLAMA_URL, "", uno.getConstantByName("com.sun.star.system.SystemShellExecuteFlags.URIS_ONLY"))

    def on_dl(self):
        model = self.c["modele"].getText().strip() or DEFAULTS["model"]
        self.c["btn_dl"].getModel().Enabled = False

        def progress(status, frac):
            self._busy("Téléchargement : %d %%" % int(frac * 100) if frac is not None else status)
        try:
            llm.pull_model(self.cfg["url"], model, progress,
                           allow_remote=self.cfg.get("serveur_distant_autorise", False))
        except llm.LLMError as e:
            self._busy(str(e))
            self.c["btn_dl"].getModel().Enabled = True
            return
        self._busy("Modèle installé.")
        self.check_setup()


ACTION_NAMES = {"normaliser_texte": "harmoniser une colonne", "formater_telephone": "formater des téléphones",
                "supprimer_doublons": "supprimer des doublons", "tableau_croise": "tableau croisé",
                "graphique": "graphique", "trier": "trier"}


def _explain(choice):
    """Ce que le modèle a compris, en clair, pour que l'utilisateur puisse vérifier."""
    parts = [ACTION_NAMES.get(choice.get("action"), choice.get("action", ""))]
    if choice.get("colonne"):
        parts.append("colonne %s" % choice["colonne"])
    if choice.get("colonne_valeurs"):
        parts.append("valeurs : %s" % choice["colonne_valeurs"])
    if choice.get("operation"):
        parts.append("calcul : %s" % choice["operation"])
    if choice.get("ordre"):
        parts.append("ordre %s" % choice["ordre"].replace("decroissant", "décroissant"))
    return "J'ai compris : " + ", ".join(parts) + "."


def open_sidebar(ctx):
    """Ouvre le panneau « IA locale » dans la barre latérale du document actif."""
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    ctrl = desktop.getCurrentComponent().getCurrentController()
    sidebar = ctrl.getSidebar()
    sidebar.setVisible(True)
    deck = sidebar.getDecks().getByName("CalcIALocaleDeck")
    deck.activate(True)
