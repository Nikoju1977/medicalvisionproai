# MedVision AI Pro

Prototype de visualisation et de lecture d’images assistée par IA. Création : Nicolas Julienne — Studio Niko Design.

**Release applicative : 17.0.0** — le même artefact de production validé est destiné à GitHub Pages et Vercel.

**Application : https://nikoju1977.github.io/medicalvisionproai/**

## Démarrage

1. Au premier accès, choisissez un code de 6 à 12 chiffres et confirmez-le. Conservez ce code : il permet de déchiffrer vos dossiers sur cet appareil.
2. Importez des images JPEG, PNG, WebP ou BMP pour l’analyse médicale ou visuelle standard. Pour une série DICOM, utilisez **DICOM / MPR** : la v17 décode localement les DICOM monochromes non compressés et reconstruit les plans axial, coronal et sagittal.
3. Ouvrez **Configurer l’IA**. Pour Mistral, renseignez votre clé personnelle et choisissez **Auto Éco**. Le bouton **Tester** utilise une image géométrique synthétique ; il ne transmet aucun examen.
4. Enregistrez la configuration puis lancez l’analyse. **Arrêter l’analyse** annule les requêtes en cours et celles en attente.

Aucune clé n’est fournie par ce dépôt. L’accès à l’API, ses quotas et ses tarifs dépendent de votre compte fournisseur. Auto Éco sélectionne un modèle vision accessible ; il ne garantit pas la gratuité. Les modèles sont interrogés via le [catalogue Mistral](https://docs.mistral.ai/api/endpoint/models) et la [Chat Completions API](https://docs.mistral.ai/api/endpoint/chat).

## Fonctions disponibles

- Visualisation, comparaison, zoom, mesures calibrées, annotations et zones d’intérêt.\n- **Imaging Pro v17** : DICOM monochrome non compressé 8/16 bits, séries CT/MR, reconstruction MPR axial/coronal/sagittal, crosshair synchronisé, Window/Level, presets CT, cine axial et lecture HU lorsque Rescale Slope/Intercept sont présents.
- Import de séries d’images ; extraction de trames vidéo dans les formats décodés par le navigateur (250 Mo maximum).
- Série / évolution pour un même examen ; lot pour des examens indépendants. Les deux boutons d’analyse respectent ce choix.
- Mistral vision ou endpoint privé compatible OpenAI, par exemple un serveur hébergeant MedGemma. MedGemma n’est pas installé ni hébergé par cette application.
- **Image standard / photo** : analyse visuelle non médicale dédiée (description, objets, texte visible, composition/cadrage, couleurs/lumière, qualité et limites), séparée du pipeline médical.
- Sauvegarde locale chiffrée de toute la série, des annotations, du contexte et du rapport ; restauration du dernier examen du patient sélectionné.
- Export PDF d’un rapport médical terminé (bibliothèque jsPDF requise), installation PWA et notification de mise à jour.

## Données et limites

Les images sont traitées localement pour l’affichage. **Lancer l’analyse transmet les images et le contexte clinique au fournisseur configuré.** Retirez les informations identifiantes, y compris celles inscrites dans les pixels. Le prétraitement n’anonymise pas les images.

Les dossiers sauvegardés dans IndexedDB sont chiffrés en AES-256-GCM avec une clé dérivée du code. Les anciennes sauvegardes restent lisibles. Les clés API sont conservées localement par la version actuelle ; utilisez cet espace uniquement sur un appareil de confiance. Une sauvegarde navigateur n’est pas une sauvegarde externe : effacer les données du site peut supprimer les dossiers et le code de déchiffrement.

Le cache hors ligne contient uniquement les fichiers applicatifs autorisés, dont le module Imaging Pro. Il ne stocke ni réponses IA ni endpoints patients. L’IA distante requiert une connexion. Le PDF hors ligne dépend du chargement préalable de jsPDF.

**Prototype non certifié comme dispositif médical.** Les tests logiciels ne valident pas les performances diagnostiques. Les réponses IA peuvent être inexactes et ne permettent pas, seules, de poser ou d’écarter un diagnostic.

## Développement, build et tests

Node.js 22 ou supérieur et Python 3 :

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
npm run validate:dist
python3 -m http.server 8080 --directory dist --bind 127.0.0.1
```

`npm run build` génère `dist/` sans modifier le `index.html` source. Les modules médicaux injectés restent indépendants du numéro de version : la release est pilotée par `package.json`, puis contrôlée automatiquement dans `index.html`, `manifest.json`, `sw.js` et `package-lock.json`. L’artefact publié contient uniquement les ressources nécessaires à l’exécution, sans les outils, tests ou workflows de développement.

Ouvrez ensuite http://localhost:8080 (évitez `file://`, incompatible avec certaines fonctions sécurisées).

Les tests exécutent le JavaScript réel, Canvas, le décodage d’images et WebCrypto dans un hôte Node avec DOM de test. La CI reconstruit également l’artefact de production, valide sa cohérence PWA et vérifie que le build est reproductible et non destructif. Ils couvrent les cinq scénarios d’intégration d’origine et les régressions de configuration, import, sauvegarde, annulation, indices d’images et cache. Un test DICOM synthétique contrôle aussi le décodage CT 16 bits vers HU, l’ordre des coupes et l’espacement 3D. Ils utilisent des réponses IA simulées, sans appel payant. Ils ne remplacent pas un essai dans les navigateurs cibles ni une validation avec un compte IA réel.

Limite Imaging Pro v17 : les Transfer Syntax compressées JPEG/JPEG-LS/JPEG2000, RLE et Deflated ne sont pas encore décodées localement ; l’application les refuse explicitement au lieu de produire une image erronée.\n\nLe banc expérimental `test/bench.js` est séparé ; ses dépendances historiques et son mode d’emploi sont décrits dans `test/BENCH.md`. Il transmet les images du jeu d’essai au fournisseur : ne l’exécuter que sur des données autorisées.

## Licence

[MIT](LICENSE) © 2026 Nicolas Julienne — Studio Niko Design
