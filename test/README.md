# Banc de test bout-en-bout — MedVision AI Pro

Pilote l'application réelle (`index.html`) dans un navigateur headless, avec une
API Mistral simulée. Aucune clé, aucun appel réseau, aucune image patient.

## Installation

    npm install jsdom canvas

## Exécution

    node test/e2e.js index.html nominal
    node test/e2e.js index.html rate-limit
    node test/e2e.js index.html lot-perdu
    node test/e2e.js index.html tronque

Code de sortie 1 si un contrôle échoue — utilisable en pré-déploiement.

## Ce que chaque scénario vérifie

| Scénario     | Vérifie |
|--------------|---------|
| `nominal`    | Chaîne complète : clé → image → /v1/models → triage → lectures → consensus → compte rendu rendu à l'écran |
| `rate-limit` | Un 429 avec `Retry-After` sur le triage est repris par le gouverneur de débit et l'analyse aboutit |
| `lot-perdu`  | Une lecture experte définitivement perdue (403) est **signalée** au lieu d'être silencieusement absorbée |
| `tronque`    | Une réponse coupée, récupérée partiellement, est **signalée** dans le compte rendu |

Les deux derniers sont les régressions médicalement critiques : avant v14.4, une
matière perdue devenait indiscernable d'un finding écarté.

## Limites

Ce banc prouve que le code s'exécute et que les gardes fonctionnent. Il ne dit
rien de la performance diagnostique : les réponses du modèle sont simulées.
