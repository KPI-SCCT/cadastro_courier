from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client


def _resp_error(resp: Any) -> Optional[Any]:
    # compatível com versões diferentes do supabase-py/postgrest
    return getattr(resp, "error", None)


def portal_submit_request(req: Dict[str, Any], veh: Optional[Dict[str, Any]]) -> str:
    """
    Envia uma solicitação via RPC (recomendado, pois evita dependência de RLS permissivo).
    Espera retorno do tipo:
      {"ok": true/false, "request_id": "...", "error": "..."}
    """
    sb = get_public_client()
    resp = sb.rpc("portal_submit_request", {"req": req, "veh": veh}).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"RPC portal_submit_request falhou: {err}")

    data = resp.data
    if isinstance(data, list) and data:
        data = data[0]

    if not isinstance(data, dict):
        raise RuntimeError(f"RPC portal_submit_request retornou formato inesperado: {resp.data}")

    if not data.get("ok"):
        raise RuntimeError(f"RPC portal_submit_request retornou ok=false: {data}")

    rid = data.get("request_id")
    if not rid:
        raise RuntimeError(f"RPC portal_submit_request não retornou request_id: {data}")

    return str(rid)


# -------------------- PORTAL (PUBLIC) --------------------

def create_request_public(row: Dict[str, Any]) -> str:
    """
    Wrapper de compatibilidade (caso algum trecho antigo ainda chame isso).
    Internamente usa o RPC para inserir apenas o request (sem veículo).
    """
    return portal_submit_request(row, None)


def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"RPC public_get_status falhou: {err}")

    return resp.data or []


# -------------------- ADMIN (SERVICE ROLE) --------------------

def list_requests_admin(limit: int = 300) -> List[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").order("created_at", desc=True).limit(limit).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"List requests admin falhou: {err}")

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

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"Search requests admin falhou: {err}")

    return resp.data or []


def get_request_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("requests").select("*").eq("request_id", request_id).limit(1).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"Get request admin falhou: {err}")

    data = resp.data or []
    return data[0] if data else None


def get_vehicle_admin(request_id: str) -> Optional[Dict[str, Any]]:
    sb = get_admin_client()
    resp = sb.table("vehicles").select("*").eq("request_id", request_id).limit(1).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"Get vehicle admin falhou: {err}")

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

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"List events admin falhou: {err}")

    return resp.data or []


def update_request_admin(request_id: str, patch: Dict[str, Any]) -> None:
    sb = get_admin_client()
    resp = sb.table("requests").update(patch).eq("request_id", request_id).execute()

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"Update requests {request_id} falhou: {err}")


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

    err = _resp_error(resp)
    if err:
        raise RuntimeError(f"Insert events falhou: {err}")