from __future__ import annotations

import os
import streamlit as st

def _is_ssl_error(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        "certificate_verify_failed" in m
        or "unable to get local issuer certificate" in m
        or "ssl:" in m and "certificate" in m
    )

def _ssl_help_message() -> str:
    return (
        "Este ambiente corporativo exige um CA bundle com o certificado raiz da empresa.\n\n"
        "1) Garanta que existe o arquivo:\n"
        r"   ...\Cadastro_Brasil_Risk\certs\ca-bundle.pem" "\n\n"
        "2) Defina a variável de ambiente SSL_CERT_FILE apontando para esse arquivo.\n\n"
        "CMD:\n"
        r"   set SSL_CERT_FILE=C:\...\certs\ca-bundle.pem" "\n"
        "PowerShell:\n"
        r"   $env:SSL_CERT_FILE='C:\...\certs\ca-bundle.pem'" "\n"
        "Persistente (Windows):\n"
        r"   setx SSL_CERT_FILE 'C:\...\certs\ca-bundle.pem'" "\n\n"
        "Depois feche e reabra o terminal e rode o app novamente."
    )

def require_supabase_portal_ok(db_module) -> None:
    """
    Valida que o Portal (ANON/public client) consegue falar com o Supabase via HTTPS.
    """
    try:
        # Não precisa existir; o objetivo é só abrir conexão com o Supabase
        db_module.public_get_status(protocol="PING", cpf_last4="0000")
        return
    except Exception as e:
        msg = str(e)
        if _is_ssl_error(msg):
            st.error("Falha de SSL ao conectar no Supabase (Portal).")
            st.info(_ssl_help_message())
            st.caption(f"SSL_CERT_FILE atual: {os.environ.get('SSL_CERT_FILE') or 'NÃO DEFINIDO'}")
            st.stop()
        raise

def require_supabase_admin_ok(db_module) -> None:
    """
    Valida que o Admin (SERVICE ROLE) consegue falar com o Supabase via HTTPS.
    """
    try:
        db_module.list_requests_admin(limit=1)
        return
    except Exception as e:
        msg = str(e)
        if _is_ssl_error(msg):
            st.error("Falha de SSL ao conectar no Supabase (Admin).")
            st.info(_ssl_help_message())
            st.caption(f"SSL_CERT_FILE atual: {os.environ.get('SSL_CERT_FILE') or 'NÃO DEFINIDO'}")
            st.stop()
        raise
