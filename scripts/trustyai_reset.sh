#!/usr/bin/env bash
# Wipe TrustyAI capture + MeanShift jobs so the lab Step 8 can be replayed from scratch.
# Keeps TrustyAIService / CA / InferenceService logger intact — only clears stored data.
#
# Requires: oc logged in, project has trustyai-service Ready.
#
# Usage:
#   export NS=chihuahua-vs-muffin-jan   # optional
#   bash scripts/trustyai_reset.sh
set -euo pipefail

NS="${NS:-chihuahua-vs-muffin-jan}"
TOKEN="${TOKEN:-$(oc whoami -t)}"
HOST=$(oc -n "$NS" get route trustyai-service -o jsonpath='{.spec.host}')
POD=$(oc -n "$NS" get pod -l app=trustyai-service -o jsonpath='{.items[0].metadata.name}')

echo "NS=$NS"
echo "HOST=$HOST"
echo "POD=$POD"

echo "=== 1) Delete all MeanShift schedules ==="
IDS=$(curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://$HOST/metrics/drift/meanshift/requests" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(r['id'] for r in d.get('requests',[])))" 2>/dev/null || true)
if [[ -z "${IDS// }" ]]; then
  echo "(none)"
else
  for id in $IDS; do
    curl -sk -H "Authorization: Bearer $TOKEN" -X DELETE \
      "https://$HOST/metrics/drift/meanshift/request" \
      -H "Content-Type: application/json" \
      -d "{\"requestId\":\"$id\"}" >/dev/null
    echo "  removed $id"
  done
fi

echo "=== 2) Wipe model CSV / metadata on PVC ==="
oc -n "$NS" exec "$POD" -c trustyai-service -- \
  sh -c 'rm -f /data/muffin-chihuahua-*.csv /data/muffin-chihuahua-metadata.json /data/data.csv 2>/dev/null; ls -la /data/ || true'

echo "=== 3) Restart TrustyAI pod ==="
oc -n "$NS" delete pod -l app=trustyai-service --wait=false
oc -n "$NS" wait --for=condition=Ready pod -l app=trustyai-service --timeout=180s

HOST=$(oc -n "$NS" get route trustyai-service -o jsonpath='{.spec.host}')
echo "=== 4) Verify empty state ==="
echo -n "/info → "
curl -sk -H "Authorization: Bearer $TOKEN" "https://$HOST/info"
echo
echo -n "/info/tags → "
curl -sk -H "Authorization: Bearer $TOKEN" "https://$HOST/info/tags"
echo
echo
echo "Reset done. Replay Step 8 from §8.2 onward:"
echo "  1) one /infer via :9081  → /info shows muffin-chihuahua"
echo "  2) bash scripts/trustyai_setup_names.sh"
echo "  3) TRAINING upload (scripts/trustyai_training_upload.py + oc exec curl)"
echo "  4) POST MeanShift schedule → use the NEW requestId in Observe"
echo "  5) notebooks/09_trustyai_flood.ipynb (neg then pos)"
