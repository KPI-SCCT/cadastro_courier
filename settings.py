from __future__ import annotations

import os
import platform
from pathlib import Path

APP_NAME = "Cadastro_Brasil_Risk"

def _default_runtime_dir() -> Path:
    system = platform.system().lower()

    # Windows: prefer LOCALAPPDATA (not synced by OneDrive)
    if "windows" in system:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or str(Path.home())
        return Path(base) / APP_NAME

    # Linux/macOS: use home hidden dir
    return Path.home() / f".{APP_NAME.lower()}"

def runtime_dir() -> Path:
    """Root directory for runtime artifacts (db, uploads, playwright profile, logs).

    Override with env var:
      - CCR_RUNTIME_DIR
    """
    p = os.environ.get("CCR_RUNTIME_DIR")
    return Path(p).expanduser() if p else _default_runtime_dir()

def db_path() -> Path:
    """SQLite DB path. Override with:
      - CCR_DB_PATH
    """
    p = os.environ.get("CCR_DB_PATH")
    return Path(p).expanduser() if p else runtime_dir() / "cadastro_courier.db"

def pw_profile_dir() -> Path:
    """Playwright persistent profile dir. Override with:
      - CCR_PW_PROFILE_DIR
    """
    p = os.environ.get("CCR_PW_PROFILE_DIR")
    return Path(p).expanduser() if p else runtime_dir() / "pw_profile"

def uploads_dir() -> Path:
    """Temp uploads dir for CNH files. Override with:
      - CCR_UPLOADS_DIR
    """
    p = os.environ.get("CCR_UPLOADS_DIR")
    return Path(p).expanduser() if p else runtime_dir() / "tmp_uploads"

def logs_dir() -> Path:
    """Logs directory. Override with:
      - CCR_LOGS_DIR
    """
    p = os.environ.get("CCR_LOGS_DIR")
    return Path(p).expanduser() if p else runtime_dir() / "logs"

def ensure_runtime_dirs() -> None:
    runtime_dir().mkdir(parents=True, exist_ok=True)
    uploads_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
    pw_profile_dir().mkdir(parents=True, exist_ok=True)
