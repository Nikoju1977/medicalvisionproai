# Banc de mesure A/B — Medical Skills Engine

Le banc `test/bench.js` exécute le **pipeline réel** sur un lot d'images annotées. Son mode A/B compare, pour chaque cas, la même version de MedVision avec les mêmes réglages :

- **baseline** : Medical Skills Engine neutralisé par un hook réservé au benchmark ;
- **skills** : Medical Skills Engine actif.

Le hook A/B n'est honoré que si `__MEDVISION_BENCH_MODE === true`. Il n'existe aucun bouton clinique pour désactiver les skills. Les couches de preuves, double lecture, critique, quantitatif, contrôle qualité et validation humaine restent identiques dans les deux conditions.

## 1. Préparer l'artefact

Construire d'abord la version de production :

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run build
```

Le mode `--ab` refuse un fichier qui ne contient pas `MEDICAL_SKILLS_ENGINE_V1`. Utiliser donc `dist/index.html`.

Le banc historique dépend de JSDOM et node-canvas, volontairement séparés des dépendances de production :

```bash
npm install --no-save jsdom canvas
```

## 2. Constituer le lot

Créer un dossier de cas avec les images et un manifeste JSON :

```json
[
  {
    "case_id": "cxr-normal-001",
    "file": "normal-001.png",
    "label": "normal"
  },
  {
    "case_id": "cxr-pna-001",
    "file": "pneumonia-001.png",
    "label": "anomalie",
    "attendu": "opacité alvéolaire basale droite",
    "expected_terms_any": [
      ["opacité", "condensation", "infiltrat"],
      ["droite", "right"]
    ]
  }
]
```

Champs principaux :

- `case_id` : identifiant stable pour l'appariement A/B ;
- `file` : chemin relatif au manifeste ;
- `label` : `normal` ou `anomalie` ;
- `attendu` : note libre pour la relecture humaine ;
- `expected_terms_any` : groupes lexicaux optionnels ; au moins un terme de chaque groupe doit apparaître pour compter le groupe comme couvert ;
- `forbidden_terms` : mentions lexicales optionnelles à surveiller.

Les contrôles lexicaux sont des aides d'audit, **pas** une métrique clinique. Ils ne comprennent pas correctement toutes les négations, synonymies ou nuances de contexte.

Pour une première comparaison exploitable, utiliser un lot équilibré et verrouillé avant l'essai. Un petit lot sert à détecter une régression logicielle ; il ne permet pas d'établir une performance clinique.

## 3. Lancer le benchmark A/B

Pour Mistral, préférer une variable d'environnement afin de ne pas placer la clé dans l'historique du shell :

```bash
MISTRAL_API_KEY="..." node test/bench.js dist/index.html cases/manifest.json --ab
```

Pour un endpoint privé OpenAI-compatible :

```bash
node test/bench.js dist/index.html cases/manifest.json \
  --ab \
  --base=http://localhost:11434/v1 \
  --model=medgemma:4b
```

Options utiles :

```text
--ab                       comparaison appariée baseline / skills
--baseline                 baseline seule
--single                   lecture unique
--nozoom                   désactive les passes zoom
--limit=N                  limite le nombre de cas
--sleep=1500               délai entre deux analyses
--out=bench-ab.csv         détails par cas
--summary=bench-ab.json    résumé statistique A/B
--allow-model-mismatch     conserve les paires dont le routage a utilisé des modèles différents
```

Par défaut, l'ordre est alterné : baseline→skills sur un cas, puis skills→baseline sur le suivant. Cela réduit un biais systématique lié à l'ordre, au cache ou à la charge du fournisseur.

## 4. Métriques produites

Pour chaque condition :

- sensibilité, spécificité et exactitude binaire avec intervalle de confiance Wilson à 95 % ;
- faux positifs rapportés par image normale ;
- échecs et examens non analysables ;
- latence médiane ;
- nombre moyen d'appels API ;
- volume moyen des corps de requête ;
- tokens prompt/completion/total lorsque le fournisseur renvoie un champ `usage` exploitable ;
- contrôles lexicaux optionnels du manifeste.

La comparaison appariée indique aussi :

- cas corrigés par les skills ;
- cas corrects en baseline devenus erronés avec skills ;
- nombre de paires utilisables ;
- paires exclues parce que les modèles réellement employés diffèrent ;
- test exact de McNemar sur les discordances ;
- deltas de sensibilité, spécificité et exactitude ;
- ratios de latence, volume de requête et tokens.

Le champ `model_signature` est construit à partir du routage réel `agentModelTrace`. Par défaut, une paire A/B utilisant des signatures différentes est exclue de l'analyse appariée.

## 5. Interprétation

Un résultat intéressant n'est pas seulement une hausse de sensibilité. Il faut regarder simultanément les faux positifs, les cas dégradés, la latence, les tokens et les discordances.

Le test de McNemar aide à déterminer si les changements de correction d'erreurs sont asymétriques. Sur de petits échantillons, il manque de puissance ; une valeur non significative ne prouve pas l'équivalence.

Les intervalles de confiance rappellent également qu'un pourcentage sur 20 ou 30 images reste très incertain.

## 6. Ce que ce banc ne prouve pas

Ce banc permet une **comparaison d'ingénierie** entre deux configurations du logiciel. Il ne constitue pas :

- une validation clinique ;
- une étude de sécurité diagnostique prospective ;
- une démonstration de généralisation à une population cible ;
- une certification de dispositif médical ;
- une preuve que les labels d'un jeu public représentent une vérité clinique exhaustive.

Pour une validation clinique, il faut un protocole pré-spécifié, des cas représentatifs, une référence de vérité indépendante, un plan statistique adapté et une revue professionnelle qualifiée.

## 7. Sorties

Le CSV contient une ligne par cas et par condition. Le JSON A/B conserve les résumés et les deltas afin de pouvoir comparer les versions dans le temps.

Exemple :

```text
bench-ab-resultats.csv
bench-ab-summary.json
```

Ces fichiers ne doivent pas contenir de données patient identifiantes.
