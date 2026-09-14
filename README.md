# MedVision AI Pro

Prototype de visualisation et de lecture d’images assistée par IA. Création : Nicolas Julienne — Studio Niko Design.

**Application : https://nikoju1977.github.io/medicalvisionproai/**

## Démarrage

1. Au premier accès, choisissez un code de 6 à 12 chiffres et confirmez-le. Conservez ce code : il permet de déchiffrer vos dossiers sur cet appareil.
2. Importez une ou plusieurs images JPEG, PNG, WebP ou BMP (24 maximum, 30 Mo et 32 mégapixels par image). Les fichiers DICOM et PDF ne sont pas décodés : exportez les images en PNG/JPEG depuis votre lecteur.
3. Ouvrez **Configurer l’IA**. Pour Mistral, renseignez votre clé personnelle et choisissez **Auto Éco**. Le bouton **Tester** utilise une image géométrique synthétique ; il ne transmet aucun examen.
4. Enregistrez la configuration puis lancez l’analyse. **Arrêter l’analyse** annule les requêtes en cours et celles en attente.

Aucune clé n’est fournie par ce dépôt. L’accès à l’API, ses quotas et ses tarifs dépendent de votre compte fournisseur. Auto Éco sélectionne un modèle vision accessible ; il ne garantit pas la gratuité. Les modèles sont interrogés via le [catalogue Mistral](https://docs.mistral.ai/api/endpoint/models) et la [Chat Completions API](https://docs.mistral.ai/api/endpoint/chat).

## Fonctions disponibles

- Visualisation, comparaison, zoom, mesures calibrées, annotations et zones d’intérêt.
- Import de séries d’images ; extraction de trames vidéo dans les formats décodés par le navigateur (250 Mo maximum).
- Série / évolution pour un même examen ; lot pour des examens indépendants. Les deux boutons d’analyse respectent ce choix.
- Mistral vision ou endpoint privé compatible OpenAI, par exemple un serveur hébergeant MedGemma. MedGemma n’est pas installé ni hébergé par cette application.
- Description générale d’une image non médicale avec résultat visible.
- Sauvegarde locale chiffrée de toute la série, des annotations, du contexte et du rapport ; restauration du dernier examen du patient sélectionné.
- Export PDF d’un rapport médical terminé (bibliothèque jsPDF requise), installation PWA et notification de mise à jour.

## Données et limites

Les images sont traitées localement pour l’affichage. **Lancer l’analyse transmet les images et le contexte clinique au fournisseur configuré.** Retirez les informations identifiantes, y compris celles inscrites dans les pixels. Le prétraitement n’anonymise pas les images.

Les dossiers sauvegardés dans IndexedDB sont chiffrés en AES-256-GCM avec une clé dérivée du code. Les anciennes sauvegardes restent lisibles. Les clés API sont conservées localement par la version actuelle ; utilisez cet espace uniquement sur un appareil de confiance. Une sauvegarde navigateur n’est pas une sauvegarde externe : effacer les données du site peut supprimer les dossiers et le code de déchiffrement.

Le cache hors ligne contient uniquement les fichiers applicatifs autorisés. Il ne stocke ni réponses IA ni endpoints patients. L’IA distante requiert une connexion. Le PDF hors ligne dépend du chargement préalable de jsPDF.

**Prototype non certifié comme dispositif médical.** Les tests logiciels ne valident pas les performances diagnostiques. Les réponses IA peuvent être inexactes et ne permettent pas, seules, de poser ou d’écarter un diagnostic.

## Développement et tests

Node.js 22 ou supérieur ; Python 3 pour servir le dossier en local :

```bash
npm install --ignore-scripts
npm test
python3 -m http.server 8080 --bind 127.0.0.1
```

Ouvrez ensuite http://localhost:8080 (évitez `file://`, incompatible avec certaines fonctions sécurisées).

Les tests exécutent le JavaScript réel, Canvas, le décodage d’images et WebCrypto dans un hôte Node avec DOM de test. Ils couvrent les cinq scénarios d’intégration d’origine et les régressions de configuration, import, sauvegarde, annulation, indices d’images et cache. Ils utilisent des réponses IA simulées, sans appel payant. Ils ne remplacent pas un essai dans les navigateurs cibles ni une validation avec un compte IA réel.

Le banc expérimental `test/bench.js` est séparé ; ses dépendances historiques et son mode d’emploi sont décrits dans `test/BENCH.md`. Il transmet les images du jeu d’essai au fournisseur : ne l’exécuter que sur des données autorisées.

## Licence

[MIT](LICENSE) © 2026 Nicolas Julienne — Studio Niko Design
