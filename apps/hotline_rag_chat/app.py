"""Hotline chat UI → dedicated OGX + pgvector (R7 ingest or AutoRAG Pattern 1 store)."""

from __future__ import annotations

import os

import requests
import streamlit as st

SYSTEM = """You are Hotline 0800-HELP. Always use the file_search tool first.

HIT when retrieved text matches THIS issue (elevator, Wi-Fi one-foot, coffee-prints-PDF, SSID, escalation).
Use the matching runbook: copy codes EXACTLY (LIFT-MON-1, BREW-PDF-7, WIFI-BALANCE-42, CAMPUS-SECURE).
Keep event names / firmware from the chunks. Short ticket. Max 100 words.

MISS when the issue is not in those runbooks (fridge, opera, unicorn, or no relevant chunk).
Do not reuse a coffee/Wi-Fi/elevator code for a fridge.
Reply exactly:
HELP-xxxx
No matching runbook in the operator-uploaded KB for this issue. Escalate to Level 2. Ask for location."""

OGX = os.environ.get(
    "OGX_URL",
    "http://hotline-rag-ogx-service.genai-hotline.svc.cluster.local:8321",
).rstrip("/")
V1 = f"{OGX}/v1"
VECTOR_STORE_ID = os.environ.get("VECTOR_STORE_ID", "").strip()
LLM_ID = os.environ.get("OGX_LLM_ID", "").strip()
# AutoRAG Pattern 1 freeze: number_of_chunks = 5
FILE_SEARCH_MAX_RESULTS = int(os.environ.get("FILE_SEARCH_MAX_RESULTS", "5"))
PATTERN_LABEL = os.environ.get("AUTORAG_PATTERN", "").strip()


def list_llm_id() -> str:
    if LLM_ID:
        return LLM_ID
    models = requests.get(f"{V1}/models", timeout=60).json().get("data") or []
    for m in models:
        if (m.get("custom_metadata") or {}).get("model_type") == "llm":
            return m["id"]
    raise RuntimeError("No llm model on OGX /v1/models")


def ask_ogx(question: str, llm_id: str, vs_id: str) -> tuple[str, str]:
    file_search: dict = {
        "type": "file_search",
        "vector_store_ids": [vs_id],
        "max_num_results": FILE_SEARCH_MAX_RESULTS,
    }
    payload = {
        "model": llm_id,
        "input": question,
        "instructions": SYSTEM,
        "temperature": 0.1,
        "tool_choice": "required",
        "tools": [file_search],
    }
    r = requests.post(f"{V1}/responses", json=payload, timeout=180)
    r.raise_for_status()
    body = r.json()
    answer = ""
    n_hits = 0
    for item in body.get("output") or []:
        if item.get("type") == "file_search_call":
            n_hits = len(item.get("results") or [])
        if item.get("type") == "message":
            for c in item.get("content") or []:
                if c.get("type") == "output_text":
                    answer = (c.get("text") or "").strip()
    tag = f" · {PATTERN_LABEL}" if PATTERN_LABEL else ""
    meta = (
        f"OGX file_search · top_k={FILE_SEARCH_MAX_RESULTS} · "
        f"retrieved={n_hits} · vs={vs_id[:18]}…{tag}"
    )
    return answer or "(empty response)", meta


st.set_page_config(page_title="Hotline RAG", page_icon="🔎", layout="centered")
st.title("Hotline 0800-HELP — RAG")
if PATTERN_LABEL:
    st.caption(
        f"End-user chat → OGX + pgvector · AutoRAG **{PATTERN_LABEL}** vector store "
        f"(chunk recursive 512/32 · top_k={FILE_SEARCH_MAX_RESULTS})."
    )
else:
    st.caption(
        "End-user chat → your OGX server searches pgvector "
        "(R7 notebook ingest, or set AUTORAG_PATTERN after pointing VECTOR_STORE_ID at a Pattern store)."
    )

st.sidebar.markdown("**Backend**")
st.sidebar.code(OGX, language=None)
st.sidebar.markdown("**Vector store**")
st.sidebar.code(VECTOR_STORE_ID or "(set VECTOR_STORE_ID)", language=None)
st.sidebar.markdown("**Retrieval**")
st.sidebar.code(f"top_k={FILE_SEARCH_MAX_RESULTS}", language=None)
if PATTERN_LABEL:
    st.sidebar.markdown("**AutoRAG**")
    st.sidebar.code(PATTERN_LABEL, language=None)

if not VECTOR_STORE_ID:
    st.error(
        "Missing env `VECTOR_STORE_ID`. Use the AutoRAG Pattern 1 store "
        "`vs_75001176-…` (R9) or an R7 `vs_…`, then set it on this Deployment."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])

prompt = st.chat_input("Describe a short IT problem…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching runbooks in pgvector…"):
            try:
                llm_id = list_llm_id()
                answer, meta = ask_ogx(prompt, llm_id, VECTOR_STORE_ID)
            except Exception as exc:  # noqa: BLE001
                answer = f"Error calling OGX: `{exc}`"
                meta = "error"
        st.markdown(answer)
        st.caption(meta)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "meta": meta}
    )
