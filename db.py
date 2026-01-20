from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_db_path() -> Path:
    base = Path(__file__).resolve().parent
    return base / "data" / "app.db"


def get_db_path() -> Path:
    env = os.getenv("CCR_DB_PATH", "").strip()
    if env:
        return Path(env)
    return _default_db_path()


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def _table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]


def _ensure_column(con: sqlite3.Connection, table: str, col_name: str, col_def: str) -> None:
    cols = _table_columns(con, table)
    if col_name not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


def init_db() -> None:
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,

        request_type TEXT NOT NULL,      -- Cadastro | Descredenciamento
        role TEXT NOT NULL,              -- Motorista | Ajudante | Motorista/Ajudante
        has_vehicle INTEGER NOT NULL,    -- 0/1

        nome TEXT NOT NULL,
        cpf TEXT NOT NULL,
        nome_padrao TEXT,

        requester_name TEXT,
        requester_org TEXT,

        cnh_received INTEGER NOT NULL DEFAULT 0,  -- 0/1

        status_overall TEXT NOT NULL,
        status_brasil_risk TEXT NOT NULL,
        status_rlog_cielo TEXT NOT NULL,
        status_rlog_geral TEXT NOT NULL,
        status_bringg TEXT NOT NULL,

        payload_json TEXT NOT NULL DEFAULT '{}'
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        request_id TEXT PRIMARY KEY,
        vehicle_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(request_id) REFERENCES requests(request_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        ts TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        FOREIGN KEY(request_id) REFERENCES requests(request_id)
    );
    """)

    # Migrações simples (caso você rode versões futuras)
    _ensure_column(con, "requests", "payload_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(con, "requests", "status_rlog_geral", "TEXT NOT NULL DEFAULT 'Aguardando'")
    _ensure_column(con, "requests", "status_bringg", "TEXT NOT NULL DEFAULT 'Aguardando'")
    _ensure_column(con, "requests", "nome_padrao", "TEXT")

    con.commit()
    con.close()


def insert_event(request_id: str, level: str, message: str) -> None:
    con = connect()
    con.execute(
        "INSERT INTO events (request_id, ts, level, message) VALUES (?, ?, ?, ?)",
        (request_id, _utc_now_iso(), level.upper(), message),
    )
    con.commit()
    con.close()


def create_request(meta: Dict[str, Any], payload: Dict[str, Any], vehicle_payload: Optional[Dict[str, Any]] = None) -> str:
    con = connect()
    con.execute("""
        INSERT INTO requests (
            request_id, created_at,
            request_type, role, has_vehicle,
            nome, nome_padrao, cpf,
            requester_name, requester_org,
            cnh_received,
            status_overall, status_brasil_risk, status_rlog_cielo, status_rlog_geral, status_bringg,
            payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        meta["request_id"], meta["created_at"],
        meta["request_type"], meta["role"], int(meta["has_vehicle"]),
        meta["nome"], meta.get("nome_padrao"), meta["cpf"],
        meta.get("requester_name"), meta.get("requester_org"),
        int(meta.get("cnh_received", 0)),
        meta["status_overall"], meta["status_brasil_risk"], meta["status_rlog_cielo"], meta["status_rlog_geral"], meta["status_bringg"],
        json.dumps(payload, ensure_ascii=False),
    ))

    if vehicle_payload is not None:
        con.execute(
            "REPLACE INTO vehicles (request_id, vehicle_json) VALUES (?, ?)",
            (meta["request_id"], json.dumps(vehicle_payload, ensure_ascii=False))
        )

    con.commit()
    con.close()

    insert_event(meta["request_id"], "INFO", "Solicitação criada e enviada para a fila.")
    return meta["request_id"]


def update_request_fields(request_id: str, fields: Dict[str, Any]) -> None:
    if not fields:
        return
    keys = list(fields.keys())
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    values = [fields[k] for k in keys] + [request_id]
    con = connect()
    con.execute(f"UPDATE requests SET {set_clause} WHERE request_id = ?", values)
    con.commit()
    con.close()


def get_request(request_id: str) -> Optional[Dict[str, Any]]:
    con = connect()
    row = con.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_payload(request_id: str) -> Dict[str, Any]:
    r = get_request(request_id)
    if not r:
        return {}
    try:
        return json.loads(r.get("payload_json") or "{}")
    except Exception:
        return {}


def get_vehicle_payload(request_id: str) -> Dict[str, Any]:
    con = connect()
    row = con.execute("SELECT vehicle_json FROM vehicles WHERE request_id = ?", (request_id,)).fetchone()
    con.close()
    if not row:
        return {}
    try:
        return json.loads(row["vehicle_json"] or "{}")
    except Exception:
        return {}


def list_requests(order_desc: bool = True) -> List[Dict[str, Any]]:
    con = connect()
    order = "DESC" if order_desc else "ASC"
    rows = con.execute(f"SELECT * FROM requests ORDER BY created_at {order}").fetchall()
    con.close()
    return [dict(r) for r in rows]


def list_requests_by_cpf(cpf_digits: str) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("""
        SELECT * FROM requests
        WHERE cpf = ?
        ORDER BY created_at DESC
    """, (cpf_digits,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def search_requests(query: str) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return list_requests()
    like = f"%{q}%"
    con = connect()
    rows = con.execute("""
        SELECT * FROM requests
        WHERE cpf LIKE ? OR nome LIKE ? OR request_id LIKE ?
        ORDER BY created_at DESC
    """, (like, like, like)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def list_events(request_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("""
        SELECT ts, level, message
        FROM events
        WHERE request_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (request_id, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]