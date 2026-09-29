#!/usr/bin/env python3
"""Flood the predictor (:9081 agent) with OOD + synthetic junk so MeanShift drops.

TrustyAI captures every /infer via the KServe agent. Does NOT train or break the
model — it only pollutes live traffic for the drift demo.

Run from the workbench (cluster DNS) OR from your laptop via port-forward:

  # terminal A
  oc -n chihuahua-vs-muffin-jan port-forward \\
    $(oc -n chihuahua-vs-muffin-jan get pod -l serving.kserve.io/inferenceservice=muffin-chihuahua -o jsonpath='{.items[0].metadata.name}') \\
    9081:9081

  # terminal B (repo venv with numpy + Pillow)
  export EP=http://127.0.0.1:9081
  export OOD_DIR=/path/to/repo/ood
  python3 scripts/trustyai_ood_flood.py
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

EP = os.environ.get(
    "EP",
    "http://muffin-chihuahua-predictor.chihuahua-vs-muffin-jan.svc.cluster.local:9081",
)
MODEL = os.environ.get("MODEL", "muffin-chihuahua")
OOD = Path(os.environ.get("OOD_DIR", "/opt/app-root/src/ood"))
D = np.dtype("f4")
RNG = np.random.default_rng(42)
OOD_REPEATS = int(os.environ.get("OOD_REPEATS", "1"))  # keep small — each image ~2MiB in TrustyAI
SYNTHETIC_COUNT = int(os.environ.get("SYNTHETIC_COUNT", "4"))


def to_chw(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB").resize((224, 224))
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
    real = [p for p in OOD.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    print("real OOD:", len(real), f"x{OOD_REPEATS}")
    for _ in range(OOD_REPEATS):
        for p in real:
            infer_chw(to_chw(Image.open(p)), f"ood:{p.name}")

    print(f"synthetic junk x{SYNTHETIC_COUNT}")
    for i in range(SYNTHETIC_COUNT):
        kind = i % 4
        if kind == 0:
            arr = RNG.integers(0, 255, (224, 224, 3), dtype=np.uint8)
            img = Image.fromarray(arr, "RGB")
            tag = "noise"
        elif kind == 1:
            color = tuple(int(x) for x in RNG.integers(0, 255, 3))
            img = Image.new("RGB", (224, 224), color)
            tag = f"solid{color}"
        elif kind == 2:
            img = Image.new("RGB", (224, 224), (255, 255, 255))
            d = ImageDraw.Draw(img)
            for _ in range(40):
                xy = [tuple(int(x) for x in RNG.integers(0, 224, 2)) for _ in range(2)]
                d.line(xy, fill=tuple(int(x) for x in RNG.integers(0, 255, 3)), width=3)
            tag = "scribble"
        else:
            img = Image.new("RGB", (224, 224), (0, 0, 0))
            d = ImageDraw.Draw(img)
            d.text((20, 100), f"NOT A DOG {i}", fill=(0, 255, 0))
            tag = "text"
        infer_chw(to_chw(img), f"junk:{tag}:{i}")

    print("done — watch Observe → trustyai_meanshift (should drop)")


if __name__ == "__main__":
    main()
