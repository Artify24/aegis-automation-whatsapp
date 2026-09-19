"""Vercel serverless entry point for AegisBot."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app as fastapi_app  # noqa: E402


async def app(scope, receive, send):
    if scope.get("type") == "http":
        raw_headers = dict(scope.get("headers", []))
        h_str = {k.decode("latin1", "ignore").lower(): v.decode("latin1", "ignore") for k, v in raw_headers.items()}
        
        # Check all possible proxy headers from Vercel
        target_path = None
        for key in ("x-forwarded-uri", "x-matched-path", "x-invoke-path", "x-vercel-matched-path", "x-real-uri", "x-original-url"):
            if key in h_str:
                target_path = h_str[key].split("?")[0]
                break
        
        if target_path:
            scope["path"] = target_path
            scope["raw_path"] = target_path.encode("utf-8")
        elif scope.get("path") in ("/api/index.py", "/api", "/api/"):
            scope["path"] = "/"
            scope["raw_path"] = b"/"

        async def custom_send(message):
            if message.get("type") == "http.response.start":
                msg_headers = list(message.get("headers", []))
                # Inject debug header so we can inspect Vercel's headers
                msg_headers.append((b"x-debug-found-path", str(target_path).encode("utf-8")))
                msg_headers.append((b"x-debug-headers-keys", ",".join(h_str.keys()).encode("utf-8")))
                message["headers"] = msg_headers
            await send(message)

        await fastapi_app(scope, receive, custom_send)
    else:
        await fastapi_app(scope, receive, send)
