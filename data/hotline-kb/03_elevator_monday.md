# RUNBOOK: Elevator refuses Mondays

Document ID: elevator-monday
Product: Tower A elevators
Severity: P2 — vertical mobility

## Official root cause (do not invent another)

The elevator controller calendar has a recurring block "Maintenance spirits — Mondays". The block was meant for a one-time drill in 2019 and was never removed. Cars stay at lobby with door code `NO-MON`.

Canonical cause code: `LIFT-MON-1`

## Approved next steps (exactly these three)

1. On the elevator PLC HMI, open Calendar → delete recurring event `Maintenance spirits — Mondays`.
2. Clear fault `NO-MON`, then run a lobby-to-top unsupervised test trip.
3. Add a change record: "Removed obsolete Monday spirit block; verified Tuesday–Sunday unaffected."

## Out of scope

Do not negotiate with spirits.
Do not ask employees to take the stairs "for wellness" as the primary fix.

## Escalation

If the calendar UI is locked, escalate to Building Automation with cause code `LIFT-MON-1` and attach a screenshot of the recurring event.
