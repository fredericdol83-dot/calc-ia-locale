# -*- coding: utf-8 -*-
"""Dialogue avec le modèle local (Ollama). Rien ne quitte l'ordinateur :
l'adresse par défaut est http://localhost:11434.

Le modèle ne reçoit que les NOMS des colonnes et la demande, jamais le contenu
des cellules. Il répond par un JSON contraint (liste fermée d'actions)."""
import json
import urllib.request
import urllib.error

ACTIONS = ["normaliser_texte", "formater_telephone", "supprimer_doublons",
           "tableau_croise", "graphique", "trier", "aucune"]


def schema(headers):
    cols = list(headers) + [""]
    return {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ACTIONS},
            "colonne": {"type": "string", "enum": cols},
            "casse": {"type": "string", "enum": ["premiere_lettre_majuscule", "tout_en_majuscules", "tout_en_minuscules", ""]},
            "colonne_valeurs": {"type": "string", "enum": cols},
            "operation": {"type": "string", "enum": ["somme", "moyenne", "nombre", ""]},
            "type_graphique": {"type": "string", "enum": ["barres", "courbe", "camembert", ""]},
            "ordre": {"type": "string", "enum": ["croissant", "decroissant", ""]},
        },
        "required": ["action", "colonne", "casse", "colonne_valeurs", "operation", "type_graphique", "ordre"],
    }


def system_prompt(headers):
    return (
        "Tu traduis une demande d'utilisateur de tableur en UNE action parmi une liste fermée. "
        "Tu ne modifies rien toi-même.\n"
        "Colonnes du tableau : " + ", ".join(headers) + ".\n"
        "Actions possibles :\n"
        "- normaliser_texte : nettoyer une colonne de texte (espaces superflus, casse). Champs : colonne, casse. "
        "casse = premiere_lettre_majuscule (Dupont, Saint-Malo), tout_en_majuscules (DUPONT), "
        "tout_en_minuscules (dupont), ou vide pour ne changer que les espaces.\n"
        "- formater_telephone : harmoniser ou mettre au format 06 12 34 56 78 une colonne de numéros de téléphone "
        "(tel, numéros, portables). Champ : colonne.\n"
        "- supprimer_doublons : supprimer les lignes en double selon une colonne. Champ : colonne.\n"
        "- tableau_croise : regrouper par une colonne et calculer sur une autre. Champs : colonne (regroupement), "
        "colonne_valeurs, operation (somme, moyenne, ou nombre pour compter des lignes).\n"
        "- graphique : graphique d'une colonne de valeurs par catégorie. Champs : colonne (catégories), "
        "colonne_valeurs, type_graphique (camembert = graphique circulaire), operation.\n"
        "- trier : trier le tableau. Champs : colonne, ordre. decroissant = du plus grand au plus petit, "
        "de Z à A, du plus récent au plus ancien. croissant = du plus petit au plus grand, de A à Z, "
        "les plus anciens d'abord.\n"
        "- aucune : la demande ne porte pas sur une de ces actions (envoyer un mail, traduire, rédiger, "
        "calculer autre chose, etc.).\n"
        "Laisse vide (\"\") tout champ inutile pour l'action choisie."
    )


class LLMError(Exception):
    pass


def _post(url, payload, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def installed_models(base_url, timeout=5):
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=timeout) as r:
            return [m["name"] for m in json.loads(r.read().decode("utf-8")).get("models", [])]
    except Exception:
        raise LLMError("Ollama ne répond pas sur %s.\nLancez Ollama (menu Démarrer), puis réessayez." % base_url)


def choose_action(base_url, model, headers, demande, timeout=180):
    models = installed_models(base_url)
    if model not in models and model + ":latest" not in models:
        raise LLMError("Le modèle « %s » n'est pas installé.\nDans un terminal, tapez : ollama pull %s"
                       % (model, model))
    payload = {
        "model": model, "stream": False, "format": schema(headers),
        "options": {"temperature": 0, "num_ctx": 4096},
        "messages": [{"role": "system", "content": system_prompt(headers)},
                     {"role": "user", "content": demande}],
    }
    # mode « réflexion » désactivé : inutile pour choisir dans une liste, et très lent sur CPU
    payload["think"] = False
    try:
        try:
            res = _post(base_url.rstrip("/") + "/api/chat", payload, timeout)
        except urllib.error.HTTPError as e:
            if "think" not in e.read().decode("utf-8", "ignore").lower():
                raise
            del payload["think"]  # modèle ou version d'Ollama sans ce réglage
            res = _post(base_url.rstrip("/") + "/api/chat", payload, timeout)
    except urllib.error.URLError as e:
        raise LLMError("Erreur de communication avec Ollama : %s" % e)
    except Exception as e:
        raise LLMError("Le modèle n'a pas répondu à temps (%s)." % e)
    try:
        return json.loads(res["message"]["content"])
    except Exception:
        raise LLMError("Réponse du modèle illisible. Reformulez votre demande.")


def pull_model(base_url, model, progress=None, timeout=3600):
    """Télécharge un modèle via Ollama. progress(texte, fraction ou None) est appelé au fil de l'eau."""
    req = urllib.request.Request(base_url.rstrip("/") + "/api/pull",
                                 data=json.dumps({"model": model, "stream": True}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:
                if not line.strip():
                    continue
                ev = json.loads(line.decode("utf-8"))
                if ev.get("error"):
                    raise LLMError("Téléchargement impossible : %s" % ev["error"])
                total, done = ev.get("total"), ev.get("completed")
                frac = (done / total) if total and done else None
                if progress:
                    progress(ev.get("status", ""), frac)
                if ev.get("status") == "success":
                    return True
    except urllib.error.URLError as e:
        raise LLMError("Ollama ne répond pas : %s" % e)
    return True
