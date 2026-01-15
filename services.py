from __future__ import annotations

import random
import time
from typing import Tuple

import db


def _simulate(system: str, request_id: str, seconds: float = 2.0) -> Tuple[bool, str]:
    db.insert_event(request_id, "INFO", f"Iniciando: {system}")
    for i in range(4):
        time.sleep(seconds / 4)
        db.insert_event(request_id, "DEBUG", f"{system}: progresso {int((i+1)*25)}%")
    if random.random() < 0.05:
        return False, "Falha simulada (protótipo)."
    return True, "OK"


def run_brasil_risk(request_id: str) -> None:
    r = db.get_request(request_id)
    if not r:
        return

    if int(r.get("cnh_received", 0)) == 0:
        db.update_request_fields(request_id, {
            "status_overall": "Bloqueado (CNH)",
            "status_brasil_risk": "Bloqueado (CNH)",
        })
        db.insert_event(request_id, "WARN", "Execução bloqueada: CNH não marcada como recebida.")
        return

    db.update_request_fields(request_id, {
        "status_overall": "Em processo",
        "status_brasil_risk": "Em processo",
    })

    ok, msg = _simulate("Brasil Risk", request_id, seconds=2.5)
    if not ok:
        db.update_request_fields(request_id, {
            "status_overall": "Erro",
            "status_brasil_risk": "Erro",
        })
        db.insert_event(request_id, "ERROR", f"Brasil Risk: {msg}")
        return

    # Regra do negócio: Brasil Risk autoriza o restante via APTO / NÃO APTO
    decision = "Apto" if random.random() < 0.80 else "Não Apto"
    db.update_request_fields(request_id, {
        "status_brasil_risk": decision,
        "status_overall": "Aguardando (próximos sistemas)" if decision == "Apto" else "Encerrado (Não Apto)",
    })
    if decision == "Apto":
        db.insert_event(request_id, "INFO", "Brasil Risk: courier APTO. Fluxo pode seguir para Rlog/Bringg.")
    else:
        db.insert_event(request_id, "WARN", "Brasil Risk: courier NÃO APTO. Fluxo deve ser encerrado e comunicado ao solicitante.")


def _guard_apto(request_id: str) -> bool:
    r = db.get_request(request_id)
    if not r:
        return False
    if r.get("status_brasil_risk") != "Apto":
        db.insert_event(request_id, "WARN", "Bloqueado: somente executar após Brasil Risk = Apto.")
        return False
    return True


def run_rlog_cielo(request_id: str) -> None:
    if not _guard_apto(request_id):
        return

    db.update_request_fields(request_id, {"status_rlog_cielo": "Em processo", "status_overall": "Em processo"})
    ok, msg = _simulate("Rlog Cielo", request_id, seconds=1.6)
    if ok:
        db.update_request_fields(request_id, {"status_rlog_cielo": "Concluído"})
        db.insert_event(request_id, "INFO", "Rlog Cielo: concluído.")
    else:
        db.update_request_fields(request_id, {"status_rlog_cielo": "Erro", "status_overall": "Erro"})
        db.insert_event(request_id, "ERROR", f"Rlog Cielo: {msg}")


def run_rlog_geral(request_id: str) -> None:
    if not _guard_apto(request_id):
        return

    db.update_request_fields(request_id, {"status_rlog_geral": "Em processo", "status_overall": "Em processo"})
    ok, msg = _simulate("Rlog Geral", request_id, seconds=1.6)
    if ok:
        db.update_request_fields(request_id, {"status_rlog_geral": "Concluído"})
        db.insert_event(request_id, "INFO", "Rlog Geral: concluído.")
    else:
        db.update_request_fields(request_id, {"status_rlog_geral": "Erro", "status_overall": "Erro"})
        db.insert_event(request_id, "ERROR", f"Rlog Geral: {msg}")


def run_bringg(request_id: str) -> None:
    if not _guard_apto(request_id):
        return

    db.update_request_fields(request_id, {"status_bringg": "Em processo", "status_overall": "Em processo"})
    ok, msg = _simulate("Bringg", request_id, seconds=1.6)
    if ok:
        db.update_request_fields(request_id, {"status_bringg": "Concluído"})
        r = db.get_request(request_id)
        if r and r.get("status_rlog_cielo") == "Concluído" and r.get("status_rlog_geral") == "Concluído":
            db.update_request_fields(request_id, {"status_overall": "Concluído"})
        else:
            db.update_request_fields(request_id, {"status_overall": "Aguardando (etapas pendentes)"})
        db.insert_event(request_id, "INFO", "Bringg: concluído.")
    else:
        db.update_request_fields(request_id, {"status_bringg": "Erro", "status_overall": "Erro"})
        db.insert_event(request_id, "ERROR", f"Bringg: {msg}")