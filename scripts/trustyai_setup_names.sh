#!/usr/bin/env bash
# Apply TrustyAI feature name mapping once, after first capture.
# Idempotent: if names are already chihuahua/muffin (+ image), skip.
# Class order matches ImageFolder / notebooks: ['chihuahua', 'muffin'].
set -euo pipefail

NS="${NS:-chihuahua-vs-muffin-jan}"
MODEL="${MODEL:-muffin-chihuahua}"
TOKEN="${TOKEN:-$(oc whoami -t)}"
HOST="${HOST:-$(oc -n "$NS" get route trustyai-service -o jsonpath='{.spec.host}')}"

INFO=$(curl -sk -H "Authorization: Bearer $TOKEN" "https://$HOST/info")
OUT_KEYS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]);
m=d.get('$MODEL',{}).get('data',{}).get('outputSchema',{}).get('items',{});
print(','.join(sorted(m)))" "$INFO")
IN_KEYS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]);
m=d.get('$MODEL',{}).get('data',{}).get('inputSchema',{}).get('items',{});
print(','.join(sorted(m)))" "$INFO")

echo "current outputs: [$OUT_KEYS]  inputs: [$IN_KEYS]"

if [[ "$OUT_KEYS" == "chihuahua,muffin" ]]; then
  echo "OK — names already applied (chihuahua / muffin). Nothing to do."
  exit 0
fi

if [[ -z "$OUT_KEYS" ]]; then
  echo "FAIL — model '$MODEL' not in /info yet. Send one /infer via :9081 first."
  exit 1
fi

# Fresh schema still uses raw tensor names
curl -sk -H "Authorization: Bearer $TOKEN" -X POST \
  "https://$HOST/info/names" \
  -H "Content-Type: application/json" \
  -d "{
    \"modelId\": \"${MODEL}\",
    \"inputMapping\": { \"input\": \"image\" },
    \"outputMapping\": {
      \"output-0\": \"chihuahua\",
      \"output-1\": \"muffin\"
    }
  }"
echo
echo "=== nameMapping after ==="
curl -sk -H "Authorization: Bearer $TOKEN" "https://$HOST/info" \
  | python3 -c "import sys,json; d=json.load(sys.stdin)['${MODEL}']['data']; print('out', d.get('outputSchema',{}).get('nameMapping')); print('in', d.get('inputSchema',{}).get('nameMapping'))"
