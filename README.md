# IA locale pour Calc

Une extension pour LibreOffice Calc qui permet de demander en français « supprime les doublons sur l'email » ou « fais-moi le total des devis par ville », avec une IA qui tourne entièrement sur votre ordinateur.

100 % libre, 100 % local, et toujours sous votre contrôle. L'IA propose, vous voyez l'aperçu, et rien ne change tant que vous n'avez pas cliqué sur Appliquer.

> **C'est une preuve de concept, pas un produit fini.** Elle sert à montrer qu'on peut déjà utiliser l'IA dans un tableur libre sans envoyer ses données sur Internet. Testez-la, réutilisez-la, améliorez-la. Mais travaillez sur une copie de vos fichiers.

## Pourquoi

Les assistants d'IA intégrés aux tableurs (Copilot, ChatGPT, Claude…) envoient le contenu de vos tableaux sur des serveurs distants. Pour un fichier clients, RH ou comptable, ce n'est pas anodin. Et chaque nouvel usage renforce notre dépendance à quelques grands acteurs.

L'idée est simple. Un logiciel libre (LibreOffice), un modèle d'IA ouvert qui tourne chez vous (via Ollama), et un fonctionnement qui garde l'humain aux commandes.

## Comment ça marche

1. Le panneau analyse votre tableau et propose des idées adaptées (colonnes mal écrites, téléphones à harmoniser, doublons, totaux possibles). Vous cliquez sur une idée, ou vous écrivez votre demande en français.
2. Le modèle local reçoit uniquement les noms des colonnes et votre phrase, jamais le contenu des cellules. Il choisit une action dans une liste fermée, avec ses paramètres.
3. L'extension calcule elle-même ce qui va changer et vous montre un aperçu (nombre de cellules, exemples avant/après, avertissements).
4. Vous cliquez sur Appliquer, ou pas. Le bouton « Annuler la dernière action » revient en arrière, y compris pour un tableau croisé ou un graphique (la feuille créée est retirée).

Le modèle ne touche jamais aux cellules. C'est ce choix qui rend l'outil rapide (quelques secondes) et fiable avec un petit modèle, là où les assistants « qui font tout » échouent sur un ordinateur ordinaire.

## Ce qu'il sait faire

| Action | Exemples de demandes |
|---|---|
| Nettoyer une colonne de texte | « uniformise les villes », « mets les noms en majuscules », « passe les emails en minuscules » |
| Formater des téléphones français | « mets les téléphones au format 06 12 34 56 78 » |
| Supprimer les doublons | « supprime les doublons sur l'email » |
| Tableau croisé dynamique | « total des devis par ville », « combien de contacts par secteur ? » |
| Graphique (barres, courbe, camembert) | « un camembert des montants par secteur » |
| Trier | « trie par montant du plus grand au plus petit » |

Pour toute autre demande (envoyer un mail, traduire, rédiger…), l'assistant répond qu'il ne sait pas faire. C'est voulu.

## Ce qu'il vous faut

- LibreOffice 7.0 ou plus récent ([libreoffice.org](https://fr.libreoffice.org/download/telecharger-libreoffice/)).
- Ollama, le logiciel qui fait tourner les modèles d'IA en local ([ollama.com](https://ollama.com/download)).
- Un ordinateur avec 8 Go de RAM au minimum, 16 Go conseillés. Pas besoin de carte graphique.
- Environ 3 Go d'espace disque pour le modèle.

## Installation (environ 10 minutes)

**1. Installez Ollama**, puis ouvrez un terminal (sous Windows, touche Windows, tapez `cmd`, Entrée) et téléchargez le modèle conseillé :

```
ollama pull qwen3:4b
```

**2. Téléchargez l'extension** : le fichier `calc-ia-locale.oxt` dans la page [Releases](../../releases) de ce dépôt.

**3. Installez-la dans LibreOffice** : double-cliquez sur le fichier `.oxt`, ou dans LibreOffice ouvrez *Outils > Gestionnaire des extensions > Ajouter*. Fermez complètement LibreOffice, puis rouvrez-le.

**4. Ouvrez un tableau dans Calc.** Cliquez sur l'icône « IA » de la barre d'outils, ou sur le menu *IA locale > Ouvrir le panneau IA locale*. Le panneau s'ouvre à droite du tableau, comme Copilot dans Excel. S'il manque Ollama ou le modèle, il vous guide, et le modèle se télécharge directement depuis le panneau.

Sous Linux, il faut parfois installer en plus le paquet `libreoffice-script-provider-python`.

## Premier essai

Le dossier `exemples/` contient `contacts-fictifs.ods`, un fichier de 305 contacts inventés, volontairement mal tenu (doublons, villes mal saisies, téléphones dans quatre formats). Ouvrez-en une copie et essayez dans l'ordre :

1. « uniformise la colonne Ville »
2. « mets les téléphones au format 06 12 34 56 78 »
3. « supprime les doublons sur l'email », il doit rester 201 contacts
4. « total des devis par ville »
5. « fais un graphique en barres du total des devis par ville »

## Confidentialité et sécurité

- L'extension ne parle qu'à Ollama sur votre ordinateur, et refuse toute autre adresse. Elle n'utilise ni proxy ni redirection.
- Le modèle ne reçoit que les noms des colonnes et votre demande, jamais le contenu des cellules. Un test automatique le vérifie.
- Rien n'est modifié sans votre clic sur Appliquer, et chaque action s'annule d'un clic.
- Aucun programme lancé, aucun droit administrateur, aucun suivi.

Le détail, et la manière de tout vérifier vous-même, est dans [SECURITE.md](SECURITE.md).

## Limites connues

- Six actions seulement. Ce n'est pas un Copilot généraliste.
- Le tableau doit commencer par une ligne d'en-têtes, et l'assistant travaille sur la feuille active. Après la création d'un tableau croisé ou d'un graphique, revenez sur la feuille de données avant la demande suivante.
- Le modèle se trompe parfois sur un détail (ordre de tri, majuscules). Lisez toujours l'aperçu avant d'appliquer.
- Les dates saisies comme du texte se trient par ordre alphabétique, pas chronologique (l'aperçu vous prévient).
- Les téléphones gérés sont les numéros français à 10 chiffres.

## Ce que nos tests ont montré

Sur un PC portable ordinaire (16 Go de RAM, processeur AMD, sans carte graphique) :

- Un assistant généraliste existant, piloté par des modèles locaux de 3 à 7 milliards de paramètres, n'a réussi aucune tâche de nettoyage (réflexion sans fin, plan jamais exécuté, ou colonnes écrasées par erreur).
- Avec l'approche de cette extension (liste fermée d'actions), nous avons comparé neuf petits modèles ouverts sur 20 demandes de test. Les quatre meilleurs :

| Modèle | Bonnes réponses | Temps moyen | Mémoire | Licence |
|---|---|---|---|---|
| qwen3:4b (par défaut) | 20/20 | 5,8 s | 3,2 Go | Apache 2.0 |
| qwen2.5:3b | 18/20 | 5,1 s | 2,2 Go | Qwen Research (à vérifier) |
| qwen3:1.7b | 17/20 | 4,2 s | 1,9 Go | Apache 2.0 |
| granite3.3:2b | 16/20 | 4,4 s | 2,0 Go | Apache 2.0 |

Avec 8 Go de RAM, préférez `qwen3:1.7b`, plus léger. Le script `tests/benchmark_modeles.mjs` permet de refaire la comparaison chez vous.

Ce sont des mesures sur un jeu de 20 demandes, rédigé par nous et ayant servi à mettre au point la consigne. Vos résultats peuvent varier.

## Dépannage

- **« Ollama ne répond pas »** : lancez Ollama depuis le menu Démarrer (son icône apparaît près de l'horloge), puis réessayez.
- **« Le modèle n'est pas installé »** : tapez `ollama pull qwen3:4b` dans un terminal.
- **Le menu IA locale n'apparaît pas** : vérifiez dans *Outils > Gestionnaire des extensions* que l'extension est activée, puis redémarrez LibreOffice en entier (y compris le démarrage rapide, s'il est actif).
- **Changer de modèle** : tapez son nom dans le champ « Modèle » de la fenêtre. Le choix est mémorisé.

## Pour les curieux

```
extension/            le code de l'extension (Python)
  pythonpath/calc_ia/
    llm.py            dialogue avec Ollama (consigne courte, réponse JSON contrainte)
    actions.py        les six actions, avec aperçu et annulation
    dialog.py         la fenêtre
tests/                tests automatiques avec LibreOffice sans interface
exemples/             fichier de test
build.py              fabrique dist/calc-ia-locale.oxt
```

Pour lancer les tests : démarrez `soffice --headless --accept="socket,host=localhost,port=2002;urp;"`, puis `python3 tests/test_actions.py` et `python3 tests/test_bout_en_bout.py`.

Les contributions sont bienvenues : nouvelles actions, autres formats de téléphone, traductions.

## Licence

MIT. Voir le fichier [LICENSE](LICENSE).

Projet de Frédéric Dol, réalisé avec l'aide de Claude.
