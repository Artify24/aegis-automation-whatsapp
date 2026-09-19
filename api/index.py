"""Vercel serverless entry point for AegisBot.

Re-exports the FastAPI app from main.py, ensuring:
1. The project root is in sys.path.
2. The original requested path captured in __path__ query param is restored into ASGI scope
   so FastAPI matches /health, /webhook/whatsapp, /api/leads, etc. cleanly.
"""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app as fastapi_app  # noqa: E402


async def app(scope, receive, send):
    """ASGI wrapper restoring original requested path from Vercel rewrite parameter."""
    if scope.get("type") == "http":
        query_bytes = scope.get("query_string", b"")
        if b"__path__=" in query_bytes:
            try:
                parsed = urllib.parse.parse_qs(query_bytes.decode("utf-8", "ignore"))
                if "__path__" in parsed and parsed["__path__"]:
                    raw_target = parsed["__path__"][0]
                    # Normalize leading slashes
                    target_path = "/" + raw_target.lstrip("/")
                    scope["path"] = target_path
                    scope["raw_path"] = target_path.encode("utf-8")

                    # Remove __path__ from query string so endpoint params are untouched
                    remaining = {k: v for k, v in parsed.items() if k != "__path__"}
                    scope["query_string"] = urllib.parse.urlencode(remaining, doseq=True).encode("utf-8")
            except Exception:
                pass

    await fastapi_app(scope, receive, send)
