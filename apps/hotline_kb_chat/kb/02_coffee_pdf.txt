# RUNBOOK: Coffee machine prints PDF instead of coffee

Document ID: coffee-pdf
Product: Break-room espresso fleet
Severity: P2 — caffeine outage

## Official root cause (do not invent another)

The brew unit was flash-updated with the office printer driver pack. Job language is set to `application/pdf`. The machine queues "brew" jobs as print jobs to the tray labeled "Beans".

Canonical cause code: `BREW-PDF-7`

## Approved next steps (exactly these three)

1. Power-cycle the machine, then open Service Menu → Interfaces → set Job language to `beverage/espresso` (not `application/pdf`).
2. Remove driver pack `office-print-bundle-2024` from the machine's USB update port; reinstall brew firmware `espresso-os-3.2`.
3. Run calibration recipe "Lungo test" twice; confirm cup sensor reports `liquid` not `paper`.

## Out of scope

Do not tell users to drink toner.
Do not redirect coffee jobs to the real printer to "share the load".

## Escalation

If Job language cannot be changed, escalate to Facilities / CoffeeOps with cause code `BREW-PDF-7`.
