"""Search Hotline runbooks from a directory (ConfigMap mount or local kb/)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# Prefer ConfigMap mount (KB_DIR). Fallback: files next to the app (local / image).
_DEFAULT_KB = Path(__file__).resolve().parent / "kb"
KB_DIR = Path(os.environ.get("KB_DIR", str(_DEFAULT_KB)))

_TOKEN = re.compile(r"[a-z0-9]+", re.I)


@dataclass(frozen=True)
class Doc:
    name: str
    text: str


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text) if len(t) > 1}


def resolve_kb_dir(kb_dir: Path | None = None) -> Path:
    return kb_dir if kb_dir is not None else KB_DIR


def load_docs(kb_dir: Path | None = None) -> list[Doc]:
    root = resolve_kb_dir(kb_dir)
    docs: list[Doc] = []
    if not root.is_dir():
        return docs
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".csv", ".md"}:
            continue
        docs.append(Doc(name=path.name, text=path.read_text(encoding="utf-8")))
    return docs


def score_query(query: str, doc: Doc) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    d = _tokens(doc.text)
    overlap = len(q & d)
    return overlap / max(len(q), 1)


def retrieve(
    query: str,
    docs: list[Doc] | None = None,
    *,
    top_k: int = 2,
    min_score: float = 0.22,
) -> list[tuple[Doc, float]]:
    """Return best runbooks for this issue, or [] when nothing is close enough."""
    corpus = docs if docs is not None else load_docs()
    # Prefer runbooks (01–04) over FAQ when scores tie
    ranked = sorted(
        ((doc, score_query(query, doc)) for doc in corpus),
        key=lambda item: (item[1], 0 if item[0].name.startswith("05") else 1),
        reverse=True,
    )
    hits = [(doc, sc) for doc, sc in ranked[:top_k] if sc >= min_score]
    return hits
