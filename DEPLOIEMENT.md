# MedVision AI Pro v12 — déploiement PWA

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | Application complète (single-file) |
| `sw.js` | Service worker — coquille en cache, API jamais mise en cache |
| `manifest.json` | Manifeste PWA |
| `icon-192.png` / `icon-512.png` | Icônes standard |
| `icon-maskable-192.png` / `icon-maskable-512.png` | Icônes adaptatives Android |
| `apple-touch-icon.png` | Icône iOS |

**Les 7 fichiers doivent être à la racine du même dossier.** Les chemins sont relatifs :
la racine d'un domaine comme un sous-dossier GitHub Pages fonctionnent sans modification.

## GitHub Pages

```bash
git add index.html sw.js manifest.json *.png
git commit -m "v12 — PWA, mode Lot, analyse multi-sources"
git push origin main
```

Puis Settings → Pages → Source : `main` / `(root)`.
URL : `https://nikoju1977.github.io/medicalvisionproai/`

## Contrôles après mise en ligne

1. Ouvrir l'URL **en https** — jamais le fichier téléchargé (origine opaque = tout appel réseau bloqué)
2. Modale clé API → **🩺 Diagnostic** → l'étape 0 doit afficher l'origine en vert
3. Bouton **⤓ Installer** dans l'en-tête (Android/Chrome). iOS : Partager → « Sur l'écran d'accueil »
4. Mode avion → l'app se lance, l'affichage, les mesures, les annotations et l'export PDF
   restent disponibles. Seule l'analyse IA exige le réseau.

## Mise à jour

Modifier `BUILD` dans `sw.js` (`v12.0.1`, …) à chaque déploiement.
Les utilisateurs voient une bannière « Nouvelle version disponible » et
rechargent d'un clic. Les anciens caches sont purgés automatiquement.
