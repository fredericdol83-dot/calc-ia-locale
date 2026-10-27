# Version 0.4.0

Preuve de concept. Testée sur Windows (LibreOffice 26.8) et Linux (LibreOffice 24.2). Non testée sur Mac.

## Nouveautés
- Panneau latéral inspiré de Copilot : idées calculées sur votre tableau (Nettoyer, Analyser), demande en français, aperçu chiffré, historique.
- Installation guidée : le panneau vérifie Ollama et télécharge le modèle en un clic.
- Prudence : actions sensibles signalées, copie de sauvegarde en un clic, harmonisation proposée avant une analyse sur une colonne mal écrite, aide « Comment ça marche ? ».
- Intégrité des données : formules jamais modifiées, données voisines du tableau préservées, feuilles protégées refusées.
- Sécurité : connexion strictement locale, sans proxy ni redirection. Interface jamais figée, bouton Arrêter.
- Modèle par défaut : qwen3:4b (Apache 2.0).

## Vérifier le fichier
SHA-256 de calc-ia-locale.oxt :
cff422b5343a71e952c3d70472894a2fe2b0dbb90b389657ee775401086a2a06

Sous Windows : certutil -hashfile calc-ia-locale.oxt SHA256
