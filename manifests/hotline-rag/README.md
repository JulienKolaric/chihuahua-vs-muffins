# Hotline RAG — dedicated install (R7)

**Not** the Gen AI Playground. This folder installs an app-team stack: your database + your OGX server, then you ingest Hotline runbooks from a notebook.

Lab guide (What / Why / Success / How): **[`README-GENAI-RAG.md` §R7](../../README-GENAI-RAG.md#r7)**

## What pgvector does

PostgreSQL alone stores text and tables. **pgvector** is an extension that stores *vectors* (numeric fingerprints of text). When a user asks a question, OGX turns the question into a vector and asks Postgres for the nearest stored passages — then the LLM answers from those passages. Without that, a large KB means reading everything or guessing.

## How this folder installs it

1. [`01-postgres-pgvector.yaml`](01-postgres-pgvector.yaml) — deploy Postgres, PVC, Service; init script runs `CREATE EXTENSION IF NOT EXISTS vector;`
2. [`02-secrets.yaml`](02-secrets.yaml) — connection details for OGX + link to Granite
3. [`04-ogx-config.yaml`](04-ogx-config.yaml) — OGX `config.yaml` with **embeddings** + LLM + pgvector (without this, `/v1/models` only shows the LLM)
4. [`03-ogxserver.yaml`](03-ogxserver.yaml) — `OGXServer` with `overrideConfig` → that ConfigMap

Ingest is not in the YAML: the notebook uploads files so OGX chunks, embeds, and writes into that database.

## What we install

| File | Creates | Role |
|------|---------|------|
| [`01-postgres-pgvector.yaml`](01-postgres-pgvector.yaml) | Secret, ConfigMap init, PVC, Deployment `hotline-rag-pgvector`, Service | PostgreSQL 16 + `vector` extension — store embeddings |
| [`02-secrets.yaml`](02-secrets.yaml) | `hotline-rag-pgvector-connection`, `hotline-rag-ogx-llm` | DB connection for OGX · link to existing Granite vLLM |
| [`03-ogxserver.yaml`](03-ogxserver.yaml) | `OGXServer` `hotline-rag-ogx` | API ingest / `file_search` (uses overrideConfig) |
| [`04-ogx-config.yaml`](04-ogx-config.yaml) | ConfigMap `hotline-rag-ogx-config` | Registers **embedding** (`sentence-transformers`) + LLM + pgvector |

Ingest + query: [`notebooks/14_hotline_ogx_pgvector.ipynb`](../../notebooks/14_hotline_ogx_pgvector.ipynb) → Service `hotline-rag-ogx-service:8321`.

## Why separate from Playground

| | Playground | This install |
|--|------------|--------------|
| Resources | `genai-pgvector`, `lsd-genai-playground` | `hotline-rag-pgvector`, `hotline-rag-ogx` |
| Owner | Gen AI studio (auto) | You (YAML in git) |
| Lifecycle | Deleted with playground | You control cleanup |
| Use | Experiment in UI | Backend for a hotline app |

## Docs of record (RHOAI 3.5)

- [Select and deploy a vector database](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_with_ogx/select-and-deploy-a-vector-database_rag)
- [Building RAG applications with OGX](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/building_rag_applications_with_ogx/index)
- [Deploying a OGX server](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_with_ogx/deploying-ogx-server_rag)

Technology Preview. Lab password in secrets is for demos only — change it outside the lab.
