import hmac
import streamlit as st

def require_admin() -> None:
    if st.session_state.get("admin_ok"):
        return

    st.title("Área Administrativa")
    st.caption("Acesso restrito aos gestores.")

    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar", type="primary"):
        ok = hmac.compare_digest((pwd or ""), st.secrets.get("ADMIN_PASSWORD", ""))
        if ok:
            st.session_state["admin_ok"] = True
            st.rerun()
        else:
            st.error("Senha inválida.")

    st.stop()
