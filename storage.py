from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from settings import uploads_dir, ensure_runtime_dirs

TMP_DIR = uploads_dir()

def ensure_tmp_dir() -> None:
    ensure_runtime_dirs()

def save_temp_upload(file_name: str, data: bytes) -> str:
    ensure_tmp_dir()
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    p = TMP_DIR / f"{int(datetime.utcnow().timestamp())}_{safe_name}"
    p.write_bytes(data)
    return str(p)

def cleanup_old_uploads(days: int = 7) -> None:
    ensure_tmp_dir()
    cutoff = datetime.utcnow() - timedelta(days=days)
    for f in TMP_DIR.glob("*"):
        try:
            if datetime.utcfromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink(missing_ok=True)
        except Exception:
            pass
