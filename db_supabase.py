from __future__ import annotations
from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client

# -------------------- PORTAL (ANON) --------------------

def create_request_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    try:
        # evita retornar a linha inserida
        resp = sb.table("requests").insert(row, returning="minimal").execute()
    except TypeError:
        # compatibilidade com versões que não aceitam returning=
        resp = sb.table("requests").insert(row).execute()

    if getattr(resp, "error", None):
        raise RuntimeError(f"Insert requests falhou: {resp.error}")
    # se returning=minimal, resp.data pode vir None/[] e ainda assim estar OK

def create_vehicle_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    try:
        resp = sb.table("vehicles").insert(row, returning="minimal").execute()
    except TypeError:
        resp = sb.table("vehicles").insert(row).execute()

    if getattr(resp, "error", None):
        raise RuntimeError(f"Insert vehicles falhou: {resp.error}")

def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"RPC public_get_status falhou: {resp.error}")
    return resp.data or []

# -------------------- ADMIN (SERVICE ROLE) --------------------

def list_requests_admin(limit: int = 300) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").order("created_at", desc=True).limit(limit).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"List requests admin falhou: {resp.error}")
    return resp.data or []

def search_requests_admin(query: str, limit: int = 300) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return list_requests_admin(limit=limit)

    sb = get_admin_client()
    resp = (
        sb.table("requests")
        .select("*")
        .or_(f"cpf.ilike.%{q}%,nome.ilike.%{q}%,nome_padrao.ilike.%{q}%")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if getattr(resp, "error", None):
        raise RuntimeError(f"Search requests admin falhou: {resp.error}")
    return resp.data or []

def get_request_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").eq("request_id", request_id).limit(1).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"Get request admin falhou: {resp.error}")
    data = resp.data or []
    return data[0] if data else None

def get_vehicle_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("vehicles").select("*").eq("request_id", request_id).limit(1).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"Get vehicle admin falhou: {resp.error}")
    data = resp.data or []
    return data[0] if data else None

def list_events_admin(request_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    resp = (
        sb.table("events")
        .select("*")
        .eq("request_id", request_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if getattr(resp, "error", None):
        raise RuntimeError(f"List events admin falhou: {resp.error}")
    return resp.data or []

def update_request_admin(request_id: str, patch: Dict[str, Any]) -> None:
    sb = get_admin_client()
    resp = sb.table("requests").update(patch).eq("request_id", request_id).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"Update requests {request_id} falhou: {resp.error}")

def insert_event_admin(
    request_id: str,
    level: str,
    system: str,
    message: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    sb = get_admin_client()
    row = {"request_id": request_id, "level": level, "system": system, "message": message, "meta": meta or {}}
    resp = sb.table("events").insert(row).execute()
    if getattr(resp, "error", None):
        raise RuntimeError(f"Insert events falhou: {resp.error}")