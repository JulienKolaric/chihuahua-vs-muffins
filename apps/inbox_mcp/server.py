"""Desk inbox MCP — fake mailbox tools (not Gmail/Outlook)."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

INBOX = Path(__file__).resolve().parent / "inbox"
PORT = int(os.environ.get("PORT", "8080"))

mcp = FastMCP(
    "desk-inbox",
    instructions="Lab mailbox. Call list_inbox then read_email. Do not invent senders.",
)


def _files() -> list[Path]:
    return sorted(p for p in INBOX.glob("*.txt"))


@mcp.tool
def list_inbox() -> str:
    """List messages in today's lab inbox (id, from, subject). Not real email."""
    lines: list[str] = []
    for path in _files():
        text = path.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        for raw in text.splitlines():
            if not raw.strip():
                break
            if ":" in raw:
                k, v = raw.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        lines.append(
            f"id={path.stem} | from={meta.get('from', '?')} | subject={meta.get('subject', '?')}"
        )
    if not lines:
        return "(empty inbox)"
    return "\n".join(lines)


@mcp.tool
def read_email(message_id: str) -> str:
    """Read one lab email by id from list_inbox (stem like 03_wifi_outage, with or without .txt)."""
    raw = Path(str(message_id).strip()).name
    stem = raw[:-4] if raw.lower().endswith(".txt") else raw
    path = INBOX / f"{stem}.txt"
    if not path.is_file():
        known = ", ".join(p.stem for p in _files()) or "(none)"
        return f"Unknown id {message_id!r}. Use an id without extra suffix. Known ids: {known}"
    return path.read_text(encoding="utf-8")


async def health(_request):
    return JSONResponse(
        {
            "status": "ok",
            "mcp": "/mcp",
            "hint": "Not a website. Playground authorizes against POST /mcp.",
        }
    )


# Serve Streamable HTTP at /mcp (no Mount("/mcp") — that 307s POST /mcp → http://…/mcp/).
_http_kw: dict = {
    "transport": "streamable-http",
    "path": "/mcp",
    "stateless_http": True,
}
try:
    mcp_asgi = mcp.http_app(**_http_kw, host_origin_protection=False)
except TypeError:
    mcp_asgi = mcp.http_app(**_http_kw)
app = Starlette(
    routes=[
        Route("/", health),
        Route("/healthz", health),
        Mount("/", app=mcp_asgi),
    ],
    lifespan=mcp_asgi.lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id", "Mcp-Session-Id"],
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
