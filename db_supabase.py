from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase_client import get_public_client, get_admin_client


# --------------------------------------------------------------------------------------
# Compatibilidade / inicialização (para projetos que chamam init_db)
# --------------------------------------------------------------------------------------
def init_db() -> None:
    """
    Mantido por compatibilidade com versões antigas do Portal/Admin.
    Para Supabase, não há "init" real necessário.
    """
    return


def _err_text(err: Any) -> str:
    if err is None:
        return ""
    if isinstance(err, dict):
        return err.get("message") or str(err)
    msg = getattr(err, "message", None)
    return msg or str(err)


def _raise_if_error(resp: Any, context: str) -> None:
    err = getattr(resp, "error", None)
    if err:
        raise RuntimeError(f"{context}: {_err_text(err)}")


# --------------------------------------------------------------------------------------
# PORTAL (ANON)  -> recomenda-se usar RPC portal_submit_request
# --------------------------------------------------------------------------------------
def portal_submit_request(req: Dict[str, Any], veh: Optional[Dict[str, Any]] = None) -> str:
    """
    Envia uma solicitação de cadastro/descredenciamento via RPC (recomendado),
    para evitar problemas de RLS e para inserir requests + vehicles de forma atômica.
    """
    sb = get_public_client()
    resp = sb.rpc("portal_submit_request", {"req": req, "veh": veh}).execute()
    _raise_if_error(resp, "RPC portal_submit_request falhou")

    data = resp.data or {}
    # Esperado: {"ok": true, "request_id": "XXXXYYYY"} (ou equivalente)
    if isinstance(data, list) and data:
        # algumas versões podem devolver lista
        data = data[0]

    ok = bool(data.get("ok")) if isinstance(data, dict) else False
    if not ok:
        raise RuntimeError(f"Falha no submit (RPC): {data}")

    rid = data.get("request_id") if isinstance(data, dict) else None
    if not rid:
        # fallback: se a RPC não retornar request_id, pega do req
        rid = req.get("request_id")

    if not rid:
        raise RuntimeError(f"RPC retornou sucesso, mas sem request_id. Retorno: {data}")

    return str(rid)


def public_get_status(protocol: str, cpf_last4: str) -> List[Dict[str, Any]]:
    sb = get_public_client()
    resp = sb.rpc("public_get_status", {"protocol": protocol, "cpf_last4": cpf_last4}).execute()
    _raise_if_error(resp, "RPC public_get_status falhou")
    return resp.data or []


# Mantidos por compatibilidade (se algum código antigo chamar direto insert).
# Você pode remover depois que o Portal estiver 100% usando portal_submit_request().
def create_request_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    try:
        resp = sb.table("requests").insert(row, returning="minimal").execute()
    except TypeError:
        resp = sb.table("requests").insert(row).execute()
    _raise_if_error(resp, "Insert requests falhou")


def create_vehicle_public(row: Dict[str, Any]) -> None:
    sb = get_public_client()
    try:
        resp = sb.table("vehicles").insert(row, returning="minimal").execute()
    except TypeError:
        resp = sb.table("vehicles").insert(row).execute()
    _raise_if_error(resp, "Insert vehicles falhou")


# --------------------------------------------------------------------------------------
# ADMIN (SERVICE ROLE)
# --------------------------------------------------------------------------------------
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
    row = {"request_id": request_id, "level": level, "system": system, "message": message, "meta": meta or {}}
    resp = sb.table("events").insert(row).execute()
    _raise_if_error(resp, "Insert events falhou")