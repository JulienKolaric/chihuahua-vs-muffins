# Gen AI lab — OpenShift AI Playground (OGX)

**Separate** from the Chihuahua vs Muffin predictive lab ([README-PREDICTIVE.md](README-PREDICTIVE.md)).

| | Predictive lab (`README-PREDICTIVE.md`) | **This lab** |
|--|------------------------------------------|--------------|
| Goal | Train / serve / monitor an **image classifier** (OVMS) | Chat with a **generative** model (LLM) |
| Theme | Muffin ↔ chihuahua photos | **Independent** fun demo (no images required) |
| UI | Workbench, Deployments (predictive), TrustyAI… | **Gen AI studio → Playground** |

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
| G3 | [Playground — Hotline 0800-HELP](#g3) | ✅ |
| G4 | [Out of scope](#g4) | |

---

<a id="g0"></a>

# G0 — What we want to show

### What we want
Prove that OpenShift AI can host a **chat LLM** and that people can talk to it in **Playground** — without tying the story to image classification.

### Why
After the predictive lab, the audience already saw OVMS. Gen AI answers a different question: *can we deploy and use a generative model on the same platform?* Mixing muffin/chihuahua into the LLM prompt muddies that message.

### Success looks like
- Everyone can explain in one sentence: predictive = labels/scores · generative = text
- A short, funny Playground exchange that needs **no** photo and **no** OVMS

### How

Demo theme for this lab: **Hotline 0800-HELP** — an absurd IT support bot that answers everyday “help, my thing is broken” tickets with over-the-top scripts (ticket id, root cause, next steps). Lab default: **English** system prompt + English user questions.

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

![AI asset endpoints — Ready + Add to playground](docs/screenshots/step-genai-ai-asset-endpoints.png)

> **Where is Add to playground?** Only under **Gen AI studio → AI asset endpoints** (project `genai-hotline`). It does **not** appear on **AI hub → Models → Deployments**.

If Gen AI / GPU is missing on the sandbox, stop and note it — do not force a huge model.

---

<a id="g3"></a>

# G3 — Playground — Hotline 0800-HELP

### What we want
Chat in Playground with a funny **IT hotline** persona — no muffin, no photo, no OVMS.

### Why
This is the audience moment: generative text on OpenShift AI, instantly understandable.

### Success looks like
- A short ticket-style reply (ticket id + fake diagnosis + next step)
- Optional screenshot for the freeze

### How

Requires [G1](#g1) (`ogx: Managed`, `llamastackoperator: Removed`, `genAiStudio: true`) and a Ready AI asset from [G2](#g2).

1. Left nav → **Gen AI studio** → **AI asset endpoints**  
   - Do **not** use **AI hub → Models → Deployments** (no Playground column there)
2. Project dropdown → **`genai-hotline`**
3. Tab **Models** → confirm Status **Ready**, Use case **Chatbot** → **+ Add to playground**

![AI asset endpoints — genai-hotline](docs/screenshots/step-genai-ai-asset-endpoints.png)

4. **Configure playground** modal:
   - Model selected: `RedHatAI/granite-4.0-h-tiny-FP8-dynamic`
   - Type = **Inference**
   - Max tokens ≈ **512** (optional; leave blank for default)
   - → **Create**

![Configure playground — Inference](docs/screenshots/step-genai-configure-playground.png)

5. Wait for **Creating playground** to finish

![Creating playground](docs/screenshots/step-genai-creating-playground.png)

6. Open **Gen AI studio → Playground**  
7. Project → **`genai-hotline`** · model → `vllm-inference-1/RedHatAI/granite-4.0-h-tiny-FP8-dynamic`  
8. **Settings** (gear) → tab **Prompt** → paste the system prompt below → tab **Model** → Temperature ≈ **0.1**, Streaming **On**

![Playground ready — genai-hotline](docs/screenshots/step-genai-playground-ready.png)

9. System prompt (copy-paste into **Prompt**) — lab default is **English** (user questions in English):

```text
You are “Hotline 0800-HELP”, an over-the-top IT support agent.
For every user message (a short problem description):
1) Invent a ticket ID like HELP-1042
2) Give a ridiculous but PG-rated root cause (2 sentences)
3) Give exactly 3 numbered next steps
4) End with: “Is there anything else I can misdiagnose today?”
Keep the whole answer under 120 words. No markdown tables.
```

10. Try user messages such as:
   - `My coffee machine prints PDF instead of coffee`
   - `Wi-Fi works only when I stand on one foot`
   - `The elevator refuses Mondays`

**Expected output (shape):** ticket id + absurd cause + 3 steps + closing line.

![Playground — Hotline 0800-HELP reply](docs/screenshots/step-genai-playground-hotline.png)

**Frozen example:** user `The elevator refuses Mondays` → `HELP-1042` + ridiculous root cause + 3 steps + closing line (EN prompt).

---

<a id="g4"></a>

# G4 — Out of scope (this Gen AI lab)

- Using the LLM to classify muffin/chihuahua **images** (that is OVMS in [README-PREDICTIVE.md](README-PREDICTIVE.md))
- RAG / AutoRAG / MCP (see official RHOAI 3.5 docs — pick a new use case later)
- Production auth / rate limits on the LLM route (out of scope for this lab)

---

## Link back

Hub: **[README.md](README.md)** · Predictive path: **[README-PREDICTIVE.md](README-PREDICTIVE.md)**
