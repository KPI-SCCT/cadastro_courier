from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client


def _err_to_str(err: Any) -> str:
    try:
        return str(err)
    except Exception:
        return repr(err)


def _raise_if_error(resp: Any, ctx: str) -> None:
    err = getattr(resp, "error", None)
    if err:
        raise RuntimeError(f"{ctx}: {_err_to_str(err)}")


# ==================== PORTAL (ANON) ====================

def portal_submit_request(req: Dict[str, Any], veh: Optional[Dict[str, Any]]) -> str:
    """
    Envia a solicitação via RPC (recomendado), para não depender de INSERT aberto no RLS.
    Requer a function no Supabase:
        public.portal_submit_request(req jsonb, veh jsonb) returns jsonb
    """
    sb = get_public_client()
    resp = sb.rpc("portal_submit_request", {"req": req, "veh": veh}).execute()
    _raise_if_error(resp, "RPC portal_submit_request falhou")

    data = resp.data

    # algumas libs retornam lista; normalizamos para dict
    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict):
        raise RuntimeError(f"Resposta inesperada do RPC portal_submit_request: {data!r}")

    if not data.get("ok"):
        raise RuntimeError(f"RPC portal_submit_request retornou ok=false: {data!r}")

    rid = data.get("request_id") or req.get("request_id")
    if not rid:
        raise RuntimeError(f"RPC portal_submit_request não retornou request_id: {data!r}")

    return str(rid)


def create_request_public(row: Dict[str, Any]) -> None:
    """
    Mantido apenas para compatibilidade/testes.
    Em produção, prefira portal_submit_request().
    """
    sb = get_public_client()
    try:
        resp = sb.table("requests").insert(row, returning="minimal").execute()
    except TypeError:
        resp = sb.table("requests").insert(row).execute()

    _raise_if_error(resp, "Insert requests (public) falhou")


def create_vehicle_public(row: Dict[str, Any]) -> None:
    """
    Mantido apenas para compatibilidade/testes.
    Em produção, prefira portal_submit_request().
    """
    sb = get_public_client()
    try:
        resp = sb.table("vehicles").insert(row, returning="minimal").execute()
    except TypeError:
        resp = sb.table("vehicles").insert(row).execute()

    _raise_if_error(resp, "Insert vehicles (public) falhou")


def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()
    _raise_if_error(resp, "RPC public_get_status falhou")
    return resp.data or []


# ==================== ADMIN (SERVICE ROLE) ====================

def list_requests_admin(limit: int = 300) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").order("created_at", desc=True).limit(limit).execute()
    _raise_if_error(resp, "List requests admin falhou")
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
    _raise_if_error(resp, "Search requests admin falhou")
    return resp.data or []


def get_request_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").eq("request_id", request_id).limit(1).execute()
    _raise_if_error(resp, "Get request admin falhou")
    data = resp.data or []
    return data[0] if data else None


def get_vehicle_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("vehicles").select("*").eq("request_id", request_id).limit(1).execute()
    _raise_if_error(resp, "Get vehicle admin falhou")
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
    _raise_if_error(resp, "List events admin falhou")
    return resp.data or []


def update_request_admin(request_id: str, patch: Dict[str, Any]) -> None:
    sb = get_admin_client()
    resp = sb.table("requests").update(patch).eq("request_id", request_id).execute()
    _raise_if_error(resp, f"Update requests {request_id} falhou")


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
    _raise_if_error(resp, "Insert events falhou")