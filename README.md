# OpenShift AI 3.5 — lab hub

Hands-on labs on **one cluster / one team**. Two independent journeys (plus optional extras).

| Lab | File | What you practice |
|-----|------|-------------------|
| **Predictive** — Chihuahua vs Muffin | [`README-PREDICTIVE.md`](README-PREDICTIVE.md) | S3 → train → **OVMS** → guardrails → **TrustyAI** → pipelines → **AutoML** |
| **Gen AI** — Hotline (Playground → RAG → AutoRAG) | [`README-GENAI.md`](README-GENAI.md) | **`genai-hotline`** · vLLM · Open WebUI → Streamlit → Playground → **KB RAG** → AutoRAG |

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
| **Hotline AutoRAG** | [`README-GENAI.md`](README-GENAI.md) **[R9](README-GENAI.md#r9)** — bake-off → notebooks → **[R9.6](README-GENAI.md#r96)** app on Pattern 1 · HIT OK · fridge soft-MISS |
| **Hotline RAG backlog** | [`README-GENAI.md`](README-GENAI.md) **[R10](README-GENAI.md#r10)** — remote embeddings · Milvus · Docling · harden app · day-summary agent |
| **Later:** Autonomous day-summary agent | Calendar / mail / tools via MCP — see R10 #5 |

### How to use

1. Pick **one** lab README and follow it top to bottom.  
2. You run all cluster / UI actions (facilitator does not apply changes for you).  
3. Freeze validated screenshots/commands back into that lab’s README.
