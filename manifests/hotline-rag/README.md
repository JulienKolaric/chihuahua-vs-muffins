# Hotline RAG — dedicated install (R7)

**Not** the Gen AI Playground. This folder installs an app-team stack: your database + your OGX server, then you ingest Hotline runbooks from a notebook.

Lab guide (What / Why / Success / How): **[`README-GENAI-RAG.md` §R7](../../README-GENAI-RAG.md#r7)**

## What we install

| File | Creates | Role |
|------|---------|------|
| [`01-postgres-pgvector.yaml`](01-postgres-pgvector.yaml) | Secret, ConfigMap init, PVC, Deployment `hotline-rag-pgvector`, Service | PostgreSQL 16 + `vector` extension — store embeddings |
| [`02-secrets.yaml`](02-secrets.yaml) | `hotline-rag-pgvector-connection`, `hotline-rag-ogx-llm` | DB connection for OGX · link to existing Granite vLLM |
| [`03-ogxserver.yaml`](03-ogxserver.yaml) | `OGXServer` `hotline-rag-ogx` | API ingest / `file_search` / chat with retrieval (`ENABLE_PGVECTOR=true`) |

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
