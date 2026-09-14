# Tests techniques MedVision

Installer les dépendances avec `npm install --ignore-scripts`, puis exécuter `npm test` (Node.js 22+).

Le banc exécute le JavaScript de `index.html`, le décodage d’images, Canvas et WebCrypto dans un hôte Node. Le DOM et les réponses du fournisseur IA sont simulés. Aucun examen réel, aucune clé réelle et aucun appel facturable.

- `e2e.js` : parcours d’import et pipeline complet ; nominal, limite temporaire 429, lecture perdue, JSON tronqué, quota épuisé.
- `regressions.cjs` : paramètres invalides, modèles vision, résultat général visible, import partiellement invalide, conservation des annotations, indices ROI, format MedGemma, annulation, examens indépendants, chiffrement/restauration et formats JSON.
- `service-worker.cjs` : exclusion des données du cache, installation hors ligne incomplète, navigation hors ligne.
- `runtime.cjs` : hôte d’exécution du code réel et adaptateur Canvas ; ce n’est pas un moteur de navigateur.
- `run.cjs` : syntaxe, cohérence des versions et exécution de l’ensemble des tests.

Les tests ne prouvent ni la conformité des mises en page sur chaque appareil, ni la disponibilité de votre compte fournisseur, ni la pertinence clinique d’une réponse IA.

Le banc clinique expérimental `bench.js` reste séparé ; voir `BENCH.md` pour ses dépendances et prérequis. Il n’est jamais lancé par `npm test`.
