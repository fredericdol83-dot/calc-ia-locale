# Version 0.4.2

Preuve de concept. Testée sur Windows (LibreOffice 26.8) et Linux (LibreOffice 24.2). Non testée sur Mac. Fonctionnement hors connexion vérifié sur Windows (Wi-Fi coupé).

## Correctifs 0.4.1 et 0.4.2
- Indicateur « 100 % local » raccourci pour ne plus être tronqué (détail en info-bulle), avertissement d’harmonisation affiché en entier.
- Aide « Comment ça marche ? » : bouton Retour placé en haut, et un second clic sur l'aide la referme. On ne peut plus rester bloqué sur cet écran.

## Nouveautés de la 0.4
- Panneau latéral inspiré de Copilot : idées calculées sur votre tableau (Nettoyer, Analyser), demande en français, aperçu chiffré, historique.
- Installation guidée : le panneau vérifie Ollama et télécharge le modèle en un clic.
- Prudence : actions sensibles signalées, copie de sauvegarde en un clic, harmonisation proposée avant une analyse sur une colonne mal écrite, aide « Comment ça marche ? ».
- Intégrité des données : formules jamais modifiées, données voisines du tableau préservées, feuilles protégées refusées.
- Sécurité : connexion strictement locale, sans proxy ni redirection. Interface jamais figée, bouton Arrêter.
- Modèle par défaut : qwen3:4b (Apache 2.0).

## Vérifier le fichier
SHA-256 de calc-ia-locale-0.4.2.oxt :
bccd23d8664d12c5037eae8eb16fd43ad69a19d644a4f78790ba3b8e4bd35964

Sous Windows : certutil -hashfile calc-ia-locale-0.4.2.oxt SHA256
