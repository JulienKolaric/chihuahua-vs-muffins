# Gen AI lab — OpenShift AI Playground (OGX)

**Separate** from the Chihuahua vs Muffin predictive lab ([README-PREDICTIVE.md](README-PREDICTIVE.md)).

| | Predictive lab (`README-PREDICTIVE.md`) | **This lab** |
|--|------------------------------------------|--------------|
| Goal | Train / serve / monitor an **image classifier** (OVMS) | Chat with a **generative** model (LLM) |
| Theme | Muffin ↔ chihuahua photos | **Independent** fun demo (no images required) |
| UI | Workbench, Deployments (predictive), TrustyAI… | External chat UIs + **Gen AI studio → Playground** |


**One-liner for the room:** same OpenShift AI cluster, **different product surface** — scores vs sentences.

Hub: [`README.md`](README.md)

Source of truth (wins over assumptions):

- [Working with OGX (RHOAI 3.5)](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html-single/working_with_ogx/index)
- Dashboard / DSC notes validated on lab sandboxes (below)

Gen AI studio / Playground are often **Technology Preview** — need admin enablement + usually a **GPU**.

---

## Progress

| Step | Topic | Done |
|------|--------|------|
| G0 | [Why Gen AI here](#g0) | |
| G1 | [Admin — OGX + Gen AI studio](#g1) | |
| G1b | [New project + free GPU](#g1b) | |
| G2 | [Deploy a chat model](#g2) | ✅ Ready |
| G3 | [Open WebUI — same model](#g3) | ✅ |
| G4 | [Streamlit + Python S2I](#g4) | ✅ |
| G5 | [Playground — Hotline (simplest)](#g5) | ✅ |
| G6 | [Out of scope](#g6) | |

---

<a id="g0"></a>

# G0 — What we want to show

### What we want
Prove that OpenShift AI can host a **chat LLM** and that people can talk to it in **Playground** — without tying the story to image classification.

### Why
After the predictive lab, the audience already saw OVMS. Gen AI answers a different question: *can we deploy and use a generative model on the same platform?* Mixing muffin/chihuahua into the LLM prompt muddies that message.

### Success looks like
- Everyone can explain in one sentence: predictive = labels/scores · generative = text
- Same Hotline persona on **Open WebUI** → **Streamlit** → **Playground** (integrated UI last)

### How

Demo theme for this lab: **Hotline 0800-HELP** — an absurd IT support bot that answers everyday “help, my thing is broken” tickets with over-the-top scripts (ticket id, root cause, next steps). Lab default: **English** system prompt + English user questions.

**Room arc (after the model is Ready):**

1. **Open WebUI** — full OSS chat UX on the cluster  
2. **Streamlit + S2I** — tiny custom app via Software Catalog Python builder  
3. **OpenShift AI Playground** — simplest path (product UI, no YAML)

Optional later (not required): wire OVMS outputs into a *second* prompt. Keep that out of the critical path.

---

<a id="g1"></a>

# G1 — Admin — enable Playground (OGX)

### What we want
Turn on Gen AI studio / Playground so **Add to playground** exists.

### Why
Without OGX + the dashboard flag, the Playground UI never appears.

### Success looks like
- Left nav shows **Gen AI studio → Playground** (or equivalent)
- Deployed chat assets can use **Add to playground**

### How

Playground needs **both**:

1. Dashboard feature **`genAiStudio: true`** on `OdhDashboardConfig`
2. DSC component **`ogx.managementState: Managed`**

#### Check

```bash
oc -n redhat-ods-applications get odhdashboardconfig odh-dashboard-config \
  -o jsonpath='genAiStudio={.spec.dashboardConfig.genAiStudio}{"\n"}'

oc get dsc default-dsc -o jsonpath='ogx={.spec.components.ogx.managementState} llama={.spec.components.llamastackoperator.managementState}{"\n"}'
```

#### Enable Gen AI studio (if needed)

```bash
oc -n redhat-ods-applications patch odhdashboardconfig odh-dashboard-config --type=merge \
  -p '{"spec":{"dashboardConfig":{"genAiStudio":true}}}'
```

Hard-refresh the OpenShift AI UI after patching.

### Critical: do not leave Llama Stack and OGX both Managed

On OpenShift AI **3.5**, **Llama Stack Operator is deprecated** and replaced by **OGX**.  
If **both** stay `Managed`, OGX **never provisions**:

| Spec | Bad (stuck) | Good |
|------|-------------|------|
| `llamastackoperator` | `Managed` | **`Removed`** |
| `ogx` | `Managed` | `Managed` |

**Symptom:** DSC `OGXReady=False`, message like `no matches for kind "OGX"` / `Some modules are not ready: ogx`. Operator log:

> `LlamaStackOperator is set to Managed; it has been deprecated, set it to Removed before enabling OGX`

**Fix (cluster admin — you run this):**

```bash
oc patch datasciencecluster default-dsc --type=merge -p '{
  "spec": {
    "components": {
      "llamastackoperator": { "managementState": "Removed" },
      "ogx": { "managementState": "Managed" }
    }
  }
}'
```

Wait until `OGXReady=True` / DSC Ready:

```bash
oc get dsc default-dsc -w
```

**UI path:** Operators → Red Hat OpenShift AI → DataScienceCluster → `default-dsc` → YAML: same states as above.

---

<a id="g1b"></a>

# G1b — New project + free the GPU

### What we want
Run Gen AI in its **own** OpenShift AI project, and stop GPU consumers from the predictive lab so the chat model can schedule.

### Why
- Pedagogy: two labs = two namespaces (no mix OVMS / vLLM in the same mental model)
- Sandbox reality: often **one GPU** — workbench + `muffin-chihuahua` predictor block vLLM

### Success looks like
- Project **`genai-hotline`** exists and opens in the dashboard
- Predictive workbench is **Stopped**
- Predictive deployment **`muffin-chihuahua`** shows status **Stopped** (Start available later — not deleted)
- No Running predictor / workbench pods holding the GPU in `chihuahua-vs-muffin-jan`

### How

#### 1) Create the Gen AI project (UI)

1. OpenShift AI → **Projects** → **Create project**
2. Name: **`genai-hotline`**
3. Create → open the project

**CLI equivalent (optional):**

```bash
export PROJECT=genai-hotline
oc apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${PROJECT}
  labels:
    opendatahub.io/dashboard: "true"
  annotations:
    opendatahub.io/display-name: "Gen AI Hotline"
EOF
```

#### 2) Free GPU in the predictive project (**Stop**, do not delete)

In project **`chihuahua-vs-muffin-jan`**:

1. **Workbenches** → **Stop** / pause **`chihuahua-muffin`** (not Running)
2. **Models → Deployments** (or project Deployments) → on **`muffin-chihuahua`** use **Stop**  
   - Status becomes **Stopped** (grey) with a **Start** action later — keep the deployment object  
   - **Do not Delete** unless you intentionally want to redo Step 5 of the predictive lab

![Predictive OVMS stopped](docs/screenshots/step-genai-muffin-serving-stopped.png)

**CLI check (read-only):**

```bash
oc -n chihuahua-vs-muffin-jan get pods
oc -n chihuahua-vs-muffin-jan get inferenceservice muffin-chihuahua
```

After a UI **Stop**, predictor pods should disappear / not Running; the InferenceService resource can remain. Prefer the dashboard **Stop** over `oc delete`.

Keep MinIO / MariaDB TrustyAI / pipeline server if you want — they usually don’t take the GPU.

#### 3) Verify

```bash
oc -n chihuahua-vs-muffin-jan get pods
oc -n genai-hotline get project 2>/dev/null || oc get ns genai-hotline
```

Then continue to [G2](#g2) **inside `genai-hotline`**.

---

<a id="g2"></a>

# G2 — Deploy a generative (chat) model

### What we want
Deploy a **small instruct** model from the catalog as a chat AI asset **in `genai-hotline`**.

### Why
Playground needs a Ready generative endpoint (usually **vLLM**), separate from any OVMS predictive deployment.

### Success looks like
- Deployment **Ready** in **`genai-hotline`**
- **Add to playground** available on the asset

### How

**UI path on OpenShift AI 3.5 (validated):** the model **Catalog** lives under **AI hub**, not always inside Project → Deployments.

1. Left nav → **AI hub** → **Models** → tab **Catalog**

![AI hub — Models Catalog](docs/screenshots/step-genai-aihub-catalog.png)

2. Search / filter for a **small instruct** chat model (lab freeze: `granite` + `tiny` / `FP8`)
3. Open the model card → **Deploy**
4. **Project:** **`genai-hotline`**
5. Wizard step **Model deployment** — use these validated values:

| Field | Lab value |
|-------|-----------|
| Model deployment name | `RedHatAI/granite-4.0-h-tiny-FP8-dynamic` (resource ≈ `redhataigranite-40-h-tiny-fp8`) |
| Deployment method | **Inference service** |
| Hardware profile | **`gpu-profile`** (1 GPU · ~12 GiB mem) — not `default-profile` CPU-only |
| Serving runtime template | **Automatic selection** → `vLLM NVIDIA GPU ServingRuntime for KServe` (ex. v0.24.0) |
| Replica count | `1` |

![Model deployment — gpu-profile + vLLM auto](docs/screenshots/step-genai-deploy-model-runtime.png)

6. **Next** → **Advanced settings**:

| Field | Lab value |
|-------|-----------|
| **Add as AI asset endpoint** | **Yes** (required for Playground) |
| **Use case** | `Chatbot` (or `chat`) |
| External route | **No** |
| Token authentication | **No** |
| Custom args / env | **No** |
| Deployment strategy | **Rolling update** |
| Model route timeout | **30** seconds |

![Advanced settings — AI asset Chatbot](docs/screenshots/step-genai-deploy-advanced.png)

7. **Review** — confirm the summary matches the freeze below → **Deploy model** → wait **Ready**

![Review — Gen AI deploy freeze](docs/screenshots/step-genai-deploy-review.png)

> If **Project → Deployments → Deploy model** only offers Predictive / empty catalog: use **AI hub → Models → Catalog** instead — that is the expected Gen AI entry point.

**Frozen example (sandbox, 1× L4) — full Review:**

| Field | Value |
|-------|--------|
| Project | **`genai-hotline`** |
| Model type | Generative AI model (LLM) |
| Location | `oci://registry.redhat.io/rhai/modelcar-granite-4-0-h-tiny-fp8-dynamic:3.0` |
| Catalog / name | `RedHatAI/granite-4.0-h-tiny-FP8-dynamic` |
| Hardware | **`gpu-profile`** |
| Format / runtime | **vLLM** · `vLLM NVIDIA GPU ServingRuntime for KServe` |
| Replicas | `1` |
| AI asset endpoint | **Yes** · use case **Chatbot** |
| External route / token | **No** / **No** |
| Strategy / timeout | Rolling update · 30s |
| Status | **Ready** (after deploy) |

If you still see `Insufficient nvidia.com/gpu`, go back to [G1b](#g1b) and confirm the predictive workbench + OVMS are stopped.

![AI asset endpoints — Ready (use case Chatbot)](docs/screenshots/step-genai-ai-asset-endpoints.png)

> **Add to playground** appears only under **Gen AI studio → AI asset endpoints** — used in [G5](#g5). It does **not** appear on **AI hub → Models → Deployments**.

If Gen AI / GPU is missing on the sandbox, stop and note it — do not force a huge model.

**Shared Hotline system prompt** (reuse in G3 / G4 / G5):

```text
You are “Hotline 0800-HELP”, an over-the-top IT support agent.
For every user message (a short problem description):
1) Invent a ticket ID like HELP-1042
2) Give a ridiculous but PG-rated root cause (2 sentences)
3) Give exactly 3 numbered next steps
4) End with: “Is there anything else I can misdiagnose today?”
Keep the whole answer under 120 words. No markdown tables.
```

**Shared endpoint freeze** (G3–G4 call this Service DNS):

| | Value |
|--|--------|
| Base URL | `http://redhataigranite-40-h-tiny-fp8-predictor.genai-hotline.svc.cluster.local:8080/v1` |
| Model id | `redhataigranite-40-h-tiny-fp8` |
| API shape | OpenAI `chat.completions` |

---

<a id="g3"></a>

# G3 — Open WebUI (same model)

### What we want
Host **Open WebUI** on the cluster and chat Hotline against the Ready vLLM endpoint.

### Why
First external UI: full OSS chat (models, system prompt, history) consuming RHOAI serving — no Gen AI studio yet.

### Success looks like
- Route opens Open WebUI
- Model `redhataigranite-40-h-tiny-fp8` answers with ticket + 3 steps + closing line
- This Deployment uses **no GPU** (GPU stays on the predictor)

### How

Requires [G2](#g2) Ready.

```bash
oc apply -f apps/open_webui/deploy.yaml

oc -n genai-hotline rollout status deploy/open-webui --timeout=300s
oc -n genai-hotline get route open-webui -o jsonpath='https://{.spec.host}{"\n"}'
```

**Expected output**

```text
deployment.apps/open-webui created
service/open-webui created
route.route.openshift.io/open-webui created
deployment "open-webui" successfully rolled out
https://open-webui-genai-hotline.apps....
```

Image pull from `ghcr.io` can take a few minutes the first time.

**In the UI:**

1. First visit → create **admin** account (lab only; `emptyDir` = lost on pod restart)
2. Confirm model **`redhataigranite-40-h-tiny-fp8`**
3. Paste the [shared Hotline system prompt](#g2) in Chat Controls / system prompt
4. Ask `My coffee machine prints PDF instead of coffee`

![Open WebUI — Hotline on same vLLM](docs/screenshots/step-genai-open-webui-hotline.png)

**Frozen:** Route `open-webui-genai-hotline…` · ticket-style reply (e.g. `HELP-847`) · same persona as later steps.

If the pod is **CrashLoop** / permission denied on `/app/backend/data`, the sandbox may need a looser SCC for this namespace (cluster-admin), e.g. default SA `anyuid` — only if logs show UID/filesystem issues.

---

<a id="g4"></a>

# G4 — Streamlit + Python S2I (Software Catalog builder)

### What we want
Deploy a **tiny custom** Streamlit Hotline app with the cluster **Python** S2I builder (Software Catalog) — same vLLM as G3.

### Why
Second external UI: *your* code + OpenShift build (`requirements.txt` + `.s2i/bin/run`). Shows catalog builder without a custom Template.

### Success looks like
- `hotline-chat` Route serves Streamlit
- Same Hotline ticket shape (persona hard-coded in `apps/hotline_chat/app.py`)
- No GPU on this Deployment

### How

Requires [G2](#g2) Ready. Builder = ImageStream `openshift/python` (e.g. **`3.12-ubi9`**).

### Cleanup previous attempt (if any)

```bash
oc -n genai-hotline delete all,bc,is,route,cm -l app=hotline-chat --ignore-not-found
oc -n genai-hotline delete deploy/hotline-chat svc/hotline-chat route/hotline-chat \
  bc/hotline-chat is/hotline-chat cm/hotline-chat-app --ignore-not-found
```

### UI path (Software Catalog)

1. Developer perspective → project **`genai-hotline`** → **+Add** → **Software Catalog**
2. Filter **Python** → select the **Python** builder (not Django sample)
3. Create application name `hotline-chat` (Git context `apps/hotline_chat` after push, or use CLI binary build below)
4. Topology → Deployment → **Environment**:

| Name | Value |
|------|--------|
| `PORT` | `8080` |
| `GRANITE_URL` | `http://redhataigranite-40-h-tiny-fp8-predictor.genai-hotline.svc.cluster.local:8080/v1` |
| `GRANITE_MODEL` | `redhataigranite-40-h-tiny-fp8` |
| `GRANITE_API_KEY` | `not-needed` |

5. Edge **Route** to service port **8080** if the wizard did not create one.

### CLI path (same builder)

From **repo root**:

```bash
NS=genai-hotline

oc -n "$NS" new-build --name=hotline-chat --binary --strategy=source \
  --image-stream=python:3.12-ubi9

oc -n "$NS" start-build hotline-chat --from-dir=apps/hotline_chat --follow

oc -n "$NS" new-app hotline-chat \
  -e PORT=8080 \
  -e GRANITE_URL=http://redhataigranite-40-h-tiny-fp8-predictor.genai-hotline.svc.cluster.local:8080/v1 \
  -e GRANITE_MODEL=redhataigranite-40-h-tiny-fp8 \
  -e GRANITE_API_KEY=not-needed

oc -n "$NS" create route edge hotline-chat --service=hotline-chat --port=8080 \
  --dry-run=client -o yaml | oc apply -f -

oc -n "$NS" rollout status deploy/hotline-chat --timeout=300s
oc -n "$NS" get route hotline-chat -o jsonpath='https://{.spec.host}{"\n"}'
```

**Expected output (shape)**

```text
buildconfig.build.openshift.io/hotline-chat created
...
Push successful
deployment "hotline-chat" successfully rolled out
https://hotline-chat-genai-hotline.apps....
```

Open the Route → ask `The elevator refuses Mondays`.

![Streamlit Hotline — S2I on same vLLM](docs/screenshots/step-genai-hotline-streamlit.png)

**Frozen:** catalog Python S2I · `PORT=8080` (if logs show `:8501`, set `PORT=8080` and rollout).

**Rebuild after code change:**

```bash
oc -n genai-hotline start-build hotline-chat --from-dir=apps/hotline_chat --follow
```

---

<a id="g5"></a>

# G5 — Playground — Hotline (simplest)

### What we want
Finish on the **built-in** OpenShift AI surface: Gen AI studio → Playground with the same Hotline prompt — no YAML, no Route for a chat UI.

### Why
Punchline after G3/G4: customers can also use the **integrated** product UI. Same model, zero custom frontend.

### Success looks like
- Playground chat with ticket-style Hotline reply
- Screenshot frozen for the room

### How

Requires [G1](#g1) (`genAiStudio: true`) and Ready AI asset from [G2](#g2).

1. Left nav → **Gen AI studio** → **AI asset endpoints**  
   - Do **not** use **AI hub → Models → Deployments**
2. Project → **`genai-hotline`**
3. Tab **Models** → **+ Add to playground**

![AI asset endpoints — Add to playground](docs/screenshots/step-genai-ai-asset-endpoints.png)

4. **Configure playground:** Type = **Inference**, Max tokens ≈ **512** (optional) → **Create**

![Configure playground — Inference](docs/screenshots/step-genai-configure-playground.png)

5. Wait for **Creating playground**

![Creating playground](docs/screenshots/step-genai-creating-playground.png)

6. **Gen AI studio → Playground** → project **`genai-hotline`**
7. **Settings** → **Prompt** → paste the [shared Hotline system prompt](#g2)  
   **Model** → Temperature ≈ **0.1**, Streaming **On**

![Playground ready — genai-hotline](docs/screenshots/step-genai-playground-ready.png)

8. Ask e.g. `The elevator refuses Mondays`

![Playground — Hotline reply](docs/screenshots/step-genai-playground-hotline.png)

**Frozen:** `HELP-1042` + absurd cause + 3 steps + closing line.

**Teaching point:** Open WebUI + Streamlit + Playground = three frontends, one RHOAI-served model.

Cleanup UIs (optional):

```bash
oc -n genai-hotline delete route,svc,deploy -l app=open-webui
oc -n genai-hotline delete route,svc,deploy,cm,bc,is -l app=hotline-chat --ignore-not-found
```

---

<a id="g6"></a>

# G6 — Out of scope (this Gen AI lab)

- Using the LLM to classify muffin/chihuahua **images** (that is OVMS in [README-PREDICTIVE.md](README-PREDICTIVE.md))
- RAG / AutoRAG / MCP (see official RHOAI 3.5 docs — pick a new use case later)
- Production auth / rate limits on the LLM route (out of scope for this lab)

---

## Link back

Hub: **[README.md](README.md)** · Predictive path: **[README-PREDICTIVE.md](README-PREDICTIVE.md)**
