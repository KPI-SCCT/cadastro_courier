from __future__ import annotations
import re
from datetime import datetime
from typing import Optional

_RE_DIGITS = re.compile(r"\D+")
_RE_MODAL_SIGLA = re.compile(r"\(([^)]+)\)")

LOWER_PARTS = {"da", "das", "de", "do", "dos", "e"}


def only_digits(value: str) -> str:
    return re.sub(_RE_DIGITS, "", value or "")

def validate_exact_digits(label: str, value: str, n: int) -> str:
    d = only_digits(value)
    if len(d) != n:
        raise ValueError(f"{label} deve conter exatamente {n} números. Você informou {len(d)}.")
    return d

def validate_date_ddmmyyyy(label: str, value: str) -> str:
    v = (value or "").strip()
    try:
        datetime.strptime(v, "%d/%m/%Y")
    except Exception:
        raise ValueError(f"{label} inválida. Use o formato dd/mm/aaaa.")
    return v

def validate_phone(label: str, value: str) -> str:
    d = only_digits(value)
    # BR: 10 ou 11 dígitos (com DDD)
    if len(d) not in (10, 11):
        raise ValueError(f"{label} inválido. Informe DDD + número (10 ou 11 dígitos).")
    return d

def normalize_name(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return s
    parts = [p for p in re.split(r"\s+", s) if p]
    out = []
    for p in parts:
        pl = p.lower()
        if pl in LOWER_PARTS:
            out.append(pl)
        else:
            out.append(pl[:1].upper() + pl[1:])
    return " ".join(out)

def make_nome_padrao(sigla_base_cielo: str, nome: str, modalidade: str) -> str:
    sigla = (sigla_base_cielo or "").strip().upper()
    n = (nome or "").strip().upper()
    mod = (modalidade or "").strip()
    m = _RE_MODAL_SIGLA.search(mod)
    mod_sigla = (m.group(1).strip().upper() if m else "—")
    if not sigla or not n:
        return ""
    return f"{sigla} - {n} - {mod_sigla}"
