# OpenShift AI 3.5 — lab hub

Hands-on labs on **one cluster / one team**. Two independent journeys (plus optional extras).

| Lab | File | What you practice |
|-----|------|-------------------|
| **Predictive** — Chihuahua vs Muffin | [`README-PREDICTIVE.md`](README-PREDICTIVE.md) | S3 → train → **OVMS** → guardrails → **TrustyAI** → pipelines → **AutoML** |
| **Gen AI** — Playground / OGX | [`README-GENAI.md`](README-GENAI.md) | **`genai-hotline`** · vLLM Hotline · **Open WebUI → Streamlit/S2I → Playground** |
| **Gen AI — Hotline KB RAG** | [`README-GENAI-RAG.md`](README-GENAI-RAG.md) | Playground Knowledge → **`hotline-kb-chat`** Streamlit · AutoRAG later |

| | Predictive | Gen AI |
|--|------------|--------|
| Model type | Classifier (ONNX / OVMS) | Generative (vLLM / catalog) |
| Typical I/O | Image → scores | Prompt → text |
| Theme | Muffin ↔ chihuahua | Independent fun demo |

**Docs of record (RHOAI 3.5):** conflicts go to [Red Hat OpenShift AI 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5). Topic SoT also in `.cursor/rules/rhoai-35-official-docs.mdc` (OGX, AutoML, MLflow, AutoRAG, MCP…).

### Optional / related

| Lab | File |
|-----|------|
| TrustyAI Step 8 pointer | [`docs/trustyai-db-install/GUIDE.md`](docs/trustyai-db-install/GUIDE.md) → predictive README |
| **Later:** Large KB (pgvector / Milvus / OGX) | Map in [`README-GENAI-RAG.md`](README-GENAI-RAG.md) R7 — after ConfigMap lab app |
| **Later:** AutoRAG on Hotline KB | After R4 / R6 — use `data/hotline-kb/eval/golden_questions.json` |
| **Later:** Autonomous day-summary agent | Agent on OpenShift AI that synthesizes the user’s daily events (calendar / mail / tools via MCP) |

### How to use

1. Pick **one** lab README and follow it top to bottom.  
2. You run all cluster / UI actions (facilitator does not apply changes for you).  
3. Freeze validated screenshots/commands back into that lab’s README.
