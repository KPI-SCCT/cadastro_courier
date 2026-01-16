from __future__ import annotations
from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client


# -------------------- PORTAL (ANON) --------------------

def create_request_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    resp = sb.table("requests").insert(row).execute()
    if resp.data is None:
        raise RuntimeError(f"Insert requests falhou: {resp}")

def create_vehicle_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    resp = sb.table("vehicles").insert(row).execute()
    if resp.data is None:
        raise RuntimeError(f"Insert vehicles falhou: {resp}")

def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()
    return resp.data or []


# -------------------- ADMIN (SERVICE ROLE) --------------------

def list_requests_admin(limit: int = 300) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").order("created_at", desc=True).limit(limit).execute()
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
    return resp.data or []

def get_request_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").eq("request_id", request_id).limit(1).execute()
    data = resp.data or []
    return data[0] if data else None

def get_vehicle_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("vehicles").select("*").eq("request_id", request_id).limit(1).execute()
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
    return resp.data or []

def update_request_admin(request_id: str, patch: Dict[str, Any]) -> None:
    sb = get_admin_client()
    resp = sb.table("requests").update(patch).eq("request_id", request_id).execute()
    if resp.data is None:
        raise RuntimeError(f"Update requests {request_id} falhou: {resp}")

def insert_event_admin(
    request_id: str,
    level: str,
    system: str,
    message: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    sb = get_admin_client()
    row = {
        "request_id": request_id,
        "level": level,
        "system": system,
        "message": message,
        "meta": meta or {},
    }
    resp = sb.table("events").insert(row).execute()
    if resp.data is None:
        raise RuntimeError(f"Insert events falhou: {resp}")
