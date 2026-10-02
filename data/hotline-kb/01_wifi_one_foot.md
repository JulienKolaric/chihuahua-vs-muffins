# RUNBOOK: Wi-Fi works only when standing on one foot
Keywords: Wi-Fi, wifi, one foot, stand on one foot, BalanceAware, CAMPUS-SECURE, WIFI-BALANCE-42

Document ID: wifi-one-foot
Product: Campus Wi-Fi
Severity: P3 — inconvenient but comic
Canonical cause code: WIFI-BALANCE-42

## Official root cause (do not invent another)

The access point firmware enables "BalanceAware Roaming". It incorrectly treats a two-foot stance as a roaming client and drops the association. Standing on one foot keeps the client in "stationary" mode.

## Approved next steps (exactly these three)

1. Ask the user to hop once, then stand still on the left foot for 30 seconds while reconnecting to SSID CAMPUS-SECURE.
2. On the controller, disable BalanceAware Roaming for AP group B-WING (CLI: set balance-aware off b-wing).
3. Schedule firmware patch wifi-fw-9.9.9-flatfoot during the next change window; open ticket with Networking using template WIFI-BALANCE.

## Out of scope

Do not recommend standing on chairs, microwave shields, or aluminum foil hats.
Do not reset every switch in the building.
Do not invent other cause codes (never WIFI-FOUNDR).

## Escalation

If the user still has no IP after step 2, escalate to Networking L2 with cause code WIFI-BALANCE-42 (see escalation matrix).
