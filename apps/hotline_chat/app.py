"""Hotline 0800-HELP — thin Streamlit client for the in-cluster vLLM endpoint."""

from __future__ import annotations

import os

import streamlit as st
from openai import OpenAI

SYSTEM_PROMPT = """You are “Hotline 0800-HELP”, an over-the-top IT support agent.
For every user message (a short problem description):
1) Invent a ticket ID like HELP-1042
2) Give a ridiculous but PG-rated root cause (2 sentences)
3) Give exactly 3 numbered next steps
4) End with: “Is there anything else I can misdiagnose today?”
Keep the whole answer under 120 words. No markdown tables."""

BASE_URL = os.environ.get(
    "GRANITE_URL",
    "http://redhataigranite-40-h-tiny-fp8-predictor.genai-hotline.svc.cluster.local:8080/v1",
).rstrip("/")
if not BASE_URL.endswith("/v1"):
    BASE_URL = BASE_URL.rstrip("/") + "/v1"

MODEL = os.environ.get("GRANITE_MODEL", "redhataigranite-40-h-tiny-fp8")
API_KEY = os.environ.get("GRANITE_API_KEY", "not-needed")

st.set_page_config(page_title="Hotline 0800-HELP", page_icon="☎️", layout="centered")
st.title("Hotline 0800-HELP")
st.caption("External chat app → same vLLM endpoint as Gen AI Playground (OpenShift AI).")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Describe a short IT problem…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

    with st.chat_message("assistant"):
        with st.spinner("Misdiagnosing…"):
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
    st.session_state.messages.append({"role": "assistant", "content": answer})
