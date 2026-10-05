# Hotline RAG chat (Streamlit)

End-user UI for the **dedicated** OGX + pgvector stack.

- OpenShift name: `hotline-rag-chat`
- Talks to `hotline-rag-ogx-service` with `file_search` + `VECTOR_STORE_ID`
- **Prompt:** `SYSTEM` in [`app.py`](app.py) → OGX `instructions` (not Playground, not the DB)

**Path after AutoRAG:** bake-off in the dashboard → **inference notebook** to validate the recipe → **this app** pointed at the Pattern 1 store ([R9.6](../../README-GENAI-RAG.md#r96)). AutoRAG notebooks are **not** this UI.

After R9.6, env should include `VECTOR_STORE_ID=vs_75001176-…`, `FILE_SEARCH_MAX_RESULTS=5`, `AUTORAG_PATTERN=Pattern 1`.

Older path: R7 notebook ingest (`hotline-kb-pgvector`) then [R8](../../README-GENAI-RAG.md#r8) without AutoRAG.

Contrast: [`apps/hotline_kb_chat`](../hotline_kb_chat) searches a ConfigMap (R6), not pgvector.
