#!/usr/bin/env bash
# Soft reset for TrustyAI DATABASE path (MariaDB).
# Clears captures, TRAINING tags, name mappings, and MeanShift jobs
# so Step 8 can be replayed from §8.7 onward.
#
# Keeps: TrustyAIService, logger, CA bundle, MariaDB deploy/secret.
# Does NOT wipe PVC files — we no longer use PVC storage for TrustyAI.
#
# Requires: oc logged in, trustyai-service Ready, MariaDB Running.
#
# Usage:
#   export NS=chihuahua-vs-muffin-jan   # optional
#   bash scripts/trustyai_reset.sh
set -euo pipefail

NS="${NS:-chihuahua-vs-muffin-jan}"
DB_NAME="${DB_NAME:-trustyai_service}"
DB_USER="${DB_USER:-trustyai}"
DB_PASS="${DB_PASS:-trustyai-lab-pass}"
MODEL_ID="${MODEL_ID:-muffin-chihuahua}"

TOKEN="${TOKEN:-$(oc whoami -t)}"

echo "=== 0) Preflight (DATABASE path) ==="
if ! oc -n "$NS" get secret trustyai-service-db-credentials >/dev/null 2>&1; then
  echo "ERROR: secret trustyai-service-db-credentials is missing."
  echo "Soft reset needs MariaDB + that secret."
  echo "  → Either recreate §8.2 + §8.3, or run: bash scripts/trustyai_uninstall.sh"
  echo "    then replay Step 8 from §8.1."
  exit 1
fi
if ! oc -n "$NS" get deploy/mariadb >/dev/null 2>&1; then
  echo "ERROR: deploy/mariadb is missing."
  echo "  → Recreate §8.2, or full uninstall + replay from §8.1."
  exit 1
fi

HOST=$(oc -n "$NS" get route trustyai-service -o jsonpath='{.spec.host}' 2>/dev/null || true)
POD=$(oc -n "$NS" get pod -l app=trustyai-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

echo "NS=$NS"
echo "HOST=${HOST:-"(no route yet)"}"
echo "POD=${POD:-"(no pod yet)"}"
echo "DB=$DB_NAME (MariaDB)"

if [[ -z "$HOST" || -z "$POD" ]]; then
  echo "ERROR: TrustyAI route/pod not ready (often CreateContainerConfigError if secret was deleted)."
  echo "  → bash scripts/trustyai_uninstall.sh   # force-cleans even without secret"
  echo "  → then replay Step 8 from §8.1"
  exit 1
fi

echo "=== 1) Delete all MeanShift schedules ==="
IDS=$(curl -sk --max-time 30 -H "Authorization: Bearer $TOKEN" \
  "https://$HOST/metrics/drift/meanshift/requests" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(r['id'] for r in d.get('requests',[])))" 2>/dev/null || true)
if [[ -z "${IDS// }" ]]; then
  echo "(none)"
else
  for id in $IDS; do
    curl -sk --max-time 30 -H "Authorization: Bearer $TOKEN" -X DELETE \
      "https://$HOST/metrics/drift/meanshift/request" \
      -H "Content-Type: application/json" \
      -d "{\"requestId\":\"$id\"}" >/dev/null
    echo "  removed $id"
  done
fi

echo "=== 2) Truncate all tables in MariaDB ($DB_NAME) ==="
# Truncate (not DROP DATABASE) so the LONGBLOB ALTER from §8.8 stays in place.
TABLES=$(oc -n "$NS" exec deploy/mariadb -- \
  mysql -u"$DB_USER" -p"$DB_PASS" -N -e \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='${DB_NAME}' AND table_type='BASE TABLE';" \
  2>/dev/null | tr -d '\r' || true)

if [[ -z "${TABLES// }" ]]; then
  echo "(no tables — DB already empty or schema not created yet)"
else
  SQL="SET FOREIGN_KEY_CHECKS=0;"
  while IFS= read -r t; do
    [[ -z "$t" ]] && continue
    SQL+=" TRUNCATE TABLE \`${t}\`;"
    echo "  truncate $t"
  done <<< "$TABLES"
  SQL+=" SET FOREIGN_KEY_CHECKS=1;"
  oc -n "$NS" exec deploy/mariadb -- \
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "$SQL"
fi

echo "=== 3) Confirm LONGBLOB still in place (needed for image TRAINING) ==="
oc -n "$NS" exec deploy/mariadb -- \
  mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e \
  "SHOW COLUMNS FROM DataframeRow_Values LIKE 'serializableObject';" 2>/dev/null \
  || echo "(table gone — TrustyAI will recreate on restart; re-run §8.8 ALTER after first write if needed)"

echo "=== 4) Restart TrustyAI pod (reload empty DB state) ==="
oc -n "$NS" delete pod -l app=trustyai-service --wait=false
oc -n "$NS" wait --for=condition=Ready pod -l app=trustyai-service --timeout=180s

# Route can lag a few seconds after the new pod is Ready
for _ in 1 2 3 4 5 6; do
  if curl -sk --max-time 10 -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" \
    "https://$HOST/info" | grep -qE '200|404'; then
    break
  fi
  sleep 5
done

echo "=== 5) Verify empty state ==="
echo -n "/info → "
curl -sk --max-time 15 -H "Authorization: Bearer $TOKEN" "https://$HOST/info" || echo "(route not ready yet)"
echo
echo -n "/info/tags → "
curl -sk --max-time 15 -H "Authorization: Bearer $TOKEN" "https://$HOST/info/tags" || echo "(route not ready yet)"
echo
echo
echo "Reset done (DATABASE path). Replay from §8.7:"
echo "  1) notebooks/08b_trustyai_capture_json.ipynb  → /info shows ${MODEL_ID}"
echo "  2) §8.8 ALTER only if serializableObject is tinyblob again"
echo "  3) §8.9 TRAINING upload (08c + oc cp into TrustyAI pod)"
echo "  4) §8.10 names  →  §8.11 MeanShift  →  §8.14 floods"
echo
echo "Full uninstall (incl. MariaDB): bash scripts/trustyai_uninstall.sh"
