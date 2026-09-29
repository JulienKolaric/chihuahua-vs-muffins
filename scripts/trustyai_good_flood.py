#!/usr/bin/env python3
"""Flood the predictor (:9081 agent) with in-domain images so MeanShift rises toward 1.

Opposite of trustyai_ood_flood.py: send real muffins + chihuahuas so live traffic
looks like TRAINING again. Does not retrain the model — only reshapes live traffic.

Run from the workbench OR from your laptop via port-forward:

  # terminal A
  oc -n chihuahua-vs-muffin-jan port-forward \\
    $(oc -n chihuahua-vs-muffin-jan get pod -l serving.kserve.io/inferenceservice=muffin-chihuahua -o jsonpath='{.items[0].metadata.name}') \\
    9081:9081

  # terminal B
  export EP=http://127.0.0.1:9081
  export DATA_ROOT=/Users/jkolaric/lab-data/muffin-chihuahua-subset/test
  python3 scripts/trustyai_good_flood.py
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

EP = os.environ.get(
    "EP",
    "http://muffin-chihuahua-predictor.chihuahua-vs-muffin-jan.svc.cluster.local:9081",
)
MODEL = os.environ.get("MODEL", "muffin-chihuahua")
ROOT = Path(os.environ.get("DATA_ROOT", "/opt/app-root/src/data/muffin-chihuahua/test"))
D = np.dtype("f4")
PER_CLASS = int(os.environ.get("PER_CLASS", "4"))  # keep small — each image ~2MiB in TrustyAI
REPEATS = int(os.environ.get("REPEATS", "2"))


def to_chw(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB").resize((224, 224))
    arr = np.asarray(img).astype(D) / D.type(255.0)
    mean = np.array([0.485, 0.456, 0.406], dtype=D)
    std = np.array([0.229, 0.224, 0.225], dtype=D)
    arr = (arr - mean) / std
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(D)


def infer_chw(chw: np.ndarray, label: str) -> None:
    body = json.dumps(
        {
            "inputs": [
                {
                    "name": "input",
                    "shape": list(chw.shape),
                    "datatype": "FP32",
                    "data": chw.ravel().tolist(),
                }
            ]
        }
    ).encode()
    req = urllib.request.Request(
        f"{EP}/v2/models/{MODEL}/infer",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        st = urllib.request.urlopen(req, timeout=180).status
        print(label, st)
    except Exception as e:
        print(label, "FAIL", e)


def main() -> None:
    muffins = [p for p in (ROOT / "muffin").iterdir() if p.suffix.lower() == ".jpg"][:PER_CLASS]
    dogs = [p for p in (ROOT / "chihuahua").iterdir() if p.suffix.lower() == ".jpg"][:PER_CLASS]
    paths = muffins + dogs
    print(f"in-domain: {len(muffins)} muffins + {len(dogs)} chihuahuas, x{REPEATS}")
    for r in range(REPEATS):
        for p in paths:
            infer_chw(to_chw(p), f"ok:{p.parent.name}/{p.name}:r{r}")
    print("done — watch Observe → trustyai_meanshift (should rise toward 1)")


if __name__ == "__main__":
    main()
