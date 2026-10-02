#!/usr/bin/env bash
# Full uninstall of TrustyAI in the lab project (DATABASE path).
# Removes TrustyAIService, CA, logger, MariaDB, and DB credentials.
# Safe to re-run: missing secret / MariaDB / CR must not fail the script.
#
# Use this when colleagues should redo Step 8 from §8.1 (fresh install).
# For data-only wipe (keep the service + MariaDB), use scripts/trustyai_reset.sh.
#
# Usage:
#   export NS=chihuahua-vs-muffin-jan   # optional
#   bash scripts/trustyai_uninstall.sh
set -euo pipefail

NS="${NS:-chihuahua-vs-muffin-jan}"
ISVC="${ISVC:-muffin-chihuahua}"

echo "NS=$NS  ISVC=$ISVC"

force_delete_trustyai() {
  local name="trustyai-service"
  if ! oc -n "$NS" get trustyaiservice "$name" >/dev/null 2>&1; then
    echo "(TrustyAIService already gone)"
    return 0
  fi

  echo "Deleting TrustyAIService $name …"
  # Best-effort graceful delete (may hang if DB secret already missing).
  oc -n "$NS" delete trustyaiservice "$name" --ignore-not-found --wait=false 2>/dev/null || true

  local i
  for i in $(seq 1 30); do
    if ! oc -n "$NS" get trustyaiservice "$name" >/dev/null 2>&1; then
      echo "TrustyAIService deleted."
      return 0
    fi
    # If the operator is stuck (e.g. secret already deleted → CreateContainerConfigError),
    # strip the finalizer so the CR can actually disappear.
    if [[ $i -eq 10 || $i -eq 20 ]]; then
      echo "Still present — removing finalizer (secret/DB may already be gone)…"
      oc -n "$NS" patch trustyaiservice "$name" --type=json \
        -p='[{"op":"remove","path":"/metadata/finalizers"}]' 2>/dev/null || true
      oc -n "$NS" delete trustyaiservice "$name" --ignore-not-found --wait=false --force --grace-period=0 2>/dev/null || true
    fi
    sleep 2
  done

  if oc -n "$NS" get trustyaiservice "$name" >/dev/null 2>&1; then
    echo "WARNING: TrustyAIService still present after force attempts — check manually."
    return 1
  fi
}

echo "=== 1) Remove InferenceService logger ==="
if oc -n "$NS" get inferenceservice "$ISVC" >/dev/null 2>&1; then
  if oc -n "$NS" get inferenceservice "$ISVC" -o jsonpath='{.spec.predictor.logger}' 2>/dev/null | grep -q .; then
    oc -n "$NS" patch inferenceservice "$ISVC" --type=json \
      -p='[{"op":"remove","path":"/spec/predictor/logger"}]' || true
  else
    echo "(no logger set)"
  fi
else
  echo "(InferenceService $ISVC not found — skip)"
fi

echo "=== 2) Delete TrustyAIService (tolerates missing DB secret) ==="
# Capture DB secret name before the CR disappears (UI often uses trustyai-db-secret).
DB_SECRET_FROM_CR=$(oc -n "$NS" get trustyaiservice trustyai-service \
  -o jsonpath='{.spec.storage.databaseConfigurations}' 2>/dev/null || true)
force_delete_trustyai || true

echo "=== 3) Delete MariaDB + DB credentials (DATABASE path) ==="
# CLI lab secret: trustyai-service-db-credentials
# Dashboard UI secret: trustyai-db-secret (Settings → Configure TrustyAI)
oc -n "$NS" delete deploy/mariadb svc/mariadb-service pvc/mariadb-data \
  secret/mariadb-root \
  secret/trustyai-service-db-credentials \
  secret/trustyai-db-secret \
  --ignore-not-found || true

if [[ -n "${DB_SECRET_FROM_CR}" ]]; then
  echo "Also deleting CR-referenced DB secret: $DB_SECRET_FROM_CR"
  oc -n "$NS" delete secret "$DB_SECRET_FROM_CR" --ignore-not-found || true
fi

# Any leftover *db* trustyai secrets (name variants)
while IFS= read -r s; do
  [[ -z "$s" ]] && continue
  echo "Deleting leftover DB secret: $s"
  oc -n "$NS" delete secret "$s" --ignore-not-found || true
done < <(oc -n "$NS" get secrets -o name 2>/dev/null \
  | sed 's|^secret/||' \
  | grep -E '^trustyai.*db|db.*trustyai|trustyai-db' || true)

echo "=== 4) Delete leftovers (CA / monitors / old PVC if any) ==="
oc -n "$NS" delete cm kserve-logger-ca-bundle --ignore-not-found || true
oc -n "$NS" delete servicemonitor trustyai-service --ignore-not-found 2>/dev/null || true
oc -n "$NS" delete secret,cm -l app=trustyai-service --ignore-not-found 2>/dev/null || true
oc -n "$NS" delete pvc trustyai-service-pvc --ignore-not-found --wait=false 2>/dev/null || true

# Deployment leftover pods / ReplicaSets / route / services
oc -n "$NS" delete pod -l app=trustyai-service --ignore-not-found --force --grace-period=0 2>/dev/null || true
oc -n "$NS" delete svc trustyai-service trustyai-service-tls --ignore-not-found 2>/dev/null || true
oc -n "$NS" delete route trustyai-service --ignore-not-found 2>/dev/null || true

echo "=== 5) Wait for TrustyAI pods gone ==="
for _ in $(seq 1 20); do
  left=$(oc -n "$NS" get pod -l app=trustyai-service --no-headers 2>/dev/null | wc -l | tr -d ' ')
  [[ "$left" == "0" ]] && break
  sleep 2
done

echo
echo "=== Verify ==="
oc -n "$NS" get trustyaiservice 2>&1 | head -3 || true
oc -n "$NS" get pod -l app=trustyai-service --no-headers 2>&1 || echo "(no TrustyAI pods)"
oc -n "$NS" get deploy/mariadb 2>&1 || true
oc -n "$NS" get secret trustyai-service-db-credentials trustyai-db-secret 2>&1 || true
oc -n "$NS" get secrets -o name 2>/dev/null | grep -iE 'trustyai.*db|db.*trustyai' || echo "(no trustyai DB secrets)"
oc -n "$NS" get route trustyai-service 2>&1 || true
oc -n "$NS" get cm kserve-logger-ca-bundle 2>&1 || true
echo -n "ISVC logger: "
oc -n "$NS" get inferenceservice "$ISVC" -o jsonpath='{.spec.predictor.logger}{"\n"}' 2>/dev/null || echo "(n/a)"
echo
echo "Clean. Replay Step 8 from §8.1 (MariaDB → secret → TrustyAIService → CA → logger)."
