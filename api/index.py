"""Vercel serverless entry point for AegisBot.

Re-exports the FastAPI app from main.py, ensuring the project root is in sys.path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is in sys.path so modules like config, db, etc. import correctly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app  # noqa: E402
