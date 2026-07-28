#!/usr/bin/env bash
# ============================================================
#  MedVision AI Pro v12 — dépôt sur GitHub
#  Studio Niko Design
#
#  Le jeton reste sur TA machine : il n'est jamais écrit dans un
#  fichier, ni affiché, ni transmis ailleurs qu'à api.github.com.
#
#  Usage :
#     export GH_TOKEN=ghp_xxxxxxxxxxxx
#     ./push-github.sh
#  ou simplement ./push-github.sh (le jeton sera demandé, saisie masquée)
# ============================================================
set -euo pipefail

OWNER="${OWNER:-Nikoju1977}"
REPO="${REPO:-medicalvisionproai}"
BRANCH="${BRANCH:-main}"
MSG="${MSG:-v12 — PWA installable, mode Lot, analyse multi-sources Mistral}"

FILES=(
  index.html
  sw.js
  manifest.json
  icon-192.png
  icon-512.png
  icon-maskable-192.png
  icon-maskable-512.png
  apple-touch-icon.png
)

C_OK=$'\033[32m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_N=$'\033[0m'

command -v curl   >/dev/null || { echo "curl requis"; exit 1; }
command -v python3 >/dev/null || { echo "python3 requis"; exit 1; }

if [ -z "${GH_TOKEN:-}" ]; then
  read -rsp "Jeton GitHub (classique, scope repo) : " GH_TOKEN; echo
fi
[ -n "$GH_TOKEN" ] || { echo "Jeton vide."; exit 1; }

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "${C_ERR}Fichier manquant : $f${C_N}"; echo "Lance ce script depuis le dossier contenant les 8 fichiers."; exit 1; }
done

API="https://api.github.com"
AUTH=(-H "Authorization: Bearer $GH_TOKEN"
      -H "Accept: application/vnd.github+json"
      -H "X-GitHub-Api-Version: 2022-11-28")

echo
echo "Dépôt  : $OWNER/$REPO"
echo "Branche: $BRANCH"
echo "Fichiers: ${#FILES[@]}"
echo

# --- Contrôle d'accès avant toute écriture ---
perm=$(curl -sS "${AUTH[@]}" "$API/repos/$OWNER/$REPO" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("permissions",{}).get("push") and "push" or d.get("message","refus"))' 2>/dev/null || echo "erreur")
if [ "$perm" != "push" ]; then
  echo "${C_ERR}Accès en écriture refusé : $perm${C_N}"
  echo "Vérifie que le jeton est CLASSIQUE avec le scope 'repo' (les jetons fine-grained"
  echo "exigent en plus l'autorisation Contents: Read and write sur ce dépôt)."
  exit 1
fi
echo "${C_OK}✓${C_N} accès en écriture confirmé"
echo

fails=0
for f in "${FILES[@]}"; do
  # sha du fichier existant (vide si création)
  sha=$(curl -sS "${AUTH[@]}" "$API/repos/$OWNER/$REPO/contents/$f?ref=$BRANCH" \
        | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("sha",""))
except Exception: print("")' 2>/dev/null || echo "")

  body=$(python3 - "$f" "$MSG" "$BRANCH" "$sha" <<'PY'
import base64, json, sys
path, msg, branch, sha = sys.argv[1:5]
d = {"message": msg, "branch": branch,
     "content": base64.b64encode(open(path, "rb").read()).decode()}
if sha: d["sha"] = sha
sys.stdout.write(json.dumps(d))
PY
)

  code=$(printf '%s' "$body" | curl -sS -o /tmp/gh_out.json -w '%{http_code}' \
         -X PUT "${AUTH[@]}" -H "Content-Type: application/json" \
         --data-binary @- "$API/repos/$OWNER/$REPO/contents/$f")

  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    act=$([ "$code" = "201" ] && echo "créé " || echo "mis à jour")
    csha=$(python3 -c 'import json;print(json.load(open("/tmp/gh_out.json"))["content"]["sha"][:7])' 2>/dev/null || echo "-------")
    printf "%s✓%s %-26s %s  %s%s%s\n" "$C_OK" "$C_N" "$f" "$act" "$C_DIM" "$csha" "$C_N"
  else
    err=$(python3 -c 'import json;print(json.load(open("/tmp/gh_out.json")).get("message","?"))' 2>/dev/null || echo "?")
    printf "%s✗%s %-26s HTTP %s — %s\n" "$C_ERR" "$C_N" "$f" "$code" "$err"
    fails=$((fails+1))
  fi
done
rm -f /tmp/gh_out.json

echo
if [ "$fails" -gt 0 ]; then
  echo "${C_ERR}$fails fichier(s) en échec.${C_N}"
  exit 1
fi

# --- Vérification : relire ce que GitHub sert réellement ---
echo "Vérification des fichiers en ligne…"
RAW="https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH"
vfails=0
for f in "${FILES[@]}"; do
  loc=$(wc -c < "$f" | tr -d ' ')
  rem=$(curl -sS -L "$RAW/$f" | wc -c | tr -d ' ')
  if [ "$loc" = "$rem" ]; then
    printf "%s✓%s %-26s %s octets\n" "$C_OK" "$C_N" "$f" "$rem"
  else
    printf "%s✗%s %-26s local %s ≠ distant %s\n" "$C_ERR" "$C_N" "$f" "$loc" "$rem"
    vfails=$((vfails+1))
  fi
done

echo
if [ "$vfails" -gt 0 ]; then
  echo "${C_ERR}$vfails écart(s) — le cache GitHub peut prendre ~1 min, relance la vérification.${C_N}"
  exit 1
fi

echo "${C_OK}Tous les fichiers sont en ligne et conformes.${C_N}"
echo
echo "  Pages    : https://$OWNER.github.io/$REPO/"
echo "  Réglages : https://github.com/$OWNER/$REPO/settings/pages  (Source : $BRANCH / root)"
echo
echo "Ensuite : ouvre l'URL en https, puis modale clé API → 🩺 Diagnostic."
echo "L'étape 0 doit passer au vert."
