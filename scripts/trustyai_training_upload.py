#!/usr/bin/env python3
"""Build TRAINING payloads on the workbench (infer via :8888 = no TrustyAI logger spam)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

# :8888 = OVMS directly (skips agent logger — we only want tagged TRAINING uploads)
PRED = "http://muffin-chihuahua-predictor.chihuahua-vs-muffin-jan.svc.cluster.local:8888"
MODEL = "muffin-chihuahua"
ROOT = Path("/opt/app-root/src/data/muffin-chihuahua/test")
OUT = Path("/tmp/trustyai_training")
DTYPE = np.dtype("f4")
N_PER_CLASS = 2  # keep small — each JSON ~1–2 MiB


def preprocess(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB").resize((224, 224))
    arr = np.asarray(img).astype(DTYPE) / DTYPE.type(255.0)
    mean = np.array([0.485, 0.456, 0.406], dtype=DTYPE)
    std = np.array([0.229, 0.224, 0.225], dtype=DTYPE)
    arr = (arr - mean) / std
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(DTYPE)


def http_json(url: str, obj: dict, timeout: int = 180) -> dict:
    body = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [p for p in (ROOT / "muffin").iterdir() if p.suffix.lower() == ".jpg"][:N_PER_CLASS]
    paths += [p for p in (ROOT / "chihuahua").iterdir() if p.suffix.lower() == ".jpg"][:N_PER_CLASS]
    print("Building", len(paths), "payloads in", OUT)
    for i, p in enumerate(paths):
        chw = preprocess(p)
        request = {
            "inputs": [
                {
                    "name": "input",
                    "shape": list(chw.shape),
                    "datatype": "FP32",
                    "data": chw.ravel().tolist(),
                }
            ]
        }
        print(p.name, "infer…")
        response = http_json(f"{PRED}/v2/models/{MODEL}/infer", request)
        payload = {
            "model_name": MODEL,
            "data_tag": "TRAINING",
            "request": request,
            "response": {
                "model_name": response.get("model_name", MODEL),
                "model_version": response.get("model_version", "1"),
                "outputs": response["outputs"],
            },
        }
        out = OUT / f"train_{i}.json"
        out.write_text(json.dumps(payload))
        print(p.name, "wrote", out, "bytes", out.stat().st_size)
    print("done")


if __name__ == "__main__":
    main()
