"""Vercel serverless entry point for AegisBot.

Re-exports the FastAPI app from main.py, ensuring:
1. The project root is in sys.path.
2. The original requested path from Vercel's rewrite proxy headers (e.g. x-forwarded-uri,
   x-matched-path, x-invoke-path) is restored into the ASGI scope so FastAPI matches all routes cleanly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is in sys.path so modules like config, db, etc. import correctly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app as fastapi_app  # noqa: E402


async def app(scope, receive, send):
    """ASGI wrapper restoring the original request URL path from Vercel proxy headers."""
    if scope.get("type") == "http":
        headers = dict(scope.get("headers", []))
        orig_path = None
        for h in (b"x-forwarded-uri", b"x-matched-path", b"x-invoke-path", b"x-original-uri"):
            if h in headers:
                raw = headers[h].decode("utf-8", "ignore")
                orig_path = raw.split("?")[0]
                break

        if orig_path:
            scope["path"] = orig_path
            scope["raw_path"] = orig_path.encode("utf-8")
        elif scope.get("path") in ("/api/index.py", "/api", "/api/"):
            scope["path"] = "/"
            scope["raw_path"] = b"/"

    await fastapi_app(scope, receive, send)
