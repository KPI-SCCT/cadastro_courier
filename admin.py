from __future__ import annotations

import pandas as pd
import streamlit as st

from auth_admin import require_admin
import db_supabase as db
import services

from net_guard import require_supabase_admin_ok

st.set_page_config(page_title="Cadastro Courier - Admin", layout="wide")

require_admin()
require_supabase_admin_ok(db)


def status_badge(status: str) -> str:
    return status or "Aguardando"


def run_safe(fn, request_id: str, label: str) -> None:
    try:
        fn(request_id)
        st.success(f"{label}: concluído.")
    except Exception as e:
        st.error(f"{label}: falhou.")
        with st.expander("Detalhes técnicos"):
            st.code(str(e))


def admin_queue_view() -> None:
    st.title("Área Administrativa")
    st.caption("Fila, monitoramento e execução por etapa.")

    query = st.text_input("Buscar por CPF / Nome / Nome Padrão", value="")
    rows = db.search_requests_admin(query)

    if not rows:
        st.warning("Nenhuma solicitação encontrada.")
        return

    df = pd.DataFrame(rows)[[
        "request_type","cpf","nome","nome_padrao","role",
        "status_brasil_risk","status_rlog_cielo","status_rlog_geral","status_bringg",
        "created_at","status_overall","request_id","cnh_received"
    ]].rename(columns={
        "request_type":"Tipo",
        "cpf":"CPF",
        "nome":"Nome",
        "nome_padrao":"Nome Padrão",
        "role":"Função",
        "status_brasil_risk":"Brasil Risk",
        "status_rlog_cielo":"Rlog Cielo",
        "status_rlog_geral":"Rlog Geral",
        "status_bringg":"Bringg",
        "created_at":"Data (UTC)",
        "status_overall":"Status Final",
        "request_id":"Request ID",
        "cnh_received":"CNH recebida?",
    })

    df.insert(0, "Selecionar", False)

    st.subheader("Solicitações (selecione 1 ou várias linhas)")
    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Selecionar"),
        },
        disabled=[c for c in df.columns if c != "Selecionar"],
        key="queue_editor",
    )

    selected_ids = edited.loc[edited["Selecionar"] == True, "Request ID"].tolist()
    st.caption(f"Selecionados: {len(selected_ids)}")

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Executar Brasil Risk (Selecionados)", type="primary", use_container_width=True, disabled=(len(selected_ids) == 0)):
            for rid in selected_ids:
                run_safe(services.run_brasil_risk, rid, f"Brasil Risk [{rid}]")
            st.rerun()
    with c2:
        if st.button("Executar Rlog Cielo (Selecionados)", use_container_width=True, disabled=(len(selected_ids) == 0)):
            for rid in selected_ids:
                run_safe(services.run_rlog_cielo, rid, f"Rlog Cielo [{rid}]")
            st.rerun()
    with c3:
        if st.button("Executar Rlog Geral (Selecionados)", use_container_width=True, disabled=(len(selected_ids) == 0)):
            for rid in selected_ids:
                run_safe(services.run_rlog_geral, rid, f"Rlog Geral [{rid}]")
            st.rerun()
    with c4:
        if st.button("Executar Bringg (Selecionados)", use_container_width=True, disabled=(len(selected_ids) == 0)):
            for rid in selected_ids:
                run_safe(services.run_bringg, rid, f"Bringg [{rid}]")
            st.rerun()

    st.divider()

    st.subheader("Abrir detalhes de uma solicitação")
    chosen = st.selectbox("Request ID", edited["Request ID"].tolist())
    r = db.get_request_admin(chosen)

    if not r:
        st.error("Request não encontrado.")
        return

    vehicle = db.get_vehicle_admin(chosen)
    payload = r.get("payload_json") or {}
    vehicle_payload = (vehicle or {}).get("payload_json") if vehicle else None

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Resumo")
        st.write({
            "Request ID": r.get("request_id"),
            "Tipo": r.get("request_type"),
            "CPF": r.get("cpf"),
            "Nome": r.get("nome"),
            "Nome Padrão": r.get("nome_padrao"),
            "Função": r.get("role"),
            "Com veículo": bool(r.get("has_vehicle")),
            "Base": r.get("base_nome"),
            "UF Base": r.get("base_uf"),
            "Modalidade": r.get("modalidade"),
        })

        cnh = st.checkbox("CNH recebida (marcar manualmente)", value=bool(r.get("cnh_received")))
        if st.button("Salvar CNH recebida"):
            try:
                db.update_request_admin(chosen, {"cnh_received": bool(cnh)})
                db.insert_event_admin(chosen, "INFO", "ADMIN", f"CNH recebida marcada como: {cnh}")
                st.success("Atualizado.")
                st.rerun()
            except Exception as e:
                st.error("Falha ao salvar CNH recebida.")
                with st.expander("Detalhes técnicos"):
                    st.code(str(e))

        st.subheader("Detalhes do Formulário (payload_json)")
        st.json(payload)

        if vehicle_payload:
            st.subheader("Veículo (payload_json)")
            st.json(vehicle_payload)

    with right:
        st.subheader("Execução individual (Request selecionado)")

        a, b = st.columns(2)
        with a:
            if st.button("Start Brasil Risk", type="primary", use_container_width=True):
                run_safe(services.run_brasil_risk, chosen, "Brasil Risk")
                st.rerun()
            if st.button("Start Rlog Cielo", use_container_width=True):
                run_safe(services.run_rlog_cielo, chosen, "Rlog Cielo")
                st.rerun()
        with b:
            if st.button("Start Rlog Geral", use_container_width=True):
                run_safe(services.run_rlog_geral, chosen, "Rlog Geral")
                st.rerun()
            if st.button("Start Bringg", use_container_width=True):
                run_safe(services.run_bringg, chosen, "Bringg")
                st.rerun()

        st.divider()
        st.subheader("Status atual")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Brasil Risk", status_badge(r.get("status_brasil_risk")))
        m2.metric("Rlog Cielo", status_badge(r.get("status_rlog_cielo")))
        m3.metric("Rlog Geral", status_badge(r.get("status_rlog_geral")))
        m4.metric("Bringg", status_badge(r.get("status_bringg")))
        m5.metric("Final", status_badge(r.get("status_overall")))

        st.divider()
        st.subheader("Eventos (últimos 200)")
        events = db.list_events_admin(chosen, limit=200)
        if events:
            ev_df = pd.DataFrame(events)[["created_at","level","system","message","meta"]]
            st.dataframe(ev_df, use_container_width=True, hide_index=True)
        else:
            st.caption("Sem eventos ainda.")


def report_view() -> None:
    st.subheader("Relatório")
    rows = db.list_requests_admin(limit=5000)
    if not rows:
        st.info("Sem dados.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV", data=csv, file_name="relatorio_cadastro_courier.csv", mime="text/csv")


tabs = st.tabs(["Fila", "Relatório"])
with tabs[0]:
    admin_queue_view()
with tabs[1]:
    report_view()
