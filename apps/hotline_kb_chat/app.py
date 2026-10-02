"""Hotline 0800-HELP with local runbook search — Streamlit UI for OpenShift."""

from __future__ import annotations

import os

import streamlit as st
from openai import OpenAI

from kb_retrieve import KB_DIR, load_docs, retrieve

SYSTEM_HIT = """You are Hotline 0800-HELP. Keep answers short and readable.
Use ONLY the operator-uploaded Hotline KB runbook(s) in CONTEXT below.
Copy cause codes EXACTLY (LIFT-MON-1, BREW-PDF-7, WIFI-BALANCE-42). Never invent codes.
Keep KB-specific nouns (event names, fault codes, SSIDs, firmware). No generic IT advice.
Format ONLY:
HELP-xxxx
Source: Operator-uploaded Hotline KB runbook.
Cause: <exact KB code> — <one sentence from KB root cause>
Steps:
1) <KB step 1>
2) <KB step 2>
3) <KB step 3>
Close: one short line.
Max 100 words. No document dump, no other runbooks, no file names."""

SYSTEM_MISS = """You are Hotline 0800-HELP.
There is NO matching runbook for this user issue in the operator-uploaded KB.
Reply EXACTLY in this shape (you may change HELP-xxxx digits only):
HELP-xxxx
No matching runbook in the operator-uploaded KB for this issue. Escalate to Level 2. Ask for location.
Do NOT invent or reuse another runbook's cause code. Do NOT claim Source/KB. Max 35 words."""

BASE_URL = os.environ.get(
    "GRANITE_URL",
    "http://redhataigranite-40-h-tiny-fp8-predictor.genai-hotline.svc.cluster.local:8080/v1",
).rstrip("/")
if not BASE_URL.endswith("/v1"):
    BASE_URL = BASE_URL.rstrip("/") + "/v1"

MODEL = os.environ.get("GRANITE_MODEL", "redhataigranite-40-h-tiny-fp8")
API_KEY = os.environ.get("GRANITE_API_KEY", "not-needed")

st.set_page_config(page_title="Hotline KB", page_icon="📚", layout="centered")
st.title("Hotline 0800-HELP — KB")
st.caption(
    "Chat app: search Hotline runbooks (ConfigMap or local folder) → same vLLM as Playground."
)

DOCS = load_docs()
st.sidebar.markdown(f"**Runbooks:** {len(DOCS)}")
st.sidebar.caption(f"`KB_DIR` = `{KB_DIR}`")
for d in DOCS:
    st.sidebar.code(d.name, language=None)

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

    # Reload each question so ConfigMap edits appear after kubelet sync (no image rebuild)
    docs = load_docs()
    hits = retrieve(prompt, docs, top_k=1)
    if hits:
        context = "\n\n---\n\n".join(
            f"FILE: {doc.name}\n{doc.text}" for doc, _ in hits
        )
        system = SYSTEM_HIT + "\n\nCONTEXT:\n" + context
        meta = "KB hit: " + ", ".join(f"{doc.name} ({sc:.2f})" for doc, sc in hits)
    else:
        system = SYSTEM_MISS
        meta = "KB miss — no close runbook"

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    api_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    with st.chat_message("assistant"):
        with st.spinner("Checking runbooks…"):
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                    temperature=0.1,
                    max_tokens=512,
                )
                answer = (resp.choices[0].message.content or "").strip()
            except Exception as exc:  # noqa: BLE001 — show raw error in lab UI
                answer = f"Error calling model: `{exc}`"
        st.markdown(answer)
        st.caption(meta)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "meta": meta}
    )
