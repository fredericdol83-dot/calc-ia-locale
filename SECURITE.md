# Sécurité et transparence

Cette page explique précisément ce que fait l'extension, ce qu'elle ne fait pas, et comment le vérifier vous-même. Le code est court et entièrement lisible dans le dossier `extension/`.

## Ce qui circule, et où

| Échange | Destination | Contenu |
|---|---|---|
| Choisir une action | Ollama sur votre ordinateur (`http://localhost:11434`) | les noms des colonnes et votre phrase |
| Vérifier l'installation | Ollama sur votre ordinateur | la liste des modèles installés |
| Télécharger le modèle (une seule fois, sur votre clic) | Ollama, qui le récupère depuis sa bibliothèque officielle | le nom du modèle |
| Bouton « Télécharger Ollama » | votre navigateur, page officielle ollama.com | aucune donnée |

Le contenu des cellules n'est jamais envoyé au modèle. Les idées affichées dans le panneau (colonnes mal écrites, doublons, totaux) sont calculées par l'extension elle-même, sans IA.

Une fois le modèle téléchargé, tout fonctionne sans connexion Internet. Pour le vérifier, coupez le Wi-Fi et utilisez l'extension normalement.

## Les garde-fous du code

- **Uniquement en local.** L'extension refuse de parler à une autre adresse que `localhost`, `127.0.0.1` ou `::1`. Si quelqu'un modifie le réglage pour pointer vers un serveur extérieur, la connexion est refusée et le panneau l'affiche en rouge (fichier `llm.py`, fonction `_check_url`).
- **Aucun proxy, aucune redirection.** Même si un proxy est configuré sur le PC (cas fréquent en entreprise), l'extension ne l'utilise pas et n'accepte aucune redirection vers une autre adresse.
- **Le modèle ne touche à rien.** Il répond dans un format imposé et ne peut que choisir une action parmi six, sur une colonne qui existe. Il ne peut ni écrire dans les cellules, ni lancer de programme, ni lire le disque.
- **Rien sans votre accord.** Chaque action affiche d'abord un aperçu, et ne s'applique qu'après un clic sur Appliquer. Le bouton « Annuler cette action » revient en arrière.
- **Aucune commande système.** L'extension n'exécute aucun programme, aucun script téléchargé, et ne demande aucun droit administrateur. Elle n'utilise que la bibliothèque standard de Python fournie avec LibreOffice.
- **Aucun suivi.** Pas de statistiques d'usage, pas de compte, pas de cookie, pas d'appel vers nos serveurs (nous n'en avons pas).
- **Un seul fichier écrit.** Le réglage du modèle choisi, dans `.calc-ia-locale.json`, dans votre dossier personnel.

## Ce que l'extension ne garantit pas

- Votre ordinateur reste exposé aux risques habituels (vol, virus, absence de sauvegarde). « Local » ne veut pas dire « invulnérable ».
- Le modèle peut se tromper sur un détail. C'est pour cela que l'aperçu est obligatoire : lisez-le avant d'appliquer, et travaillez sur une copie de vos fichiers importants.
- Ollama et le modèle sont des logiciels tiers, téléchargés depuis leurs sources officielles. Leur sécurité relève de leurs éditeurs (Ollama, Alibaba pour Qwen3, sous licence Apache 2.0).

## Vérifier par vous-même

1. **Lire le code.** Tout est dans `extension/pythonpath/calc_ia/`. Les seuls appels réseau sont dans `llm.py`.
2. **Couper Internet.** L'extension continue de fonctionner une fois le modèle installé.
3. **Vérifier le fichier téléchargé.** L'empreinte SHA-256 du fichier `.oxt` est publiée avec chaque version. Sous Windows : `certutil -hashfile calc-ia-locale.oxt SHA256`.
4. **Ouvrir le fichier .oxt.** C'est une simple archive ZIP. Renommez-la en `.zip` pour voir son contenu.

## Signaler un problème

Ouvrez une « issue » sur GitHub. Pour une faille de sécurité, merci de la signaler en privé à l'auteur avant de la rendre publique.
