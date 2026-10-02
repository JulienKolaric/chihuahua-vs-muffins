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
| G2 | [Deploy a chat model](#g2) | |
| G3 | [Playground — Hotline 0800-HELP](#g3) | |
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

Demo theme for this lab: **Hotline 0800-HELP** — an absurd IT support bot that answers everyday “help, my thing is broken” tickets with over-the-top scripts (ticket id, root cause, next steps). Universal humour; works in any language you set in the system prompt (lab default: English or French — pick one for the room).

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

<a id="g2"></a>

# G2 — Deploy a generative (chat) model

### What we want
Deploy a **small instruct** model from the catalog as a chat AI asset.

### Why
Playground needs a Ready generative endpoint (usually **vLLM**), separate from any OVMS predictive deployment.

### Success looks like
- Deployment **Ready**
- **Add to playground** available on the asset

### How

**UI (typical RHOAI 3.5):**

1. Open a project (lab often reuses `chihuahua-vs-muffin-jan`, or create a dedicated Gen AI project)
2. **Deployments** → **Deploy model**
3. Choose **Generative AI model** (not Predictive / OVMS)
4. Pick a **small instruct** model from the **Model catalog** that fits your quota
5. Runtime: usually **vLLM** (cluster defaults)
6. Enable **Add as AI asset endpoint** · use case **chat**
7. Wait until **Ready**

**Frozen example (sandbox, 1× L4):**

| Field | Value |
|-------|--------|
| Catalog / model | `RedHatAI/granite-4.0-h-tiny-FP8-dynamic` |
| Deployment / asset id | `redhat-granite-4.0-h-tiny-fp8` |
| Use case | `chat` |
| Status | **Ready** |

Stop other GPU workbenches/deployments if you see `Insufficient nvidia.com/gpu`.

![AI asset Ready + Add to playground](docs/screenshots/step11-ai-asset-ready.png)

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

Requires [G1](#g1) (`ogx: Managed`, `llamastackoperator: Removed`, `genAiStudio: true`).

1. **AI asset endpoints** → **+ Add to playground** on your Ready chat model  
2. **Configure playground:** Type = **Inference**, Max tokens ≈ **512** → **Create**  
3. Wait for **Creating playground** to finish  

![Creating playground](docs/screenshots/step11-creating-playground.png)

4. Open **Gen AI studio → Playground**  
5. Select your project + chat model  
6. System prompt (copy-paste):

```text
You are “Hotline 0800-HELP”, an over-the-top IT support agent.
For every user message (a short problem description):
1) Invent a ticket ID like HELP-1042
2) Give a ridiculous but PG-rated root cause (2 sentences)
3) Give exactly 3 numbered next steps
4) End with: “Is there anything else I can misdiagnose today?”
Keep the whole answer under 120 words. No markdown tables.
```

7. Try user messages such as:
   - `My coffee machine prints PDF instead of coffee`
   - `Wi-Fi works only when I stand on one foot`
   - `The elevator refuses Mondays`

**Expected output (shape):** ticket id + absurd cause + 3 steps + closing line.

> Old muffin-court screenshots in `docs/screenshots/step11-playground-teacup.png` are from a previous theme — replace when you freeze this hotline demo.

---

<a id="g4"></a>

# G4 — Out of scope (this Gen AI lab)

- Using the LLM to classify muffin/chihuahua **images** (that is OVMS in [README-PREDICTIVE.md](README-PREDICTIVE.md))
- RAG / AutoRAG / MCP (see official docs + optional [People Policy lab](docs/PEOPLE_POLICY_AGENT_LAB.md))
- Production auth on the LLM route (see predictive [Step 12](README-PREDICTIVE.md#step-12) as a *pattern*, not copy-paste for Gen AI)

---

## Link back

Hub: **[README.md](README.md)** · Predictive path: **[README-PREDICTIVE.md](README-PREDICTIVE.md)**
