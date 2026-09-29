#!/usr/bin/env bash
# Full uninstall of TrustyAI in the lab project — pod, CR, PVC, CA, logger.
# Use this when colleagues should redo Step 8 from §8.1 (fresh install).
# For data-only wipe (keep the service), use scripts/trustyai_reset.sh instead.
#
# Usage:
#   export NS=chihuahua-vs-muffin-jan   # optional
#   bash scripts/trustyai_uninstall.sh
set -euo pipefail

NS="${NS:-chihuahua-vs-muffin-jan}"
ISVC="${ISVC:-muffin-chihuahua}"

echo "NS=$NS  ISVC=$ISVC"

echo "=== 1) Remove InferenceService logger ==="
if oc -n "$NS" get inferenceservice "$ISVC" >/dev/null 2>&1; then
  if oc -n "$NS" get inferenceservice "$ISVC" -o jsonpath='{.spec.predictor.logger}' | grep -q .; then
    oc -n "$NS" patch inferenceservice "$ISVC" --type=json \
      -p='[{"op":"remove","path":"/spec/predictor/logger"}]'
  else
    echo "(no logger set)"
  fi
else
  echo "(InferenceService $ISVC not found — skip)"
fi

echo "=== 2) Delete TrustyAIService ==="
oc -n "$NS" delete trustyaiservice trustyai-service --ignore-not-found --wait=true --timeout=180s

echo "=== 3) Delete leftovers ==="
oc -n "$NS" delete pvc trustyai-service-pvc --ignore-not-found --wait=false
oc -n "$NS" delete cm kserve-logger-ca-bundle --ignore-not-found
oc -n "$NS" delete servicemonitor trustyai-service --ignore-not-found 2>/dev/null || true
oc -n "$NS" delete secret,cm -l app=trustyai-service --ignore-not-found 2>/dev/null || true

echo "=== 4) Wait for pods gone ==="
for _ in $(seq 1 20); do
  left=$(oc -n "$NS" get pod -l app=trustyai-service --no-headers 2>/dev/null | wc -l | tr -d ' ')
  [[ "$left" == "0" ]] && break
  sleep 2
done

echo
echo "=== Verify ==="
oc -n "$NS" get trustyaiservice 2>&1 | head -3 || true
oc -n "$NS" get pod -l app=trustyai-service --no-headers 2>&1 || echo "(no pods)"
oc -n "$NS" get pvc trustyai-service-pvc 2>&1 || true
oc -n "$NS" get route trustyai-service 2>&1 || true
oc -n "$NS" get cm kserve-logger-ca-bundle 2>&1 || true
echo -n "ISVC logger: "
oc -n "$NS" get inferenceservice "$ISVC" -o jsonpath='{.spec.predictor.logger}{"\n"}' 2>/dev/null || echo "(n/a)"
echo
echo "Clean. Replay Step 8 from §8.1 (install TrustyAIService + CA + logger)."
