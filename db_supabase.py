from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client


# -------------------- HELPERS --------------------

def _raise_rpc_if_bad(data: Any, fn_name: str) -> None:
    """
    Espera payload do tipo:
      {"ok": true/false, "request_id": "...", "error": "..."}
    """
    if not isinstance(data, dict):
        raise RuntimeError(f"RPC {fn_name} resposta inesperada: {data}")

    if not data.get("ok"):
        raise RuntimeError(f"RPC {fn_name} retornou ok=false: {data}")


# -------------------- PORTAL (ANON) --------------------

def portal_submit_request(req: Dict[str, Any], veh: Optional[Dict[str, Any]] = None) -> str:
    """
    Submissão ATÔMICA via RPC (bypassa RLS corretamente).
    - req: dict com colunas de requests + payload_json
    - veh: dict com colunas de vehicles + payload_json (ou None)
    Retorna request_id.
    """
    sb = get_public_client()
    try:
        resp = sb.rpc("portal_submit_request", {"req": req, "veh": veh}).execute()
    except Exception as e:
        raise RuntimeError(f"Falha ao chamar RPC portal_submit_request: {e}") from e

    data = resp.data
    _raise_rpc_if_bad(data, "portal_submit_request")
    rid = data.get("request_id") or req.get("request_id")
    if not rid:
        raise RuntimeError(f"RPC portal_submit_request ok=true mas sem request_id: {data}")
    return str(rid)


def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    try:
        resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()
    except Exception as e:
        raise RuntimeError(f"Falha ao chamar RPC public_get_status: {e}") from e
    return resp.data or []


# -------------------- ADMIN (SERVICE ROLE) --------------------

def list_requests_admin(limit: int = 300) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    try:
        resp = sb.table("requests").select("*").order("created_at", desc=True).limit(limit).execute()
    except Exception as e:
        raise RuntimeError(f"List requests admin falhou: {e}") from e
    return resp.data or []


def search_requests_admin(query: str, limit: int = 300) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return list_requests_admin(limit=limit)

    sb = get_admin_client()
    try:
        resp = (
            sb.table("requests")
            .select("*")
            .or_(f"cpf.ilike.%{q}%,nome.ilike.%{q}%,nome_padrao.ilike.%{q}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        raise RuntimeError(f"Search requests admin falhou: {e}") from e
    return resp.data or []


def get_request_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    try:
        resp = sb.table("requests").select("*").eq("request_id", request_id).limit(1).execute()
    except Exception as e:
        raise RuntimeError(f"Get request admin falhou: {e}") from e
    data = resp.data or []
    return data[0] if data else None


def get_vehicle_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    try:
        resp = sb.table("vehicles").select("*").eq("request_id", request_id).limit(1).execute()
    except Exception as e:
        raise RuntimeError(f"Get vehicle admin falhou: {e}") from e
    data = resp.data or []
    return data[0] if data else None


def list_events_admin(request_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    try:
        resp = (
            sb.table("events")
            .select("*")
            .eq("request_id", request_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        raise RuntimeError(f"List events admin falhou: {e}") from e
    return resp.data or []


def update_request_admin(request_id: str, patch: Dict[str, Any]) -> None:
    sb = get_admin_client()
    try:
        sb.table("requests").update(patch).eq("request_id", request_id).execute()
    except Exception as e:
        raise RuntimeError(f"Update requests {request_id} falhou: {e}") from e


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
    try:
        sb.table("events").insert(row).execute()
    except Exception as e:
        raise RuntimeError(f"Insert events falhou: {e}") from e