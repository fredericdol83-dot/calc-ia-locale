# Contribuer

Ce projet est une expérimentation personnelle, partagée librement. Vous pouvez le reprendre, l'adapter ou l'améliorer comme vous le souhaitez, dans le respect de la licence MIT.

## Signaler un problème ou proposer une idée

Ouvrez une « issue » sur GitHub en décrivant :

- ce que vous avez demandé, ou l'idée sur laquelle vous avez cliqué ;
- ce que le panneau a proposé, et ce que vous attendiez ;
- votre système (Windows, Linux, Mac), la version de LibreOffice et le modèle utilisé.

## Protégez vos données

Ne joignez jamais vos fichiers réels, ni des captures où l'on voit des données personnelles. Une description suffit. Si un exemple est nécessaire, recréez quelques lignes avec des valeurs inventées, ou partez du fichier `exemples/contacts-fictifs.ods`.

## Proposer du code

1. Créez une copie du dépôt (« fork ») et une branche.
2. Faites votre modification. Les seuls appels réseau doivent rester dans `llm.py`, vers l'ordinateur local.
3. Lancez les tests avec LibreOffice sans interface (voir l'en-tête des fichiers dans `tests/`).
4. Ouvrez une « pull request » en expliquant le pourquoi de la modification.

Les contributions qui ajoutent un envoi de données vers Internet, un suivi d'usage ou une dépendance extérieure ne seront pas acceptées, puisque c'est tout l'objet du projet.
