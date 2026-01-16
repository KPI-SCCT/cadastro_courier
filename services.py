from __future__ import annotations
from typing import Dict
import db_supabase as db


def _normalize_status(s: str) -> str:
    return (s or "").strip().lower()

def _is_apto(status_brasil_risk: str) -> bool:
    s = _normalize_status(status_brasil_risk)
    return s in {"apto", "done", "concluido", "concluído", "ok"}

def _recompute_overall(r: Dict) -> str:
    br = r.get("status_brasil_risk", "")
    if _normalize_status(br) in {"nao apto", "não apto"}:
        return "Encerrado (Não Apto)"
    if any(_normalize_status(r.get(k, "")) in {"erro", "failed"} for k in
           ["status_brasil_risk", "status_rlog_cielo", "status_rlog_geral", "status_bringg"]):
        return "Erro"

    statuses = [
        r.get("status_brasil_risk", ""),
        r.get("status_rlog_cielo", ""),
        r.get("status_rlog_geral", ""),
        r.get("status_bringg", ""),
    ]
    if all(_normalize_status(s) in {"done", "concluido", "concluído"} for s in statuses):
        return "Concluído"
    return "Em Andamento"

def _mark_running(request_id: str, system: str) -> None:
    db.insert_event_admin(request_id, "INFO", system, "Início da execução")
    # opcional: setar status como "Em Execução"
    field = {
        "BRASIL_RISK": "status_brasil_risk",
        "RLOG_CIELO": "status_rlog_cielo",
        "RLOG_GERAL": "status_rlog_geral",
        "BRINGG": "status_bringg",
    }[system]
    db.update_request_admin(request_id, {field: "Em Execução", "status_overall": "Em Andamento"})

def _mark_done(request_id: str, system: str) -> None:
    field = {
        "BRASIL_RISK": "status_brasil_risk",
        "RLOG_CIELO": "status_rlog_cielo",
        "RLOG_GERAL": "status_rlog_geral",
        "BRINGG": "status_bringg",
    }[system]
    db.update_request_admin(request_id, {field: "Concluído"})
    db.insert_event_admin(request_id, "INFO", system, "Finalizado com sucesso")

    r = db.get_request_admin(request_id) or {}
    overall = _recompute_overall(r)
    db.update_request_admin(request_id, {"status_overall": overall})

def _mark_failed(request_id: str, system: str, err: Exception) -> None:
    field = {
        "BRASIL_RISK": "status_brasil_risk",
        "RLOG_CIELO": "status_rlog_cielo",
        "RLOG_GERAL": "status_rlog_geral",
        "BRINGG": "status_bringg",
    }[system]
    db.update_request_admin(request_id, {field: "Erro", "status_overall": "Erro"})
    db.insert_event_admin(request_id, "ERROR", system, "Falha na execução", {"error": str(err)})


def run_brasil_risk(request_id: str) -> None:
    system = "BRASIL_RISK"
    try:
        _mark_running(request_id, system)
        # TODO: Aqui entra Playwright + Captcha assistido
        _mark_done(request_id, system)
    except Exception as e:
        _mark_failed(request_id, system, e)
        raise

def run_rlog_cielo(request_id: str) -> None:
    system = "RLOG_CIELO"
    try:
        r = db.get_request_admin(request_id) or {}
        if not _is_apto(r.get("status_brasil_risk", "")):
            raise RuntimeError("Bloqueado: Brasil Risk ainda não está APTO/Concluído.")

        _mark_running(request_id, system)
        # TODO: Playwright do Rlog Cielo
        _mark_done(request_id, system)
    except Exception as e:
        _mark_failed(request_id, system, e)
        raise

def run_rlog_geral(request_id: str) -> None:
    system = "RLOG_GERAL"
    try:
        r = db.get_request_admin(request_id) or {}
        if not _is_apto(r.get("status_brasil_risk", "")):
            raise RuntimeError("Bloqueado: Brasil Risk ainda não está APTO/Concluído.")
        _mark_running(request_id, system)
        # TODO: Playwright do Rlog Geral
        _mark_done(request_id, system)
    except Exception as e:
        _mark_failed(request_id, system, e)
        raise

def run_bringg(request_id: str) -> None:
    system = "BRINGG"
    try:
        r = db.get_request_admin(request_id) or {}
        if not _is_apto(r.get("status_brasil_risk", "")):
            raise RuntimeError("Bloqueado: Brasil Risk ainda não está APTO/Concluído.")
        _mark_running(request_id, system)
        # TODO: Playwright do Bringg
        _mark_done(request_id, system)
    except Exception as e:
        _mark_failed(request_id, system, e)
        raise
