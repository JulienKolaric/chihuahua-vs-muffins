# Hotline 0800-HELP — Escalation matrix

Document ID: escalation
Audience: Hotline agents

## SLA (lab)

| Severity | First response | Resolve or escalate |
|----------|----------------|---------------------|
| P1 | 5 minutes | 30 minutes |
| P2 | 15 minutes | 2 hours |
| P3 | 1 hour | 1 business day |

## When to escalate

Escalate when:

1. The approved runbook steps are completed and the symptom remains.
2. The user reports safety risk (smoke, trapped, medical).
3. Cause codes `WIFI-BALANCE-42`, `BREW-PDF-7`, or `LIFT-MON-1` need a change window the Hotline cannot approve.

## Teams

| Cause code | Team | Channel |
|------------|------|---------|
| WIFI-BALANCE-42 | Networking L2 | `#net-l2` |
| BREW-PDF-7 | Facilities / CoffeeOps | `#coffeeops` |
| LIFT-MON-1 | Building Automation | `#lifts` |

## Ticket format for escalation

Subject: `[CAUSECODE] short symptom`
Body must include: user location, steps already tried from the runbook, and the exact cause code.
