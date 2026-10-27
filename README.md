# IA locale pour Calc

Un petit assistant d'IA pour LibreOffice Calc, inspiré de Copilot dans Excel, mais qui fonctionne entièrement sur votre ordinateur. Il repère ce qui peut être amélioré dans votre tableau, comprend des demandes en français comme « supprime les doublons sur l'email » ou « total des devis par ville », et vous montre ce qui va changer avant de le faire.

Logiciel libre, modèle d'IA ouvert, aucune donnée envoyée sur Internet, et toujours sous votre contrôle. L'IA propose, vous validez.

> **Une preuve de concept, pas un produit fini.** Elle montre qu'on peut déjà utiliser l'IA dans un tableur libre en gardant la maîtrise de ses données. Elle a été testée sur Windows et Linux, pas encore sur Mac. Par précaution, travaillez sur une copie de vos fichiers importants.

## Pourquoi

Les assistants d'IA intégrés aux tableurs envoient le contenu de vos tableaux sur des serveurs distants. Pour un fichier clients, RH ou comptable, ce n'est pas anodin. L'idée ici est de garder les données sur le poste, avec des outils libres, et de laisser à l'humain la décision finale.

## Comment ça marche, en clair

1. Le panneau, à droite du tableau, analyse vos colonnes et propose des idées : une colonne mal écrite à harmoniser, des téléphones à mettre au même format, des doublons, un total ou un graphique utile. Ces idées sont calculées par l'extension elle-même, sans IA.
2. Pour une demande libre, un petit modèle d'IA, installé sur votre PC, lit seulement les noms de vos colonnes et votre phrase. Il choisit une action parmi six, et le panneau vous dit ce qu'il a compris.
3. L'extension calcule l'aperçu : combien de cellules changent, des exemples avant et après, et les avertissements utiles (colonne mal écrite, formules préservées, lignes supprimées).
4. Vous appliquez, ou pas. Un bouton annule l'action juste après. Avant une suppression, un bouton enregistre une copie de sauvegarde.

Le rôle de l'IA est volontairement limité : comprendre votre demande. Tout le reste est fait par un code prévisible et lisible. C'est ce qui rend l'outil rapide (quelques secondes) et fiable avec un petit modèle, sur un ordinateur ordinaire.

## Ce qu'il sait faire, et ce qu'il ne fait pas

| Nettoyer | Analyser |
|---|---|
| Harmoniser l'écriture d'une colonne (« Lyon », « LYON », « lyon ») | Tableau croisé dynamique : total, moyenne, nombre |
| Mettre en majuscules ou en minuscules | Graphique en barres, courbe ou camembert |
| Formater des téléphones français (06 12 34 56 78) | |
| Supprimer les doublons | |
| Trier le tableau | |

Il ne sait pas rédiger ou traduire du texte, écrire des formules, fusionner des fichiers ni envoyer des mails. Il le dit quand une demande sort de son périmètre.

## Ce qu'il vous faut

- LibreOffice 7.0 ou plus récent ([libreoffice.org](https://fr.libreoffice.org/download/telecharger-libreoffice/)).
- Ollama, le logiciel libre qui fait tourner le modèle sur votre PC ([ollama.com](https://ollama.com/download)).
- 8 Go de RAM au minimum, 16 Go conseillés. Pas besoin de carte graphique.
- Environ 3 Go d'espace disque, et une connexion Internet une seule fois, pour télécharger le modèle.

## Installation en trois étapes (environ 10 minutes, sans terminal)

1. **Installez Ollama** depuis son site officiel, puis lancez-le (son icône apparaît près de l'horloge).
2. **Installez l'extension** : téléchargez `calc-ia-locale.oxt` dans la page [Releases](../../releases), double-cliquez dessus, puis fermez et rouvrez LibreOffice.
3. **Ouvrez un tableau dans Calc** et cliquez sur l'icône « IA » de la barre d'outils (ou menu *IA locale*). Le panneau vérifie l'installation et propose de télécharger le modèle en un clic.

Le pas-à-pas illustré, avec les réponses aux questions courantes, est dans le [guide](GUIDE.md).

## Confiance et sécurité

- L'extension ne communique qu'avec Ollama sur votre ordinateur et refuse toute autre adresse, sans proxy ni redirection.
- Le modèle ne reçoit jamais le contenu des cellules.
- Les formules ne sont jamais modifiées, les données voisines du tableau ne bougent pas, une feuille protégée n'est pas touchée.
- Aucun programme lancé, aucun droit administrateur, aucun suivi d'usage.

Tout cela se vérifie : le détail et la méthode sont dans [SECURITE.md](SECURITE.md). Pensez à tenir Ollama à jour, comme tout logiciel installé.

## Ce que nos tests ont montré

Sur un PC portable ordinaire (16 Go de RAM, sans carte graphique), un assistant généraliste existant piloté par des modèles locaux n'a réussi aucune tâche de nettoyage. Avec l'approche de cette extension, nous avons comparé neuf petits modèles ouverts sur 20 demandes de test :

| Modèle | Bonnes réponses | Temps moyen | Mémoire | Licence |
|---|---|---|---|---|
| qwen3:4b (par défaut) | 20/20 | 5,8 s | 3,2 Go | Apache 2.0 |
| qwen2.5:3b | 18/20 | 5,1 s | 2,2 Go | licence Qwen, à vérifier |
| qwen3:1.7b (conseillé avec 8 Go) | 17/20 | 4,2 s | 1,9 Go | Apache 2.0 |
| granite3.3:2b | 16/20 | 4,4 s | 2,0 Go | Apache 2.0 |

Ces chiffres sont indicatifs : 20 demandes rédigées par nous, qui ont aussi servi à régler la consigne. Le script `tests/benchmark_modeles.mjs` permet de refaire la mesure chez vous. Le moteur d'actions est par ailleurs testé automatiquement sur huit tableaux différents (titres au-dessus du tableau, vraies dates, codes article, formules, second tableau à côté, 5 000 lignes, en-têtes en anglais).

## Pour les curieux et les contributeurs

```
extension/pythonpath/calc_ia/
  panel.py     le panneau latéral
  suggest.py   les idées calculées sans IA
  llm.py       le seul fichier qui communique (avec Ollama, en local)
  actions.py   les six actions, avec aperçu, prudence et annulation
tests/         tests automatiques avec LibreOffice sans interface
exemples/      fichier d'essai
```

Les contributions sont bienvenues : retours sur vos fichiers réels, tests sur Mac, nouvelles actions, autres formats de téléphone.

## Licence et transparence

Code sous licence MIT. Projet de Frédéric Dol, développé avec l'aide de Claude (Anthropic). L'outil lui-même ne fait appel à aucun service en ligne.
