# -*- coding: utf-8 -*-
"""Test de bout en bout sans vrai modèle : un faux serveur Ollama renvoie des
réponses préparées, et on pilote la fenêtre de l'assistant comme un utilisateur.
Lancer d'abord : soffice --headless --accept="socket,host=localhost,port=2002;urp;"
puis : python3 tests/test_bout_en_bout.py"""
import json, os, shutil, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "extension", "pythonpath"))
import test_actions as t  # noqa: E402
from calc_ia import dialog  # noqa: E402

REPONSES = {
    "nettoie les villes": {"action": "normaliser_texte", "colonne": "Ville", "casse": "premiere_lettre_majuscule"},
    "doublons email": {"action": "supprimer_doublons", "colonne": "Email"},
    "envoie un mail": {"action": "aucune", "colonne": ""},
}
RECU = []


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"models": [{"name": "qwen2.5:3b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        RECU.append(body)
        demande = body["messages"][-1]["content"]
        self._send({"message": {"content": json.dumps(REPONSES[demande])}})


def main():
    srv = HTTPServer(("localhost", 11999), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dialog.CONFIG = os.path.join(tempfile.mkdtemp(), "cfg.json")
    dialog.DEFAULTS["url"] = "http://localhost:11999"

    import uno
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    rctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    desktop = rctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", rctx)
    tmp = os.path.join(tempfile.mkdtemp(), "contacts.ods")
    shutil.copy(os.path.join(HERE, "..", "exemples", "contacts-fictifs.ods"), tmp)
    doc = t.load(desktop, tmp)
    a = dialog.Assistant(rctx, doc)

    def ask(text):
        a.dlg.getControl("demande").setText(text)
        a.on_proposer()
        return a.dlg.getControl("apercu").getText()

    out = ask("nettoie les villes")
    print(out, "\n")
    t.check("76 cellule(s)" in out, "aperçu du nettoyage affiché")
    t.check(a.model.getByName("appliquer").Enabled, "bouton Appliquer activé après proposition")
    villes_avant = set(dialog.actions.Table(doc.Sheets.getByIndex(0)).column("Ville"))
    t.check(len(villes_avant) > 8, "rien n'est modifié avant de cliquer sur Appliquer")
    a.on_appliquer()
    print(a.dlg.getControl("apercu").getText(), "\n")
    villes = set(dialog.actions.Table(doc.Sheets.getByIndex(0)).column("Ville"))
    t.check(len(villes) == 8, "villes nettoyées après Appliquer")

    out = ask("doublons email")
    a.on_appliquer()
    n = len(dialog.actions.Table(doc.Sheets.getByIndex(0)).rows)
    t.check(n == 201, "201 contacts après dédoublonnage via la fenêtre")

    out = ask("envoie un mail")
    print(out, "\n")
    t.check(not a.model.getByName("appliquer").Enabled, "demande hors périmètre refusée, Appliquer désactivé")

    sent = json.dumps(RECU)
    t.check("Lefebvre" not in sent and "@exemple.fr" not in sent,
            "aucune donnée de cellule envoyée au modèle (seulement les noms de colonnes)")

    dialog.DEFAULTS["url"] = "http://localhost:1"
    a.cfg["url"] = "http://localhost:1"
    out = ask("nettoie les villes")
    print(out, "\n")
    t.check("Ollama ne répond pas" in out, "message clair si Ollama est éteint")

    doc.close(True)
    srv.shutdown()
    print("TOUS LES TESTS PASSENT" if not t.check.failed else "%d échec(s)" % t.check.failed)
    sys.exit(1 if t.check.failed else 0)


if __name__ == "__main__":
    main()
