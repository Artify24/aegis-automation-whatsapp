"""AegisBot Automated Backup & Disaster Recovery Engine.

Creates full system snapshots (Supabase tables + RAG knowledge files) into timestamped
ZIP archives, and supports one-click restore and client migration.
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
import db
import rag

logger = logging.getLogger("aegisbot.backup")

BACKUP_DIR = Path(__file__).parent / "backups"
try:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    BACKUP_DIR = Path("/tmp/backups")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_system_backup() -> Dict[str, Any]:
    """Create a complete ZIP archive containing Supabase database dumps and knowledge documents."""
    global BACKUP_DIR
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        BACKUP_DIR = Path("/tmp/backups")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"aegisbot_backup_{timestamp_str}.zip"
    zip_path = BACKUP_DIR / zip_filename

    client = db._db()
    customers = client.table("customers").select("*").execute().data or []
    conversations = client.table("conversations").select("*").execute().data or []
    messages = client.table("messages").select("*").execute().data or []
    leads = client.table("leads").select("*").execute().data or []

    manifest = {
        "backup_version": "1.0",
        "business_name": config.BUSINESS_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "customers": len(customers),
            "conversations": len(conversations),
            "messages": len(messages),
            "leads": len(leads),
        },
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Manifest
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # 2. Database tables
        zf.writestr("db/customers.json", json.dumps(customers, indent=2))
        zf.writestr("db/conversations.json", json.dumps(conversations, indent=2))
        zf.writestr("db/messages.json", json.dumps(messages, indent=2))
        zf.writestr("db/leads.json", json.dumps(leads, indent=2))

        # 3. Knowledge directory files
        if rag.KNOWLEDGE_DIR.exists():
            for doc_file in rag.KNOWLEDGE_DIR.glob("*"):
                if doc_file.is_file():
                    zf.write(doc_file, arcname=f"knowledge/{doc_file.name}")

    file_size_kb = round(zip_path.stat().st_size / 1024, 1)
    logger.info("Backup created: %s (%s KB)", zip_filename, file_size_kb)

    return {
        "ok": True,
        "filename": zip_filename,
        "size_kb": file_size_kb,
        "created_at": manifest["created_at"],
        "manifest": manifest,
        "download_url": f"/api/backup/download/{zip_filename}",
    }


def list_backups() -> List[Dict[str, Any]]:
    """List all available system backups."""
    results = []
    seen = set()
    dirs = [BACKUP_DIR]
    tmp_backup = Path("/tmp/backups")
    if tmp_backup != BACKUP_DIR and tmp_backup.exists():
        dirs.append(tmp_backup)

    all_files = []
    for d in dirs:
        if d.exists():
            all_files.extend(d.glob("*.zip"))

    for f in sorted(all_files, key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.name not in seen:
            seen.add(f.name)
            results.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": f"/api/backup/download/{f.name}",
            })
    return results
