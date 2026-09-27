# Déploiement de MedVision AI Pro 16.8.0

MedVision est une application statique, mais la version de production est désormais **générée et validée** dans `dist/`. GitHub Pages et Vercel doivent publier ce même artefact afin d’éviter toute divergence entre la version web, le manifeste PWA et le service worker.

## Vérifier localement

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
npm run validate:dist
git diff --exit-code
```

Le build applique la pile médicale de production sur une copie logique de l’application, valide ses marqueurs et restaure ensuite exactement le fichier source. `git diff --exit-code` doit donc rester propre.

La release `16.8.0` doit être cohérente entre `package.json`, `package-lock.json`, `APP_VERSION` dans l’application générée, `manifest.json` et `BUILD` dans `sw.js`. `tools/validate_distribution.py` bloque la publication si cette cohérence est rompue.

## GitHub Pages

Le workflow `.github/workflows/pages.yml` :

1. installe les dépendances verrouillées ;
2. exécute les tests ;
3. construit `dist/` ;
4. vérifie que le build ne modifie pas les sources ;
5. envoie uniquement `dist/` comme artefact GitHub Pages ;
6. déploie cet artefact.

Dans les paramètres GitHub Pages du dépôt, la source de publication doit être **GitHub Actions** pour utiliser ce workflow. Une fois activée, chaque fusion sur `main` publie l’artefact validé.

Application : https://nikoju1977.github.io/medicalvisionproai/

## Vercel

`vercel.json` utilise le même `tools/build_vercel.py` et le même dossier `dist/`. Il ajoute des en-têtes de sécurité de base et force la revalidation de `index.html` et `sw.js`, afin de limiter les incohérences de cache lors d’une mise à jour PWA.

Aucune clé IA ne doit être stockée dans le dépôt ou dans l’artefact statique.

## Mise à jour et hors ligne

Une mise à jour du service worker affiche une bannière. Enregistrez l’examen avant de recharger : aucun rechargement n’est imposé pendant une opération. Si le nouveau shell ne peut pas être téléchargé, le worker ne remplace pas la version hors ligne précédente.

Le cache est limité aux fichiers applicatifs explicitement autorisés, aux modules de références web et à jsPDF. Les URL avec paramètres, les appels authentifiés et les endpoints de données ne sont pas interceptés. L’IA distante requiert une connexion.

## Vérification manuelle après déploiement

- Premier accès et déverrouillage avec le code choisi.
- Import de deux images, déplacement, annotations et suppression d’une image.
- Sauvegarde puis restauration d’un dossier de test sans données réelles.
- Configuration IA puis **Tester** avec une clé personnelle valide.
- Lecture d’une image de test autorisée, annulation d’une requête et export PDF.
- Installation PWA, fermeture/réouverture et essai hors ligne.
- Vérification qu’une mise à jour de version affiche correctement la proposition de rechargement.

Les tests automatisés utilisent des réponses IA simulées. Un essai avec un fournisseur réel nécessite un compte autorisé et ne constitue pas une validation clinique. MedVision reste un prototype non certifié comme dispositif médical.
