import re
from datetime import datetime

def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def normalize_name(name: str) -> str:
    name = (name or "").strip()
    return " ".join([w.capitalize() for w in name.split()])

def validate_exact_digits(field: str, value: str, n: int) -> str:
    value = only_digits(value)
    if len(value) != n:
        raise ValueError(f"{field} deve ter {n} dígitos. Recebido: {len(value)}")
    return value

def validate_phone(field: str, value: str) -> str:
    v = only_digits(value)
    if len(v) not in (10, 11):
        raise ValueError(f"{field} deve ter 10 ou 11 dígitos (com DDD).")
    return v

def validate_date_ddmmyyyy(field: str, value: str) -> str:
    try:
        datetime.strptime(value.strip(), "%d/%m/%Y")
        return value.strip()
    except Exception:
        raise ValueError(f"{field} deve estar no formato dd/mm/aaaa.")

def extract_sigla_modalidade(modalidade: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", (modalidade or "").strip())
    return (m.group(1).strip().upper() if m else "")

def sigla_cielo_prefix(sigla_cielo: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", (sigla_cielo or "").upper())
    if not tokens:
        return ""
    t = tokens[0]
    return t[:3] if len(t) >= 3 else t

def make_nome_padrao(sigla_cielo: str, nome: str, modalidade: str) -> str:
    prefix = sigla_cielo_prefix(sigla_cielo)
    nome_up = (nome or "").strip().upper()
    mod = extract_sigla_modalidade(modalidade)
    parts = [p for p in [prefix, nome_up, mod] if p]
    return " - ".join(parts)

def format_cpf_mask(digits: str) -> str:
    d = only_digits(digits)[:11]
    if not d:
        return ""
    # ###.###.###-##
    if len(d) <= 3:
        return d
    if len(d) <= 6:
        return f"{d[:3]}.{d[3:]}"
    if len(d) <= 9:
        return f"{d[:3]}.{d[3:6]}.{d[6:]}"
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

def format_phone_mask(digits: str) -> str:
    d = only_digits(digits)[:11]
    if not d:
        return ""
    # 10 dígitos: (##) ####-####
    # 11 dígitos: (##) # ####-####
    if len(d) <= 2:
        return f"({d}"
    ddd = d[:2]
    rest = d[2:]
    if len(d) <= 10:
        # (DD) XXXX-XXXX
        if len(rest) <= 4:
            return f"({ddd}) {rest}"
        if len(rest) <= 8:
            return f"({ddd}) {rest[:4]}-{rest[4:]}"
        return f"({ddd}) {rest[:4]}-{rest[4:8]}"
    else:
        # (DD) 9 XXXX-XXXX
        if len(rest) <= 1:
            return f"({ddd}) {rest}"
        if len(rest) <= 5:
            re
