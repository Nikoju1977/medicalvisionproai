# Déploiement de MedVision AI Pro 16.2.0

Le site reste une application statique sans étape de compilation. Conservez `index.html`, `sw.js`, `manifest.json` et les icônes dans le même dossier. Les chemins relatifs fonctionnent dans le sous-dossier GitHub Pages.

## Vérifier puis publier

1. `npm install --ignore-scripts` puis `npm test`.
2. Soumettre les corrections dans une branche et vérifier les tests avant la fusion.
3. GitHub Pages doit publier `main` depuis la racine du dépôt, ou utiliser le déploiement Pages déjà configuré.
4. Attendre la réussite du déploiement, puis ouvrir https://nikoju1977.github.io/medicalvisionproai/ et vérifier la version affichée.

La version doit être identique dans `APP_VERSION`, `BUILD`, `manifest.json` et `package.json`. Le test automatique vérifie cette cohérence.

## Mise à jour et hors ligne

Une mise à jour du service worker affiche une bannière. Enregistrez l’examen avant de recharger : aucun rechargement n’est imposé pendant une opération. Si le nouveau fichier principal ne peut pas être téléchargé, le worker ne remplace pas la version hors ligne précédente.

Le cache comprend seulement les chemins applicatifs explicitement autorisés et jsPDF. Les URL avec paramètres, les appels authentifiés et les endpoints de données ne sont pas mis en cache. Le fonctionnement hors ligne exige un premier chargement réussi ; l’IA distante nécessite Internet.

## Vérification manuelle après déploiement

- Premier accès et déverrouillage avec le code choisi.
- Import de deux images, déplacement, annotations, suppression d’une image.
- Sauvegarde et restauration sur un dossier de test sans données réelles.
- Configuration IA puis **Tester** avec une clé personnelle valide.
- Lecture réelle d’une image de test autorisée, arrêt d’une requête et export PDF.
- Installation Android, fermeture/réouverture et essai hors ligne.

Les tests automatisés utilisent une API simulée. Un essai de génération réelle requiert votre accès fournisseur et ne constitue pas une validation clinique.
