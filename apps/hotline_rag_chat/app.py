"""Hotline chat UI → dedicated OGX + pgvector (after R7 notebook ingest)."""

from __future__ import annotations

import os

import requests
import streamlit as st

SYSTEM = """You are Hotline 0800-HELP. Keep answers short and readable.
Use ONLY retrieved runbooks when they match the SAME product/symptom.
Copy cause codes exactly (LIFT-MON-1, BREW-PDF-7, WIFI-BALANCE-42). Never invent codes.
Keep KB-specific nouns (event names, fault codes, SSIDs, firmware).
If nothing matches, reply:
HELP-xxxx
No matching runbook in the operator-uploaded KB for this issue. Escalate to Level 2. Ask for location.
Max 100 words. No document dump."""

OGX = os.environ.get(
    "OGX_URL",
    "http://hotline-rag-ogx-service.genai-hotline.svc.cluster.local:8321",
).rstrip("/")
V1 = f"{OGX}/v1"
VECTOR_STORE_ID = os.environ.get("VECTOR_STORE_ID", "").strip()
LLM_ID = os.environ.get("OGX_LLM_ID", "").strip()


def list_llm_id() -> str:
    if LLM_ID:
        return LLM_ID
    models = requests.get(f"{V1}/models", timeout=60).json().get("data") or []
    for m in models:
        if (m.get("custom_metadata") or {}).get("model_type") == "llm":
            return m["id"]
    raise RuntimeError("No llm model on OGX /v1/models")


def ask_ogx(question: str, llm_id: str, vs_id: str) -> tuple[str, str]:
    payload = {
        "model": llm_id,
        "input": question,
        "instructions": SYSTEM,
        "temperature": 0.1,
        "tools": [{"type": "file_search", "vector_store_ids": [vs_id]}],
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
    meta = f"OGX file_search · retrieved={n_hits} · vs={vs_id[:18]}…"
    return answer or "(empty response)", meta


st.set_page_config(page_title="Hotline RAG", page_icon="🔎", layout="centered")
st.title("Hotline 0800-HELP — RAG")
st.caption(
    "End-user chat → your OGX server searches pgvector (runbooks ingested in the R7 notebook)."
)

st.sidebar.markdown("**Backend**")
st.sidebar.code(OGX, language=None)
st.sidebar.markdown("**Vector store**")
st.sidebar.code(VECTOR_STORE_ID or "(set VECTOR_STORE_ID)", language=None)

if not VECTOR_STORE_ID:
    st.error(
        "Missing env `VECTOR_STORE_ID`. Run the R7 notebook first, copy `vs_…`, "
        "then set it on this Deployment and rollout."
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
