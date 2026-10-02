# Hotline 0800-HELP — Official Knowledge Base (lab)

Synthetic IT runbooks for the Gen AI RAG lab. Keep the Hotline persona funny in chat, but **ground procedures in these documents**.

| Document ID | File | Topic |
|-------------|------|--------|
| `wifi-one-foot` | `01_wifi_one_foot.txt` | Wi-Fi only works on one foot |
| `coffee-pdf` | `02_coffee_pdf.txt` | Coffee machine prints PDFs |
| `elevator-monday` | `03_elevator_monday.txt` | Elevator refuses Mondays |
| `escalation` | `04_escalation_matrix.txt` | When to escalate / fake SLA |
| `faq` | `05_faq.csv` | Short FAQ rows |

Playground Knowledge upload on this sandbox (UI text): **PDF, CSV or TXT** — max 10 files, 10 MB each (not `.doc` / `.md`).

Regenerate TXT from Markdown:

```bash
cd data/hotline-kb
mkdir -p upload
for f in 01_wifi_one_foot 02_coffee_pdf 03_elevator_monday 04_escalation_matrix; do
  cp "${f}.md" "upload/${f}.txt"
done
cp 05_faq.csv upload/
ls upload/
```
