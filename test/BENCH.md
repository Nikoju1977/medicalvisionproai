# Banc de mesure — sensibilité, spécificité, faux positifs

Le banc `e2e.js` prouve que la mécanique fonctionne. Celui-ci répond à la
seule question qui compte vraiment : **est-ce que l'application voit juste ?**

Il fait tourner le pipeline réel sur un lot d'images annotées et calcule
une matrice de confusion. Il ne simule rien — il lui faut un vrai modèle.

## 1. Constituer le lot

Créer un dossier `cases/` avec les images et un `manifest.json` :

```json
[
  { "file": "n001.png", "label": "normal" },
  { "file": "p012.png", "label": "anomalie", "attendu": "opacité alvéolaire LID" }
]
```

`label` vaut `normal` ou `anomalie`. `attendu` est facultatif, pour la
relecture humaine du CSV.

### Sources publiques annotées

| Jeu | Contenu | Lien |
|-----|---------|------|
| `hf-vision/chest-xray-pneumonia` | 5 863 radios thoraciques, NORMAL / PNEUMONIA | https://hf.co/datasets/hf-vision/chest-xray-pneumonia |
| `realsudarshan/chest-xray-tb-pneumonia` | 3 classes : normal, pneumonie, tuberculose | https://hf.co/datasets/realsudarshan/chest-xray-tb-pneumonia |
| `opencampus/chest-xray-pneumonia-3class-balanced` | Lot équilibré, pneumonie bactérienne / virale / normal | https://hf.co/datasets/opencampus/chest-xray-pneumonia-3class-balanced |

**Commencer petit** : 30 à 50 cas, moitié normaux, moitié pathologiques.
Un lot déséquilibré produit des chiffres flatteurs et faux.

## 2. Lancer

```
npm install jsdom canvas
node test/bench.js index.html cases/manifest.json --key=CLE_MISTRAL
node test/bench.js index.html cases/manifest.json --base=http://localhost:11434/v1 --model=medgemma:4b
```

Options : `--single` (lecture unique), `--nozoom`, `--limit=N`, `--out=fichier.csv`.

Le banc attend 1,5 s entre deux cas pour ne pas saturer le fournisseur.
Compter plusieurs minutes pour 50 cas en panel complet.

## 3. Lire le résultat

- **Sensibilité** — part des anomalies réelles détectées. Une valeur basse
  signifie que l'application rassure à tort. C'est le risque grave.
- **Spécificité** — part des examens normaux non sur-appelés. Une valeur
  basse noie le lecteur sous de fausses alertes et détruit la confiance.
- **Faux positifs par image normale** — mesure directe de la
  sur-interprétation. C'est le chiffre à surveiller après chaque
  modification des prompts ou de la liste d'experts.

## 4. Ce que ça vaut, et ne vaut pas

Ces chiffres décrivent le comportement de l'application **sur ce lot, avec
ce modèle, à cette version**. Ils permettent de comparer deux versions entre
elles et de détecter une régression.

Ils ne constituent **pas** une validation clinique : les jeux publics ne
reflètent pas la population visée, l'annotation est au niveau de l'image et
non du finding, et aucun de ces lots n'a été collecté selon un protocole
d'évaluation clinique. Le dossier MDR exige une étude conçue pour ça.
