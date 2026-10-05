# Hotline KB chat (Streamlit)

End-user Hotline UI: search runbooks → same in-cluster vLLM as Playground.

- OpenShift name: `hotline-kb-chat`
- Runbooks: ConfigMap `hotline-kb` mounted at `/etc/hotline-kb` (`KB_DIR`)
- Source files for the ConfigMap: `kb/` (also local fallback)
- Lab steps: [`README-GENAI.md`](../../README-GENAI.md) §R6
