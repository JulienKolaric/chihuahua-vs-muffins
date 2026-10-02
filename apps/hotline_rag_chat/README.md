# Hotline RAG chat (Streamlit)

End-user UI for the **dedicated** OGX + pgvector stack (R7 → R8).

- OpenShift name: `hotline-rag-chat`
- Talks to `hotline-rag-ogx-service` with `file_search` + `VECTOR_STORE_ID`
- Runbooks must already be indexed via [`notebooks/14_hotline_ogx_pgvector.ipynb`](../../notebooks/14_hotline_ogx_pgvector.ipynb) (**validate before** deploying this app)
- Lab steps: [`README-GENAI-RAG.md`](../../README-GENAI-RAG.md) §R8

Contrast: [`apps/hotline_kb_chat`](../hotline_kb_chat) searches a ConfigMap (R6), not pgvector.
