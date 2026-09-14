# MedVision 16.2.0 — Livraison et validation

Version d’origine du dépôt : `211315f0ba1638faa8859692e3ff0c0cce4481d6`.

## Résultats

- Syntaxe JavaScript : validée.
- Versions application, service worker, manifeste et package : `16.2.0`, cohérentes.
- Cinq scénarios d’intégration : réussis.
- Quatorze tests de régression et de cache : réussis.
- Identifiants DOM dupliqués : aucun détecté.
- Clé ou jeton réel ajouté au code : aucun.

Ces contrôles exécutent le code et Canvas dans Node, avec DOM et réponses IA simulés. Le test de l’analyse avec un compte fournisseur réel n’a pas été réalisé : aucune clé IA n’a été fournie pour cet essai. Le navigateur a pu afficher l’écran d’accès du site actuellement publié ; il n’a pas pu accéder au serveur local de prévisualisation. La validation clinique et la vérification complète sur Android restent à effectuer.

## Corrections principales

- Analyse générale affichée ; découverte du modèle selon le fournisseur configuré.
- Erreurs de clé, de catalogue et d’endpoint remontées au lieu d’être masquées par des modèles supposés disponibles.
- Test de connexion sans altération des paramètres actifs ; exclusion des modèles déclarés sans vision.
- Import borné et conservation des fichiers valides en présence d’un fichier corrompu.
- Conservation des annotations à la suppression d’une image ; indices ROI globaux corrigés.
- Sauvegarde chiffrée de la série complète et restauration sans mélange d’examens.
- Respect du mode lot par les deux boutons ; triage de chaque image et terminaison en cas d’image non analysable.
- Annulation des requêtes en cours, en attente et en reprise.
- Cache limité aux ressources applicatives ; version hors ligne antérieure conservée si le remplacement échoue.
- Guide de démarrage, meilleure disposition mobile et documentation conforme aux fonctions présentes.

## État de publication

Les écritures GitHub ont été refusées avec HTTP 403, « Resource not accessible by integration », y compris une tentative excluant le workflow. Aucun commit distant ni déploiement n’a été réalisé. L’archive contient les sources corrigées ; elle ne prouve pas une mise à jour du site public.

La connexion GitHub utilisée doit disposer de l’écriture sur le contenu du dépôt pour publier les sources. Le fichier `.github/workflows/tests.yml` nécessite aussi les droits appropriés sur les workflows.
