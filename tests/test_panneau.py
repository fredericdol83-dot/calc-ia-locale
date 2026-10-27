# -*- coding: utf-8 -*-
"""Test du panneau latéral sans interface graphique réelle, avec un faux Ollama.
LibreOffice headless sur le port 2002, puis : python3 tests/test_panneau.py"""
import json, os, shutil, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "extension", "pythonpath"))
import test_actions as t  # noqa: E402
from calc_ia import dialog, panel  # noqa: E402

STATE = {"models": ["qwen3:4b"], "pulled": False}


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, lines=None):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if lines:
            for l in lines:
                self.wfile.write((json.dumps(l) + "\n").encode())
        else:
            self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        self._send({"models": [{"name": m} for m in STATE["models"]]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/pull":
            STATE["models"].append(body["model"])
            return self._send(None, [{"status": "pulling", "total": 100, "completed": 50},
                                     {"status": "success"}])
        self._send({"message": {"content": json.dumps(
            {"action": "tableau_croise", "colonne": "Ville", "colonne_valeurs": "Montant devis (€)",
             "operation": "moyenne"})}})


def main():
    srv = HTTPServer(("localhost", 11998), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dialog.CONFIG = os.path.join(tempfile.mkdtemp(), "cfg.json")
    cfg = {"url": "http://localhost:11998", "model": "qwen3:4b"}
    panel.load_config = lambda: dict(cfg)

    import uno
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    rctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    desktop = rctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", rctx)
    tmp = os.path.join(tempfile.mkdtemp(), "contacts.ods")
    shutil.copy(os.path.join(HERE, "..", "exemples", "contacts-fictifs.ods"), tmp)
    doc = t.load(desktop, tmp)
    frame = doc.getCurrentController().getFrame()
    p = panel.AssistantPanel(rctx, frame, frame.getContainerWindow())
    vis = lambda n: p.c[n].isVisible() if hasattr(p.c[n], "isVisible") else None
    label = lambda n: p.c[n].getModel().Label

    t.check(p.state == "main", "panneau prêt quand Ollama et le modèle sont là")
    t.check(label("etat") == "● 100 % local", "indicateur « 100 % local »")
    t.check(len(p.ideas) == 5 and "Ville" in label("idee0"), "5 idées adaptées au tableau, la première sur Ville")
    t.check(label("cap_p").startswith("Pas encore"), "le panneau dit ce qu'il ne sait pas faire")
    print("  " + label("table"))
    for k in range(5):
        print("  idée :", label("idee%d" % k).replace("\n", " · "))

    p.on_idea(2)  # doublons
    t.check(p.state == "proposition" and "104" in p.c["details"].getText(), "clic sur une idée : proposition chiffrée sans passer par le modèle")
    p.on_appliquer()
    n = len(dialog.actions.Table(doc.Sheets.getByIndex(0)).rows)
    t.check(n == 201 and p.done_text, "Appliquer : 201 contacts et bandeau « C'est fait »")
    t.check(len(p.history) == 1, "action ajoutée à l'historique")
    t.check(not any("Email" in i["titre"] and "doublons" in i["titre"] for i in p.ideas), "les idées sont recalculées après l'action")
    p.on_annuler()
    n = len(dialog.actions.Table(doc.Sheets.getByIndex(0)).rows)
    t.check(n == 305, "Annuler cette action : retour à 305 lignes")

    p.c["demande"].setText("moyenne des devis par ville")
    p.on_proposer()
    t.check(p.state == "proposition" and "oyenne" in label("prop_t"), "demande libre : proposition du modèle local")
    p.on_modifier()
    t.check(p.state == "main", "Modifier ma demande : retour à l'accueil")

    STATE["models"] = []
    p.check_setup()
    t.check(p.state == "setup" and "modèle" in label("setup_t"), "modèle absent : écran d'installation")
    p.on_dl()
    t.check(p.state == "main", "téléchargement du modèle depuis le panneau, puis accueil")

    cfg["url"] = "http://localhost:1"
    p.cfg["url"] = "http://localhost:1"
    p.check_setup()
    t.check(p.state == "setup" and "Ollama" in label("setup_t"), "Ollama absent : écran d'installation avec lien")
    p.layout()
    t.check(p.height_px > 100, "mise en page calculée (%d px)" % p.height_px)

    doc.close(True)
    srv.shutdown()
    print("TOUS LES TESTS PASSENT" if not t.check.failed else "%d échec(s)" % t.check.failed)
    sys.exit(1 if t.check.failed else 0)


if __name__ == "__main__":
    main()
