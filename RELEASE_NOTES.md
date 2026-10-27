# Version 0.4.1

Preuve de concept. Testée sur Windows (LibreOffice 26.8) et Linux (LibreOffice 24.2). Non testée sur Mac.

## Correctif 0.4.1
- Aide « Comment ça marche ? » : bouton Retour placé en haut, et un second clic sur l'aide la referme. On ne peut plus rester bloqué sur cet écran.

## Nouveautés de la 0.4
- Panneau latéral inspiré de Copilot : idées calculées sur votre tableau (Nettoyer, Analyser), demande en français, aperçu chiffré, historique.
- Installation guidée : le panneau vérifie Ollama et télécharge le modèle en un clic.
- Prudence : actions sensibles signalées, copie de sauvegarde en un clic, harmonisation proposée avant une analyse sur une colonne mal écrite, aide « Comment ça marche ? ».
- Intégrité des données : formules jamais modifiées, données voisines du tableau préservées, feuilles protégées refusées.
- Sécurité : connexion strictement locale, sans proxy ni redirection. Interface jamais figée, bouton Arrêter.
- Modèle par défaut : qwen3:4b (Apache 2.0).

## Vérifier le fichier
SHA-256 de calc-ia-locale.oxt :
67fe06ca9988d09c1556db392a0ee17f4dc73bd4f5cfaf2759bef1e6efd7be77

Sous Windows : certutil -hashfile calc-ia-locale.oxt SHA256
