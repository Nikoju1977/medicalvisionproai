# MedVision AI Pro

Application HTML mono-fichier d'aide à la décision en imagerie médicale.
**Studio Niko Design** — Nicolas Julienne.

> Aide à la décision destinée à un professionnel de santé qualifié.
> Ne constitue pas un diagnostic. Aucune conclusion n'a de valeur tant
> qu'elle n'a pas été confirmée par un praticien.
>
> Ce logiciel **n'est pas** un dispositif médical marqué CE. Le dossier
> technique MDR est en cours de constitution ; aucune performance
> diagnostique n'est mesurée à ce jour.

## En ligne

https://nikoju1977.github.io/medicalvisionproai/

## Structure

| Fichier | Rôle |
| --- | --- |
| `index.html` | L'application entière : interface, pipeline, rendu, export PDF |
| `sw.js` | Service worker — coquille en cache, réseau d'abord pour la navigation |
| `manifest.json` | Manifeste PWA |
| `test/e2e.js` | Banc bout-en-bout, API simulée, 5 scénarios |
| `test/bench.js` | Banc de mesure : sensibilité, spécificité, faux positifs |
| `.github/workflows/tests.yml` | Intégration continue — bloque la fusion vers `main` |

## Moteurs d'analyse

- **Mistral** — clé API, sélection automatique du meilleur modèle vision.
- **MedGemma** — tout point d'accès compatible OpenAI (Ollama, vLLM,
  LM Studio). Aucune image ne quitte l'appareil. En GGUF, la vision exige
  le fichier `mmproj` du dépôt du modèle.

Configuration stockée localement, en double : `localStorage` et IndexedDB,
le second prenant le relais quand le premier est bloqué.

## Pipeline

Pré-traitement → triage de modalité → lectures expertes indépendantes
(19 spécialités routées d'après le triage) → consensus → annotations.

Déterministe : `temperature: 0`, graine fixe, toutes deux consignées dans
la traçabilité de chaque compte rendu.

Toute perte de matière est rendue visible — lot en échec, réponse tronquée,
lecture forcée sur image jugée non analysable — à l'écran **et** dans le PDF.
Une région non évaluable est signalée comme telle et jamais comme normale.

## Développement

```
npm install jsdom canvas
node test/e2e.js index.html nominal        # + rate-limit, lot-perdu, tronque, quota
```

Travailler sur `dev`, ouvrir une pull request vers `main`. L'intégration
continue vérifie la syntaxe, les cinq scénarios et la cohérence des versions
entre `index.html`, `sw.js` et `manifest.json`.

À chaque version, incrémenter les trois ensemble : `APP_VERSION`, le `BUILD`
du service worker et `version` du manifeste. Sinon la coquille en cache reste
en arrière.

## Mesurer la performance

Voir [`test/BENCH.md`](test/BENCH.md). Aucune mesure n'a encore été effectuée.
C'est le point bloquant du dossier réglementaire.
