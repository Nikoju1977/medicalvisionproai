# Politique de sécurité

## Données médicales

MedVision AI Pro est un prototype non certifié comme dispositif médical. N'utilisez pas de données de santé identifiantes pour les tests de développement ou de démonstration.

L'affichage et la sauvegarde locale sont réalisés dans le navigateur. Une analyse distante transmet les images et le contexte clinique au fournisseur IA configuré par l'utilisateur. Le prétraitement ne garantit pas l'anonymisation des informations visibles dans les pixels.

## Secrets

Aucune clé API, jeton, donnée patient ou identifiant d'accès ne doit être commité dans ce dépôt. Les clés de fournisseur saisies dans l'application sont gérées côté navigateur et doivent être utilisées uniquement sur un appareil de confiance.

## Signaler une vulnérabilité

Évitez de publier une vulnérabilité contenant des données médicales, des secrets ou des informations permettant d'exploiter directement une installation réelle dans une issue publique. Utilisez les mécanismes privés de signalement de sécurité GitHub lorsqu'ils sont activés sur le dépôt.

## Périmètre

Les tests logiciels couvrent le fonctionnement technique de l'application. Ils ne démontrent ni performance diagnostique, ni sécurité clinique, ni conformité réglementaire.
