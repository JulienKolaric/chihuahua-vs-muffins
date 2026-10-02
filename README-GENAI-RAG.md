# Gen AI — Hotline KB RAG (OpenShift AI 3.5)

Continuation of [`README-GENAI.md`](README-GENAI.md) (Hotline LLM UIs). Same project **`genai-hotline`**, same Granite model — now **grounded** on a small knowledge base.

Hub: [`README.md`](README.md)

**Docs of record:**

- [Experimenting with models in the gen AI playground — RAG](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/experimenting_with_models_in_the_gen_ai_playground/testing-your-model-with-rag_rhoai-user)
- [Building RAG applications with OGX](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/building_rag_applications_with_ogx/index)
- Later: [Working with AutoRAG](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/working_with_autorag/index)

Playground / Gen AI studio RAG is **Technology Preview**.

---

## Progress

| Step | Topic | Done |
|------|--------|------|
| R0 | [Why RAG on Hotline](#r0) | |
| R1 | [Knowledge base files](#r1) | |
| R2 | [Before/after without Knowledge](#r2) | |
| R3 | [Playground Knowledge upload](#r3) | ✅ |
| R4 | [Grounded Hotline prompts](#r4) | ✅ HIT elevator · MISS fridge |
| R5 | [Out of scope / next](#r5) | Playground → real hotline app |

---

<a id="r0"></a>

# R0 — Why RAG on Hotline

### What we want
Show that the same Hotline persona can answer from **official runbooks** instead of inventing steps.

### Why
G3–G5 proved chat UIs on a Ready LLM. Customers next ask: *“How do we stop hallucinations on procedures?”* → retrieval-augmented generation.

### Success looks like
- You can say in one sentence: LLM alone invents; RAG retrieves then answers
- Everyone knows **`genai-pgvector` was created automatically when the Playground was activated** (not a manual install)

### How

**Room arc:**

1. Ask a Hotline question **without** Knowledge → funny but **wrong** procedure codes  
2. Upload KB → ask again → answers cite **WIFI-BALANCE-42** / **BREW-PDF-7** / **LIFT-MON-1**  
3. (Later lab) AutoRAG optimizes chunking/retrieval on the same corpus

**Where does pgvector come from?**

When you completed [G5 — Playground](README-GENAI.md#g5) (**Add to playground** / Creating playground), OpenShift AI created:

- `OGXServer` **`lsd-genai-playground`**
- Deployment / Service / PVC **`genai-pgvector`** (PostgreSQL 16 + pgvector), owned by that `OGXServer`, label `gen-ai.opendatahub.io/pgvector=true`

That is the vector store backing Playground **Knowledge** uploads on this project. Confirm anytime:

```bash
oc -n genai-hotline get deploy genai-pgvector
oc -n genai-hotline get ogxserver lsd-genai-playground -o jsonpath='{.metadata.name} owner of pgvector via UI/operator{"\n"}'
```

---

<a id="r1"></a>

# R1 — Knowledge base files

### What we want
Have a small Hotline KB ready in formats the Playground accepts.

### Why
Playground Knowledge on this sandbox accepts **PDF, CSV or TXT** (UI: up to 10 files, 10 MB each) — not `.doc` / `.md`.

### Success looks like
- Repo folder `data/hotline-kb/` present
- `data/hotline-kb/upload/` contains `.txt` + `05_faq.csv` for the dashboard

### How

Source Markdown (editable) + CSV live under [`data/hotline-kb/`](data/hotline-kb/).  
Pre-built upload artifacts:

| Upload file | Topic | Cause code / key fact |
|-------------|--------|------------------------|
| `upload/01_wifi_one_foot.txt` | Wi-Fi one foot | `WIFI-BALANCE-42` |
| `upload/02_coffee_pdf.txt` | Coffee → PDF | `BREW-PDF-7` |
| `upload/03_elevator_monday.txt` | Elevator Mondays | `LIFT-MON-1` |
| `upload/04_escalation_matrix.txt` | Escalation | `#coffeeops` / `#net-l2` |
| `upload/05_faq.csv` | FAQ | SSID `CAMPUS-SECURE` |

Regenerate TXT from Markdown if you edit sources:

```bash
cd data/hotline-kb
mkdir -p upload
for f in 01_wifi_one_foot 02_coffee_pdf 03_elevator_monday 04_escalation_matrix; do
  cp "${f}.md" "upload/${f}.txt"
done
cp 05_faq.csv upload/
ls upload/
```

**Expected output**

```text
01_wifi_one_foot.txt
02_coffee_pdf.txt
03_elevator_monday.txt
04_escalation_matrix.txt
05_faq.csv
```

Golden questions for later AutoRAG: [`data/hotline-kb/eval/golden_questions.json`](data/hotline-kb/eval/golden_questions.json).

---

<a id="r2"></a>

# R2 — Before/after without Knowledge

### What we want
Capture a **baseline** Hotline answer with Knowledge **Off**.

### Why
The room must see the delta. Without a baseline, RAG looks like “just a better prompt”.

### Success looks like
- One chat turn with Knowledge disabled
- Answer invents steps / omits official cause codes (typical)

### How

1. **Gen AI studio → Playground** → project **`genai-hotline`**
2. **Settings → Knowledge** → ensure no files / Knowledge off  
3. **Prompt** — use the Hotline system prompt from [README-GENAI.md G2](README-GENAI.md#g2) **or** the grounded variant in [R4](#r4) without docs yet  
4. Ask: `The elevator refuses Mondays`  
5. Note whether cause code `LIFT-MON-1` and calendar event `Maintenance spirits — Mondays` appear (usually **no**)

Optional: screenshot as `docs/screenshots/step-genai-rag-before.png` when you freeze.

---

<a id="r3"></a>

# R3 — Playground Knowledge upload

### What we want
Upload the Hotline KB into Playground Knowledge so retrieval can run.

### Why
This is the product path for experimenting with RAG on OpenShift AI 3.5 ([official procedure](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/experimenting_with_models_in_the_gen_ai_playground/testing-your-model-with-rag_rhoai-user)).

### Success looks like
- Notification **Source uploaded** (or equivalent)
- Files listed under Uploaded files
- Knowledge available for chat

### How

Requires Playground already created ([README-GENAI G5](README-GENAI.md#g5)).

1. Dashboard → **Gen AI studio → Playground** → **`genai-hotline`**
2. Settings panel → tab **Knowledge**
3. **Upload files** → upload from `data/hotline-kb/upload/` (all five files, or start with the three runbooks)
4. Optional chunk settings: leave defaults first; tune later if retrieval is weak ([Understanding RAG settings](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/experimenting_with_models_in_the_gen_ai_playground/testing-your-model-with-rag_rhoai-user) in the same doc set)
5. Wait until each file shows as uploaded / processed

**Expected signals**

- UI: files listed under Knowledge; RAG toggle **On**
- Cluster: `genai-pgvector` still **Ready** (instantiated at Playground creation — see [R0](#r0) / [G5](README-GENAI.md#g5))

```bash
oc -n genai-hotline get deploy genai-pgvector
# expect: 1/1 Ready
```

> Official note: Playground RAG is for **experimentation** with the playground vector store (here: the auto-provisioned **`genai-pgvector`**). Building a full app stack with a separately managed remote Milvus/pgvector is covered under [RAG with OGX](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/building_rag_applications_with_ogx/index) — out of scope for R3.

### If chat fails with `auto tool choice requires --enable-auto-tool-choice`

Playground Knowledge/RAG calls the model with **tool choice `auto`** (knowledge search). Your vLLM deployment must expose tool calling.

**Error shape:**

```text
[invalid_prompt] "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

**Fix (redeploy / edit the generative model in `genai-hotline`):** add **custom serving runtime arguments** (Advanced / additional args), then wait Ready again:

```text
--enable-auto-tool-choice
--tool-call-parser=granite4
```

For this lab model (`granite-4.0-h-tiny`), prefer parser **`granite4`** ([vLLM tool calling](https://docs.vllm.ai/en/latest/features/tool_calling/)). If the runtime rejects `granite4`, try `granite`.

UI path: **AI hub → Models → Deployments** → `RedHatAI/granite-4.0-h-tiny-FP8-dynamic` → edit → **Additional serving runtime arguments** (or equivalent) → save → wait **Ready**.

**1× GPU sandbox tip:** prefer **Stop** the deployment → edit args → **Start**, or choose deployment strategy **Recreate** (not Rolling update). Rolling needs a second GPU briefly and often fails with `Insufficient nvidia.com/gpu`.

CLI check after Ready:

```bash
oc -n genai-hotline get deploy -l serving.kserve.io/inferenceservice=redhataigranite-40-h-tiny-fp8 \
  -o jsonpath='{range .items[0].spec.template.spec.containers[?(@.name=="kserve-container")].args[*]}{@}{"\n"}{end}'
```

Expect lines including `--enable-auto-tool-choice` and `--tool-call-parser=granite4` (or `granite`).

---

<a id="r4"></a>

# R4 — Grounded Hotline prompts

### What we want
Chat again so answers use **KB facts** (cause codes, exact steps).

### Why
Retrieval alone is not enough; the system prompt must order the model to **prefer documents**.

### Success looks like
- Elevator question mentions `LIFT-MON-1` and deleting `Maintenance spirits — Mondays`
- Coffee question mentions `BREW-PDF-7` / `espresso-os-3.2`
- Wi-Fi question mentions `WIFI-BALANCE-42` / `CAMPUS-SECURE`

### How

**Important:** after you change **Prompt**, turn **Knowledge/RAG** on/off, or finish an upload, click **+ New chat** so the new settings apply (an open thread can keep old prompt / tool context). With settings already stable, HIT then MISS in the **same** chat can work — New chat is still the safe reset when something looks sticky.

1. **Settings → Prompt** — paste:

```text
You are Hotline 0800-HELP. Keep answers short and readable.

Always call knowledge_search first. Then HIT or MISS for THIS user issue only.

Relevance rule (critical):
- Retrieved chunks are NOT automatically a HIT. “5 sources retrieved” can still be a MISS.
- HIT only if the chunk is clearly about the SAME product/symptom (elevator↔elevator, Wi-Fi↔Wi-Fi, coffee↔coffee).
- If the user says fridge/opera/unicorn and chunks talk about Wi-Fi, coffee, or elevators → MISS.

HIT (same-issue runbook only):
- Use the operator-uploaded Hotline KB procedure (not generic IT advice).
- Copy the KB cause code EXACTLY (LIFT-MON-1, BREW-PDF-7, WIFI-BALANCE-42). Never invent codes.
- Keep the KB’s specific nouns (event names, fault codes, SSIDs, firmware names). Do not replace them with generic “notify users / check calendar”.
- Format ONLY:
HELP-xxxx
Source: Operator-uploaded Hotline KB runbook.
Cause: <exact KB code> — <one sentence from KB root cause>
Steps:
1) <KB step 1>
2) <KB step 2>
3) <KB step 3>
Close: one short line.
- Max 100 words. No document dump, no other runbooks, no chunk/file ids.

Example HIT shape for elevators (when KB matches):
HELP-1042
Source: Operator-uploaded Hotline KB runbook.
Cause: LIFT-MON-1 — recurring calendar block "Maintenance spirits — Mondays"; door code NO-MON.
Steps:
1) On PLC HMI Calendar, delete recurring event Maintenance spirits — Mondays.
2) Clear fault NO-MON, run lobby-to-top test trip.
3) Add change record that the Monday spirit block was removed.
Close: Anything else I can misdiagnose today?

MISS:
HELP-xxxx
No matching runbook in the operator-uploaded KB for this issue. Escalate to Level 2. Ask for location.
Do NOT invent or reuse another runbook’s cause code. Do NOT claim Source/KB. Max 35 words.
```

2. **Model** — Temperature ≈ **0.1**, Streaming On  
3. **+ New chat** (required — see note above)  
4. Ask in turn:
   - `The elevator refuses Mondays`
   - `My coffee machine prints PDF instead of coffee`
   - `Wi-Fi works only when I stand on one foot`
   - `Which team owns BREW-PDF-7?`
   - Out-of-KB control: `My fridge is singing opera` → must **MISS** (no invented `FRIG-*` code; must **not** claim the operator KB)

**Expected output (shape)**

```text
HELP-1042
Source: Operator-uploaded Hotline KB runbook.
Cause: LIFT-MON-1 — obsolete Monday calendar block …
Steps:
1) delete recurring event Maintenance spirits — Mondays
2) clear fault NO-MON …
3) …
Close: …
```

Out-of-KB shape:

```text
… no matching runbook in the knowledge base the operator uploaded …
… escalate …
(no fake cause code)
```

Optional freeze: `docs/screenshots/step-genai-rag-after.png`

![Playground RAG — elevator HIT](docs/screenshots/step-genai-rag-elevator-hit.png)

**Frozen HIT:** `The elevator refuses Mondays` → `LIFT-MON-1` + *Maintenance spirits — Mondays* + official steps · sources retrieved.

![Playground RAG — fridge MISS](docs/screenshots/step-genai-rag-fridge-miss.png)

**Frozen MISS:** `My fridge is singing opera` → no invented cause code · escalate · no Source/KB claim (even with sources retrieved).

![Playground RAG — HIT then MISS same session](docs/screenshots/step-genai-rag-hit-miss.png)

**Known limit (tiny Granite + always-on retrieval):** an out-of-KB question can still retrieve nearest chunks (Wi-Fi/coffee) and the model may false-HIT. Demo tip: reinforce MISS in the prompt; optionally toggle RAG **Off** once to contrast “no KB path”.

![False HIT example — fridge reused Wi-Fi runbook](docs/screenshots/step-genai-rag-fridge-false-hit.png)

**Teaching point:** same model + same persona; Knowledge tab is what changed. Playground is for **operators / builders** to prove grounded answers — not the UI end users call.

---

<a id="r5"></a>

# R5 — Out of scope / next (Playground → real hotline app)

### What we want
Leave the room with a clear map from **Playground Knowledge** (what we just validated) to a **hotline app** callers actually use — without building that app in this hour.

### Why
Playground is an experimentation surface (prompt, Knowledge upload, HIT/MISS). End users never open Gen AI studio. Production needs the same three pieces behind a normal chat UI: **LLM endpoint + vector store + retrieve-then-generate** (plus your system prompt).

### Success looks like
- You can name the split: Playground = prove RAG; app = ship RAG
- Backlog pointers match RHOAI 3.5 docs (OGX RAG / AutoRAG)

### How

**This lab stops at Playground Knowledge.** What stays the same in “real life”:

| Piece (validated here) | In a hotline app |
|------------------------|------------------|
| vLLM Granite in `genai-hotline` | Same OpenAI-compatible `/v1` endpoint |
| Operator-uploaded runbooks | Ingest into a vector store (keep `data/hotline-kb`) |
| Grounded HIT/MISS system prompt | Baked into the app (or OGX agent), not a Settings tab users edit |
| Playground Knowledge / `knowledge_search` | App or **OGX RAG stack** does retrieve → inject context → generate |

**Official path on OpenShift AI 3.5** ([Building RAG applications with OGX](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/building_rag_applications_with_ogx/index) — Technology Preview):

1. **OGXServer** wired to the inference model + vector store (pgvector / Milvus)  
2. **Ingest** Hotline KB with Docling (pipeline or notebook) so embeddings stay in sync  
3. **Query** that stack from your UI (extend [`apps/hotline_chat`](apps/hotline_chat) / Open WebUI, or a thin agent front-end) — callers only see the chat

**Next (separate sessions):**

| Topic | Why |
|-------|-----|
| **AutoRAG** on `data/hotline-kb` + `eval/golden_questions.json` | Optimize chunking/embedding/retrieval before you hard-wire the app ([AutoRAG docs](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/working_with_autorag/index)) |
| **RAG with OGX** (Docling ingest, remote pgvector/Milvus) | App-style pipeline beyond Playground experimentation |
| **Open WebUI / Streamlit + RAG** | Same files + grounded prompt; UI employees actually open |
| **Day-summary agent + MCP** | Later autonomous agent idea |

---

## Link back

Hub: **[README.md](README.md)** · LLM UIs: **[README-GENAI.md](README-GENAI.md)** · Predictive: **[README-PREDICTIVE.md](README-PREDICTIVE.md)**
