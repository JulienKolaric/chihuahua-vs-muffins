# LAB — Chihuahua vs Muffin on OpenShift AI

**Version:** draft 0.5 — English, copy-paste friendly  
**Goal:** Test OpenShift AI end-to-end with a small image model  
**Example:** Is this photo a **chihuahua** or a **muffin**?  
**Audience:** Beginners on OpenShift AI / ML on Kubernetes  
**Time:** Half day (or full day if you train from scratch)

> **How to use this doc:** Follow the steps in order.  
> Copy each command block as-is, then change only the values marked `<LIKE_THIS>`.

---

## Success criteria

At the end you have:

1. An API URL that accepts an image and returns `chihuahua` or `muffin`
2. A short team note: what worked / what broke on the platform

We are **not** chasing 99% accuracy. We are testing **OpenShift AI**.

---

## Glossary (plain English)

| Name in the product | Meaning |
|---------------------|---------|
| **OpenShift** | The Kubernetes platform (cluster) |
| **OpenShift AI (RHOAI)** | The AI add-on on top of OpenShift |
| **Data Science Project** | Your shared team workspace |
| **Workbench** | Browser IDE (JupyterLab) with Python / PyTorch |
| **Data Connection** | Saved link from OpenShift AI → S3 storage |
| **S3 / MinIO** | Object storage for images and model files |
| **Training** | Teaching the model with labeled photos |
| **ONNX** | Portable model file format for serving |
| **Model Serving** | Running the model behind an HTTP API |
| **Endpoint / API** | The URL you call with an image |

---

## What you need before starting

- [ ] Access to an OpenShift cluster with **OpenShift AI** installed
- [ ] `oc` CLI logged in (`oc whoami` works)
- [ ] Rights to create projects / deploy apps (or an admin helps for MinIO)
- [ ] A browser for the OpenShift AI dashboard
- [ ] (Optional) GPU for faster training — CPU works with a small dataset

---

# PART A — Storage (MinIO as S3)

We install a small **MinIO** server on the cluster.  
It speaks the same API as Amazon S3. Perfect for labs.

## A1. Create a project for storage

```bash
oc new-project lab-minio
```

## A2. Create username / password secrets

```bash
# Change these passwords in a real environment
export MINIO_ROOT_USER="minio"
export MINIO_ROOT_PASSWORD="minio123"

oc -n lab-minio create secret generic minio-root \
  --from-literal=MINIO_ROOT_USER="$MINIO_ROOT_USER" \
  --from-literal=MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD"
```

## A3. Deploy MinIO (PVC + Deployment + Service)

```bash
oc -n lab-minio apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: quay.io/minio/minio:RELEASE.2024-12-18T13-15-44Z
          args:
            - server
            - /data
            - --console-address
            - :9001
          env:
            - name: MINIO_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: minio-root
                  key: MINIO_ROOT_USER
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-root
                  key: MINIO_ROOT_PASSWORD
          ports:
            - name: api
              containerPort: 9000
            - name: console
              containerPort: 9001
          volumeMounts:
            - name: data
              mountPath: /data
          readinessProbe:
            httpGet:
              path: /minio/health/ready
              port: 9000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /minio/health/live
              port: 9000
            initialDelaySeconds: 30
            periodSeconds: 20
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-data
---
apiVersion: v1
kind: Service
metadata:
  name: minio
spec:
  selector:
    app: minio
  ports:
    - name: api
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
EOF
```

Wait until MinIO is ready:

```bash
oc -n lab-minio rollout status deployment/minio
oc -n lab-minio get pods
```

## A4. Expose MinIO (API + web console)

```bash
# S3 API (port 9000)
oc -n lab-minio create route edge minio-api \
  --service=minio \
  --port=9000 \
  --insecure-policy=Redirect

# Web UI (port 9001)
oc -n lab-minio create route edge minio-console \
  --service=minio \
  --port=9001 \
  --insecure-policy=Redirect
```

Get the URLs:

```bash
echo "MinIO API:     https://$(oc -n lab-minio get route minio-api -o jsonpath='{.spec.host}')"
echo "MinIO Console: https://$(oc -n lab-minio get route minio-console -o jsonpath='{.spec.host}')"
```

Open the **Console** URL in a browser.  
Login with `minio` / `minio123` (or the values you set).

> **Note for beginners:**  
> - **API URL** = what apps / OpenShift AI use  
> - **Console URL** = what humans use in the browser

### Important: in-cluster URL vs public route

Inside the cluster (Workbench, Model Serving), prefer the **Service DNS** (no TLS issues):

```text
http://minio.lab-minio.svc.cluster.local:9000
```

From your laptop, use the **Route** HTTPS URL.

Save these values (you will reuse them):

```bash
export MINIO_ENDPOINT_INCLUSTER="http://minio.lab-minio.svc.cluster.local:9000"
export MINIO_ENDPOINT_EXTERNAL="https://$(oc -n lab-minio get route minio-api -o jsonpath='{.spec.host}')"
export AWS_ACCESS_KEY_ID="minio"
export AWS_SECRET_ACCESS_KEY="minio123"
export BUCKET="muffin-chihuahua"
```

## A5. Create the bucket (from your laptop)

### Option 1 — MinIO Client (`mc`) — recommended

Install `mc` (macOS example):

```bash
brew install minio/stable/mc
```

Or Linux:

```bash
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
```

Configure and create the bucket:

```bash
mc alias set lab "$MINIO_ENDPOINT_EXTERNAL" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" --api S3v4

# If TLS cert is self-signed and mc complains, add --insecure:
# mc alias set lab "$MINIO_ENDPOINT_EXTERNAL" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" --api S3v4 --insecure

mc mb lab/"$BUCKET"
mc ls lab/
```

### Option 2 — AWS CLI (also works with MinIO)

```bash
# macOS: brew install awscli
export AWS_ACCESS_KEY_ID="minio"
export AWS_SECRET_ACCESS_KEY="minio123"

aws --endpoint-url "$MINIO_ENDPOINT_EXTERNAL" s3 mb "s3://$BUCKET"
aws --endpoint-url "$MINIO_ENDPOINT_EXTERNAL" s3 ls
```

---

# PART B — Import the dataset

## B1. What the dataset is

We use the public Kaggle dataset:

**Muffin vs Chihuahua** — Samuel Cortinhas  
https://www.kaggle.com/datasets/samuelcortinhas/muffin-vs-chihuahua-image-classification  

- ~6,000 images  
- License: **CC0** (free to use for this lab)  
- Folders: `train/` and `test/`, each with `chihuahua/` and `muffin/`

Target layout in S3:

```text
s3://muffin-chihuahua/
├── train/
│   ├── chihuahua/
│   └── muffin/
└── test/
    ├── chihuahua/
    └── muffin/
```

## B2. Download from Kaggle (laptop)

1. Create a free Kaggle account  
2. Kaggle → Account → **Create New Token** → downloads `kaggle.json`  
3. Install and configure:

```bash
pip install kaggle

mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

4. Download and unzip:

```bash
mkdir -p ~/lab-data && cd ~/lab-data

kaggle datasets download -d samuelcortinhas/muffin-vs-chihuahua-image-classification
unzip -q muffin-vs-chihuahua-image-classification.zip -d muffin-chihuahua-raw

# Inspect
find muffin-chihuahua-raw -type d | head
```

> Folder names after unzip can vary slightly.  
> Make sure you end up with `train/chihuahua`, `train/muffin`, `test/chihuahua`, `test/muffin`.

Find the real root folder:

```bash
# Example: adjust if your unzip path is different
export DATA_ROOT=~/lab-data/muffin-chihuahua-raw
ls "$DATA_ROOT"
ls "$DATA_ROOT/train"
```

## B3. (Recommended) Build a smaller subset for the lab

Full dataset training can be slow on CPU. For a half-day lab, use a subset:

```bash
export FULL="$DATA_ROOT"
export SUBSET=~/lab-data/muffin-chihuahua-subset

mkdir -p "$SUBSET"/{train,test}/{chihuahua,muffin}

# Copy 500 train + 100 test images per class (adjust numbers if you want)
for split in train test; do
  for class in chihuahua muffin; do
    if [ "$split" = "train" ]; then N=500; else N=100; fi
    find "$FULL/$split/$class" -type f \
      | head -n "$N" \
      | while read -r f; do cp "$f" "$SUBSET/$split/$class/"; done
    echo "$split/$class: $(ls "$SUBSET/$split/$class" | wc -l) files"
  done
done
```

## B4. Upload to MinIO

```bash
# Upload the SUBSET (recommended)
mc mirror "$SUBSET" lab/"$BUCKET"/

# Or upload the FULL dataset:
# mc mirror "$DATA_ROOT" lab/"$BUCKET"/

# Verify
mc ls lab/"$BUCKET"/
mc ls lab/"$BUCKET"/train/
mc ls --summarize --recursive lab/"$BUCKET"/train/chihuahua/ | tail -5
```

With AWS CLI instead:

```bash
aws --endpoint-url "$MINIO_ENDPOINT_EXTERNAL" s3 sync "$SUBSET" "s3://$BUCKET/"
aws --endpoint-url "$MINIO_ENDPOINT_EXTERNAL" s3 ls "s3://$BUCKET/train/"
```

---

# PART C — OpenShift AI project + Data Connection

## C1. Create the Data Science Project

**UI path (easiest for beginners):**

1. Open the **OpenShift AI** dashboard  
2. **Data Science Projects** → **Create project**  
3. Name: `chihuahua-vs-muffin`  
4. Add your teammates (Edit access)

**Or CLI:**

```bash
# OpenShift AI projects are OpenShift namespaces with special labels.
# Prefer the UI if you are new. If your cluster uses the standard pattern:
oc new-project chihuahua-vs-muffin
```

> If the UI creates extra resources (permissions, operators hooks), **prefer the UI** for this step.

## C2. Create a Data Connection to MinIO

In the project `chihuahua-vs-muffin`:

1. **Connections** (or **Data connections**) → **Add connection** / **Create**
2. Type: **S3 compatible object storage**
3. Fill:

| Field | Value |
|-------|--------|
| Name | `minio-lab` |
| Access key | `minio` |
| Secret key | `minio123` |
| Endpoint | `http://minio.lab-minio.svc.cluster.local:9000` |
| Region | `us-east-1` (dummy value is fine for MinIO) |
| Bucket | `muffin-chihuahua` |

> Use the **in-cluster** endpoint from Workbenches and Model Serving.  
> Do **not** use the external HTTPS route here unless you know how to trust the certificate.

### Optional: create the connection as a Secret (advanced)

OpenShift AI Data Connections are Secrets with specific keys. Exact keys can vary by RHOAI version. Prefer the UI unless your cluster docs say otherwise.

## C3. Start a Workbench

1. In the project → **Workbenches** → **Create workbench**
2. Suggested settings:
   - Name: `pytorch-lab`
   - Image: **PyTorch** (latest available on your cluster)
   - Size: Medium (or larger)
   - Accelerator: GPU if available, else none
3. Attach connection: `minio-lab`
4. Create → wait until **Running** → **Open**

You should land in **JupyterLab**.

---

# PART D — From the Workbench: talk to S3

Open a notebook or terminal inside Jupyter.

## D1. Install helpers (once)

```bash
pip install boto3 pillow matplotlib
```

## D2. List files in the bucket (copy-paste)

Create a notebook cell:

```python
import boto3
import os

endpoint = os.environ.get(
    "AWS_S3_ENDPOINT",
    "http://minio.lab-minio.svc.cluster.local:9000",
)
access_key = os.environ.get("AWS_ACCESS_KEY_ID", "minio")
secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "minio123")
bucket = os.environ.get("AWS_S3_BUCKET", "muffin-chihuahua")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
)

# List first 20 objects
resp = s3.list_objects_v2(Bucket=bucket, MaxKeys=20)
for obj in resp.get("Contents", []):
    print(obj["Key"], obj["Size"])
```

> When you attach a Data Connection to a Workbench, OpenShift AI often injects env vars  
> like `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT`, `AWS_S3_BUCKET`.  
> Print them to learn your cluster’s exact names:

```python
import os
for k, v in sorted(os.environ.items()):
    if "AWS" in k or "S3" in k or "MINIO" in k:
        print(f"{k}={v}")
```

## D3. Download dataset from S3 into the Workbench

```python
import os
from pathlib import Path
import boto3

endpoint = os.environ.get("AWS_S3_ENDPOINT", "http://minio.lab-minio.svc.cluster.local:9000")
access_key = os.environ.get("AWS_ACCESS_KEY_ID", "minio")
secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "minio123")
bucket = os.environ.get("AWS_S3_BUCKET", "muffin-chihuahua")
local_root = Path("/opt/app-root/src/data/muffin-chihuahua")
local_root.mkdir(parents=True, exist_ok=True)

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
)

paginator = s3.get_paginator("list_objects_v2")
count = 0
for page in paginator.paginate(Bucket=bucket):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        if key.endswith("/"):
            continue
        dest = local_root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, key, str(dest))
        count += 1
        if count % 100 == 0:
            print(f"downloaded {count} files...")

print(f"Done. {count} files in {local_root}")
print("train/chihuahua:", len(list((local_root / "train/chihuahua").glob("*"))))
print("train/muffin:", len(list((local_root / "train/muffin").glob("*"))))
```

---

# PART E — Train a small model (PyTorch)

## E1. What we do (beginner view)

1. Start from a model that already knows general image features (**ResNet18**)
2. Replace the last layer so it only answers: **chihuahua** or **muffin**
3. Train on our photos
4. Export an **ONNX** file
5. Upload that file to S3 for Model Serving

## E2. Training notebook (copy-paste starter)

```python
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

DATA = Path("/opt/app-root/src/data/muffin-chihuahua")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", DEVICE)

train_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])
test_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

train_ds = datasets.ImageFolder(DATA / "train", transform=train_tf)
test_ds = datasets.ImageFolder(DATA / "test", transform=test_tf)
print("Classes:", train_ds.classes)  # expect ['chihuahua', 'muffin']

train_loader = DataLoader(train_ds, batch_size=32, shuffle=True, num_workers=2)
test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=2)

model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
for p in model.parameters():
    p.requires_grad = False
model.fc = nn.Linear(model.fc.in_features, 2)
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.fc.parameters(), lr=1e-3)

def evaluate():
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            pred = model(x).argmax(1)
            correct += (pred == y).sum().item()
            total += y.size(0)
    return correct / total

EPOCHS = 3  # increase later if you have time / GPU
for epoch in range(EPOCHS):
    model.train()
    running = 0.0
    t0 = time.time()
    for x, y in train_loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        optimizer.step()
        running += loss.item()
    acc = evaluate()
    print(f"epoch {epoch+1}/{EPOCHS}  loss={running/len(train_loader):.4f}  test_acc={acc:.3f}  time={time.time()-t0:.1f}s")

# Save PyTorch checkpoint (optional)
out_dir = Path("/opt/app-root/src/models")
out_dir.mkdir(parents=True, exist_ok=True)
torch.save({"model": model.state_dict(), "classes": train_ds.classes}, out_dir / "model.pt")
print("Saved", out_dir / "model.pt")
```

**Target for the lab:** test accuracy **> 0.90** is enough.

### Plan B (if training is too slow)

Before the lab, upload a ready `model.onnx` to:

```text
s3://muffin-chihuahua/models/model.onnx
```

Then skip training and jump to Part F.

## E3. Export ONNX and upload to S3

```python
import torch
import boto3
import os
from pathlib import Path

model.eval()
dummy = torch.randn(1, 3, 224, 224, device=DEVICE)
onnx_path = Path("/opt/app-root/src/models/model.onnx")

torch.onnx.export(
    model.cpu() if DEVICE == "cpu" else model,
    dummy.cpu() if DEVICE == "cpu" else dummy,
    str(onnx_path),
    input_names=["input"],
    output_names=["output"],
    dynamo=False,  # remove if unsupported on older torch
)
print("ONNX written:", onnx_path)

# Upload
endpoint = os.environ.get("AWS_S3_ENDPOINT", "http://minio.lab-minio.svc.cluster.local:9000")
s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "minio"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "minio123"),
)
bucket = os.environ.get("AWS_S3_BUCKET", "muffin-chihuahua")
key = "models/model.onnx"
s3.upload_file(str(onnx_path), bucket, key)
print(f"Uploaded s3://{bucket}/{key}")
```

---

# PART F — Deploy Model Serving

Exact UI labels change slightly between OpenShift AI versions. The idea is always the same.

## F1. UI steps

1. Open project `chihuahua-vs-muffin`
2. Go to **Models** / **Model serving**
3. Configure a serving runtime if needed → choose **OpenVINO Model Server** (or the ONNX-compatible runtime on your cluster)
4. Deploy model:
   - Name: `muffin-chihuahua`
   - Framework / format: **ONNX**
   - Location: Data Connection `minio-lab`
   - Path: `models/model.onnx`  
     (or the folder your runtime expects — some want a directory)
5. Wait until status is **Ready**
6. Copy the **Inference endpoint** URL

## F2. If your runtime wants a folder, not a single file

Some OpenVINO setups expect:

```text
s3://muffin-chihuahua/models/muffin-chihuahua/1/model.onnx
```

Create that layout:

```bash
mc cp lab/muffin-chihuahua/models/model.onnx \
  lab/muffin-chihuahua/models/muffin-chihuahua/1/model.onnx
mc ls --recursive lab/muffin-chihuahua/models/
```

Then set the model path to `models/muffin-chihuahua` (parent folder), depending on UI help text.

## F3. Smoke-test the endpoint from the Workbench

Your cluster’s request format may differ (KServe v1/v2, OpenVINO).  
Start by checking docs linked from the model details page, then adapt.

Minimal pattern (pseudo / often close to OpenVINO REST):

```python
import base64
import json
import requests
from pathlib import Path
from PIL import Image
import numpy as np

ENDPOINT = "<PASTE_INFERENCE_URL_HERE>"  # from the UI
TOKEN = "<OPTIONAL_BEARER_TOKEN>"        # if auth is enabled

img_path = Path("/opt/app-root/src/data/muffin-chihuahua/test/muffin")
sample = next(img_path.glob("*"))

# Many servers expect raw bytes or a preprocessed tensor.
# Check your runtime's example request in the OpenShift AI UI.
headers = {"Content-Type": "application/json"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"

with open(sample, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

# EXAMPLE payload — adjust to your runtime
payload = {
    "inputs": [
        {
            "name": "input",
            "shape": [1, 3, 224, 224],
            "datatype": "FP32",
            "data": [],  # fill with preprocessed tensor if required
        }
    ]
}

print("Sample image:", sample)
print("Next: adapt payload using the example from your Model Serving page.")
print("Endpoint:", ENDPOINT)
```

### Simple confidence rule (client-side)

After you get class scores:

```python
classes = ["chihuahua", "muffin"]
# probs = ... from model output (softmax)
# conf = float(max(probs))
# label = classes[int(probs.argmax())]
# if conf < 0.80:
#     print("uncertain / human review")
# else:
#     print(label, conf)
```

---

# PART G — Team checklist (fill during the lab)

| Step | OK / Fail / Partial | Notes |
|------|---------------------|-------|
| MinIO installed | | |
| Bucket created | | |
| Dataset uploaded | | |
| Data Science Project | | |
| Data Connection | | |
| Workbench starts | | |
| Can list S3 from notebook | | |
| Training runs | | |
| ONNX uploaded | | |
| Model Serving Ready | | |
| API returns a label | | |

---

# PART H — Timing (half day)

| Time | What |
|------|------|
| 0:00 | Intro + Part A (MinIO) |
| 0:40 | Part B (dataset upload) — better if done **before** the lab |
| 1:00 | Part C (project, connection, workbench) |
| 1:30 | Part D + E (download + train + ONNX) or Plan B |
| 2:45 | Part F (Model Serving) |
| 3:30 | Call the API + confidence rule |
| 3:50 | Fill Part G checklist together |

**Strong recommendation:** Do **Part A + Part B before the lab day**, so the live session starts at Part C.

---

# Troubleshooting (beginners)

| Problem | What to try |
|---------|-------------|
| `mc` TLS certificate error | Add `--insecure` to `mc` commands, or use in-cluster endpoint from a pod |
| Workbench cannot reach MinIO | Use `http://minio.lab-minio.svc.cluster.local:9000` (not the public route) |
| Empty bucket listing | Wrong access key / bucket name / endpoint |
| Kaggle download fails | Check `~/.kaggle/kaggle.json` permissions (`chmod 600`) |
| Training very slow | Use the subset; reduce epochs; use Plan B ONNX |
| Model never becomes Ready | Path to ONNX wrong; runtime expects a folder; check pod logs: `oc logs -n chihuahua-vs-muffin -l <serving-label>` |
| Prediction always wrong | Train and serve **must** use the same image size and normalization |
| PVC pending for MinIO | Cluster has no storage class / no capacity — ask your cluster admin |

Check MinIO logs:

```bash
oc -n lab-minio logs deploy/minio --tail=100
```

Check pods in the AI project:

```bash
oc -n chihuahua-vs-muffin get pods
oc -n chihuahua-vs-muffin get routes
```

---

# What we skip on purpose (later)

1. Automated pipelines (retrain when new images arrive)  
2. Model Registry versioning  
3. TrustyAI drift monitoring  
4. Service Mesh rate limits  

First make the simple path work: **storage → train → serve → call**.

---

# Pre-lab owner checklist

| Task | Owner | Done? |
|------|-------|-------|
| Install MinIO + create bucket | Ops | ☐ |
| Download + subset + upload dataset | Facilitator | ☐ |
| Dry-run: train → ONNX → serve → predict | Facilitator | ☐ |
| Optional Plan B `model.onnx` on S3 | Facilitator | ☐ |
| Confirm PyTorch workbench image exists | Ops | ☐ |
| Confirm Model Serving / OpenVINO available | Ops | ☐ |
| Invite all users to the project | Ops | ☐ |

---

# Useful links

- Dataset: https://www.kaggle.com/datasets/samuelcortinhas/muffin-vs-chihuahua-image-classification  
- Background paper: https://arxiv.org/abs/1801.09573  
- MinIO docs: https://min.io/docs/minio/linux/index.html  
- Example “DIY serving” (FastAPI) for comparison: https://github.com/fabianjkrueger/muffin_vs_chihuahua  

---

*Draft 0.5 — Copy-paste lab to test OpenShift AI with Chihuahua vs Muffin.*
