from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import streamlit as st

import validators as v
import bases  # mantenha seu bases.py atual
import db_supabase as db
from net_guard import require_supabase_portal_ok


st.set_page_config(page_title="Cadastro Courier - Portal", layout="wide")

# valida conectividade/credenciais antes de renderizar o app
require_supabase_portal_ok(db)


UF_LIST = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
GENDER_LIST = ["Masculino", "Feminino", "Outros"]
FUNCAO_LIST = ["Motorista", "Ajudante"]
PERFIL_FIXO = "Agregado"

MODALIDADES = [
    "FedEx Moto Courier (FMC)",
    "FedEx Courier Motorista (FCM)",
    "FedEx Indoor PA (FIP)",
    "Motorista Fixo Variável (MFV)",
    "Terceiro Variável (TVL)",
    "Terceiro Fixo (TFO)",
]

VEICULO_TIPOS = ["3/4", "Carro", "Motocicleta", "Pick-up", "Utilitário", "Van"]
VEICULO_CATEGORIA = ["Particular", "Aluguel"]
PROPRIETARIO_TIPO = ["Física", "Jurídica"]
EQUIP_RASTREAMENTO = ["Não Possui"]

DESCRED_MOTIVOS = [
    "Saída do parceiro",
    "Troca de rota/base",
    "Solicitação do parceiro",
    "Desempenho/conduta",
    "Documento vencido",
    "Outros",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_request_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def status_badge(status: str) -> str:
    return status or "Aguardando"


def explain_hierarchy() -> None:
    st.info(
        "Hierarquia do fluxo:\n"
        "1) Brasil Risk é o gatekeeper: somente após Brasil Risk indicar **Apto** o cadastro deve seguir.\n"
        "2) Depois: Rlog Cielo → Rlog Geral → Bringg.\n"
        "3) Se Brasil Risk indicar **Não Apto**, o fluxo deve ser encerrado."
    )


def clear_draft() -> None:
    keys = list(st.session_state.keys())
    for k in keys:
        if k.startswith("draft_") or k.startswith("veh_") or k.startswith("ui_") or k in ("uf_end", "uf_cnh"):
            del st.session_state[k]


def portal_header() -> None:
    st.title("Cadastro Courier")
    st.caption("Brasil Risk / Rlog Cielo / Rlog Geral / Bringg")


def _submit_via_rpc(req_row: Dict[str, Any], veh_row: Optional[Dict[str, Any]]) -> str:
    """
    Ponto único de submit do Portal.
    """
    return db.portal_submit_request(req_row, veh_row)


def portal_acompanhar_view() -> None:
    st.subheader("Acompanhar Solicitação")
    explain_hierarchy()

    c1, c2 = st.columns(2)
    with c1:
        protocol = st.text_input("Request ID (Protocolo)", value="", placeholder="Ex.: 1A2B3C4D")
    with c2:
        last4 = st.text_input("Últimos 4 dígitos do CPF", value="", placeholder="Ex.: 8901", max_chars=4)

    if st.button("Consultar", type="primary"):
        try:
            if not protocol.strip():
                raise ValueError("Informe o Request ID.")
            if not last4.strip().isdigit() or len(last4.strip()) != 4:
                raise ValueError("Informe os últimos 4 dígitos do CPF (4 números).")

            rows = db.public_get_status(protocol.strip(), last4.strip())
            if not rows:
                st.warning("Nada encontrado. Verifique Request ID e os últimos 4 dígitos do CPF.")
                return

            r = rows[0]
            st.success("Solicitação encontrada.")
            st.write(f"**Nome:** {r.get('nome')}")
            st.write(f"**Nome Padrão:** {r.get('nome_padrao') or '—'}")
            st.caption(f"Data (UTC): {r.get('created_at')}")

            cols = st.columns(5)
            cols[0].metric("Brasil Risk", status_badge(r.get("status_brasil_risk")))
            cols[1].metric("Rlog Cielo", status_badge(r.get("status_rlog_cielo")))
            cols[2].metric("Rlog Geral", status_badge(r.get("status_rlog_geral")))
            cols[3].metric("Bringg", status_badge(r.get("status_bringg")))
            cols[4].metric("Final", status_badge(r.get("status_overall")))

        except Exception as e:
            st.error(str(e))


def portal_descredenciamento_form() -> None:
    st.subheader("Solicitação de Descredenciamento")

    c1, c2 = st.columns(2)
    with c1:
        cpf_in = st.text_input("CPF *", value="", placeholder="Somente números ou com máscara", key="descred_cpf")
    with c2:
        motivo = st.selectbox("Qual o motivo?", DESCRED_MOTIVOS, key="descred_motivo")

    detalhe = ""
    if motivo == "Outros":
        detalhe = st.text_area("Detalhar motivo (obrigatório quando 'Outros')", key="descred_detalhe")

    requester_name = st.text_input("Solicitante (nome)", value="", key="descred_reqname")
    requester_org = st.text_input("Empresa/Base/Parceiro", value="", key="descred_reqorg")

    if st.button("Solicitar Descredenciamento", type="primary", use_container_width=True):
        try:
            cpf = v.validate_exact_digits("CPF", cpf_in, 11)
            if motivo == "Outros" and not detalhe.strip():
                raise ValueError("Detalhe do motivo é obrigatório quando 'Outros'.")

            request_id = new_request_id()

            payload = {
                "tipo_solicitacao": "DESCREDENCIAMENTO",
                "cpf": cpf,
                "motivo": motivo,
                "detalhe": detalhe.strip(),
                "requester_name": requester_name.strip(),
                "requester_org": requester_org.strip(),
            }

            request_row = {
                "request_id": request_id,
                "created_at": utc_now_iso(),
                "request_type": "DESCREDENCIAMENTO",
                "role": "Motorista/Ajudante",
                "has_vehicle": False,

                "nome": "—",
                "nome_padrao": None,
                "cpf": cpf,

                "requester_name": requester_name.strip() or None,
                "requester_org": requester_org.strip() or None,

                "cnh_ack": True,
                "cnh_received": False,

                "status_overall": "Aguardando",
                "status_brasil_risk": "Aguardando",
                "status_rlog_cielo": "Aguardando",
                "status_rlog_geral": "Aguardando",
                "status_bringg": "Aguardando",

                "payload_json": payload,
            }

            _submit_via_rpc(request_row, None)

            st.success(f"Solicitação registrada com sucesso. Request ID: {request_id}")
            st.info("Use o Request ID + últimos 4 dígitos do CPF para acompanhar o status.")
        except Exception as e:
            st.error("Falha ao registrar descredenciamento.")
            with st.expander("Detalhes técnicos"):
                st.code(str(e))


def portal_home_select_role() -> None:
    st.subheader("Modalidades Courier")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Courier com veículo (Motorista)", type="primary", use_container_width=True):
            st.session_state["portal_role"] = "MOTORISTA"
            st.session_state["portal_has_vehicle"] = True
            st.session_state["portal_mode"] = "CADASTRO_STEP1"
            st.rerun()

    with col2:
        if st.button("Courier sem veículo (Ajudante)", use_container_width=True):
            st.session_state["portal_role"] = "AJUDANTE"
            st.session_state["portal_has_vehicle"] = False
            st.session_state["portal_mode"] = "CADASTRO_STEP1"
            st.rerun()

    st.divider()
    tabs = st.tabs(["Acompanhar Solicitação", "Solicitar Descredenciamento"])
    with tabs[0]:
        portal_acompanhar_view()
    with tabs[1]:
        portal_descredenciamento_form()


def build_payload_from_session(request_id: str) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "tipo_solicitacao": "CADASTRO",
        "role": st.session_state.get("portal_role"),
        "has_vehicle": bool(st.session_state.get("portal_has_vehicle")),

        "base_nome": st.session_state.get("draft_base_nome"),
        "base_uf": st.session_state.get("draft_base_uf"),
        "sigla_base_cielo": st.session_state.get("draft_sigla_cielo"),
        "sigla_base_geral": st.session_state.get("draft_sigla_geral"),
        "modalidade": st.session_state.get("draft_modalidade"),

        "dados_pessoais": {
            "nome": st.session_state.get("draft_nome"),
            "genero": st.session_state.get("draft_genero"),
            "data_nascimento": st.session_state.get("draft_nascimento"),
            "cpf": st.session_state.get("draft_cpf"),
            "rg": st.session_state.get("draft_rg"),
            "data_emissao": st.session_state.get("draft_data_emissao"),
            "nome_pai": st.session_state.get("draft_nome_pai") or "Não Informado",
            "nome_mae": st.session_state.get("draft_nome_mae"),
            "funcao": st.session_state.get("draft_funcao"),
            "perfil": PERFIL_FIXO,
        },
        "endereco": {
            "cep": st.session_state.get("draft_cep"),
            "uf": st.session_state.get("draft_uf_end"),
            "cidade": st.session_state.get("draft_cidade"),
            "bairro": st.session_state.get("draft_bairro"),
            "logradouro": st.session_state.get("draft_endereco"),
            "numero": st.session_state.get("draft_numero"),
            "complemento": st.session_state.get("draft_complemento"),
        },
        "contato": {
            "telefone": st.session_state.get("draft_telefone"),
            "celular": st.session_state.get("draft_celular"),
            "telefone_comercial": st.session_state.get("draft_tel_com"),
            "email": st.session_state.get("draft_email"),
        },
        "habilitacao": {
            "numero_registro": st.session_state.get("draft_registro"),
            "cnh_no": st.session_state.get("draft_cnh_no"),
            "categoria": st.session_state.get("draft_categoria"),
            "validade": st.session_state.get("draft_validade"),
            "uf_cnh": st.session_state.get("draft_uf_cnh"),
        },
        "centro_custos": {
            "empresa_centro_custo": "FEDEX",
            "responsavel_faturamento": "FEDEX BRASIL",
        }
    }


def build_request_row_from_session(request_id: str, cnh_ack: bool) -> Dict[str, Any]:
    payload = build_payload_from_session(request_id=request_id)

    return {
        "request_id": request_id,
        "created_at": utc_now_iso(),
        "request_type": "CADASTRO",
        "role": "Motorista" if st.session_state.get("portal_role") == "MOTORISTA" else "Ajudante",
        "has_vehicle": bool(st.session_state.get("portal_has_vehicle")),

        "nome": st.session_state.get("draft_nome"),
        "nome_padrao": st.session_state.get("draft_nome_padrao"),
        "cpf": st.session_state.get("draft_cpf"),

        "base_estado": st.session_state.get("draft_estado"),
        "base_nome": st.session_state.get("draft_base_nome"),
        "base_uf": st.session_state.get("draft_base_uf"),
        "sigla_cielo": st.session_state.get("draft_sigla_cielo"),
        "sigla_geral": st.session_state.get("draft_sigla_geral"),
        "modalidade": st.session_state.get("draft_modalidade"),

        "requester_name": None,
        "requester_org": None,

        "cnh_ack": bool(cnh_ack),
        "cnh_received": False,

        "status_overall": "Aguardando",
        "status_brasil_risk": "Aguardando",
        "status_rlog_cielo": "Aguardando",
        "status_rlog_geral": "Aguardando",
        "status_bringg": "Aguardando",

        "payload_json": payload,
    }


def cadastro_form_step1() -> None:
    st.subheader("Solicitação de Cadastro Courier - Etapa 1 (Dados do Courier)")
    st.markdown("### Base a qual o courier será associado:")

    if "ui_estado" not in st.session_state:
        st.session_state["ui_estado"] = st.session_state.get("draft_estado", "")
    if "ui_base_nome" not in st.session_state:
        st.session_state["ui_base_nome"] = st.session_state.get("draft_base_nome", "")
    if "ui_modalidade" not in st.session_state:
        st.session_state["ui_modalidade"] = st.session_state.get("draft_modalidade", MODALIDADES[0])

    b1, b2, b3, b4 = st.columns([3, 1, 2, 2])

    with b1:
        estados = [""] + list(bases.BASES_POR_ESTADO.keys())
        estado = st.selectbox("Estado *", estados, key="ui_estado")

    with b2:
        uf_base = bases.ESTADO_PARA_UF.get(estado, "")
        st.text_input("UF (auto)", value=uf_base, disabled=True)

    with b3:
        sigla_cielo = st.text_input(
            "Sigla da Base (Cielo) *",
            value=st.session_state.get("draft_sigla_cielo", ""),
            placeholder="Ex.: CJR"
        )

    with b4:
        sigla_geral = st.text_input(
            "Sigla da Base (Geral) *",
            value=st.session_state.get("draft_sigla_geral", ""),
            placeholder="Ex.: CJR"
        )

    b5, b6 = st.columns([4, 3])

    with b5:
        bases_list = bases.BASES_POR_ESTADO.get(estado, [])
        base_nome = st.selectbox("Nome da Base *", [""] + bases_list, key="ui_base_nome")

    with b6:
        modalidade = st.selectbox("Modalidade do Courier?", MODALIDADES, key="ui_modalidade")

    st.divider()
    st.markdown("### Dados Pessoais")
    p1, p2, p3 = st.columns(3)
    with p1:
        nome = st.text_input("Nome *", value=st.session_state.get("draft_nome",""))
    with p2:
        genero = st.selectbox("Gênero *", GENDER_LIST)
    with p3:
        nascimento = st.text_input("Data Nascimento * (dd/mm/aaaa)", value=st.session_state.get("draft_nascimento",""))

    p4, p5, p6 = st.columns(3)
    with p4:
        cpf_in = st.text_input("CPF *", value=st.session_state.get("draft_cpf",""), placeholder="###.###.###-##")
    with p5:
        rg = st.text_input("RG *", value=st.session_state.get("draft_rg",""))
    with p6:
        data_emissao = st.text_input("Data Emissão * (dd/mm/aaaa)", value=st.session_state.get("draft_data_emissao",""))

    p7, p8 = st.columns(2)
    with p7:
        nome_pai = st.text_input("Nome do Pai *", value=st.session_state.get("draft_nome_pai",""))
    with p8:
        nome_mae = st.text_input("Nome da Mãe *", value=st.session_state.get("draft_nome_mae",""))

    p9, p10, p11 = st.columns(3)
    with p9:
        funcao = st.selectbox("Função *", FUNCAO_LIST, index=0 if st.session_state.get("portal_role")=="MOTORISTA" else 1)
    with p10:
        st.text_input("Perfil *", value=PERFIL_FIXO, disabled=True)
    with p11:
        st.text_input("CNPJ (Empresa)", value="Não Preencher", disabled=True)

    st.divider()
    st.markdown("### Endereço")
    e1, e2, e3, e4 = st.columns(4)
    with e1:
        cep_in = st.text_input("CEP *", value=st.session_state.get("draft_cep",""))
    with e2:
        uf_end = st.selectbox("UF *", [""] + UF_LIST, key="uf_end")
    with e3:
        cidade = st.text_input("Cidade *", value=st.session_state.get("draft_cidade",""))
    with e4:
        bairro = st.text_input("Bairro *", value=st.session_state.get("draft_bairro",""))

    e5, e6, e7 = st.columns([3, 1, 2])
    with e5:
        endereco = st.text_input("Endereço *", value=st.session_state.get("draft_endereco",""))
    with e6:
        numero = st.text_input("Número *", value=st.session_state.get("draft_numero",""))
    with e7:
        complemento = st.text_input("Complemento", value=st.session_state.get("draft_complemento",""))

    st.divider()
    st.markdown("### Contato")
    c1, c2, c3 = st.columns(3)
    with c1:
        telefone = st.text_input("Telefone", value=st.session_state.get("draft_telefone",""))
    with c2:
        celular = st.text_input("Celular *", value=st.session_state.get("draft_celular",""), placeholder="(##)9 ####-####")
    with c3:
        tel_com = st.text_input("Telefone Comercial", value=st.session_state.get("draft_tel_com",""))

    email = st.text_input("E-mail", value=st.session_state.get("draft_email",""))

    st.divider()
    st.markdown("### Dados da Habilitação")
    h1, h2, h3 = st.columns(3)
    with h1:
        reg = st.text_input("Número do Registro *", value=st.session_state.get("draft_registro",""))
    with h2:
        cnh_no = st.text_input("CNH No. *", value=st.session_state.get("draft_cnh_no",""))
    with h3:
        categoria = st.text_input("Categoria *", value=st.session_state.get("draft_categoria",""))

    h4, h5 = st.columns(2)
    with h4:
        validade = st.text_input("Validade * (dd/mm/aaaa)", value=st.session_state.get("draft_validade",""))
    with h5:
        uf_cnh = st.selectbox("UF *", [""] + UF_LIST, key="uf_cnh")

    st.divider()
    st.markdown("### Centro de Custos")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.text_input("Empresa Centro de Custo *", value="FEDEX", disabled=True)
    with cc2:
        st.text_input("Responsável Faturamento *", value="FEDEX BRASIL", disabled=True)

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Voltar", use_container_width=True):
            st.session_state["portal_mode"] = "HOME"
            st.rerun()

    with colB:
        if st.button("Continuar", type="primary", use_container_width=True):
            try:
                estado = st.session_state.get("ui_estado", "")
                base_nome = st.session_state.get("ui_base_nome", "")
                modalidade = st.session_state.get("ui_modalidade", "")
                uf_base = bases.ESTADO_PARA_UF.get(estado, "")

                nome_n = v.normalize_name(nome)
                cpf = v.validate_exact_digits("CPF", cpf_in, 11)
                cep = v.validate_exact_digits("CEP", cep_in, 8)
                rg_d = v.only_digits(rg)
                if not rg_d:
                    raise ValueError("RG é obrigatório.")
                celular_d = v.validate_phone("Celular", celular)
                if telefone.strip():
                    v.validate_phone("Telefone", telefone)
                if tel_com.strip():
                    v.validate_phone("Telefone Comercial", tel_com)

                v.validate_date_ddmmyyyy("Data Nascimento", nascimento)
                v.validate_date_ddmmyyyy("Data Emissão", data_emissao)
                v.validate_date_ddmmyyyy("Validade", validade)

                if not nome_pai.strip():
                    raise ValueError("Nome do Pai é obrigatório (se desconhecido, use 'Não Informado').")
                if not nome_mae.strip():
                    raise ValueError("Nome da Mãe é obrigatório.")

                if not estado:
                    raise ValueError("Estado é obrigatório.")
                if not base_nome:
                    raise ValueError("Nome da Base é obrigatório.")
                if not uf_base:
                    raise ValueError("UF da Base não pôde ser inferida. Verifique o mapeamento.")
                if not sigla_cielo.strip() or not sigla_geral.strip():
                    raise ValueError("Siglas da Base (Cielo e Geral) são obrigatórias.")
                if not uf_end:
                    raise ValueError("UF do Endereço é obrigatório.")
                if not uf_cnh:
                    raise ValueError("UF da CNH é obrigatório.")
                if not endereco.strip() or not bairro.strip() or not cidade.strip() or not numero.strip():
                    raise ValueError("Endereço, Bairro, Cidade e Número são obrigatórios.")

                st.session_state.update({
                    "draft_base_nome": base_nome.strip(),
                    "draft_estado": estado,
                    "draft_base_uf": uf_base,
                    "draft_sigla_cielo": sigla_cielo.strip().upper(),
                    "draft_sigla_geral": sigla_geral.strip().upper(),
                    "draft_modalidade": modalidade,

                    "draft_nome": nome_n,
                    "draft_genero": genero,
                    "draft_nascimento": nascimento.strip(),
                    "draft_cpf": cpf,
                    "draft_rg": rg_d,
                    "draft_data_emissao": data_emissao.strip(),
                    "draft_nome_pai": v.normalize_name(nome_pai) if nome_pai.strip() else "Não Informado",
                    "draft_nome_mae": v.normalize_name(nome_mae),
                    "draft_funcao": funcao,

                    "draft_cep": cep,
                    "draft_uf_end": uf_end,
                    "draft_cidade": v.normalize_name(cidade),
                    "draft_bairro": v.normalize_name(bairro),
                    "draft_endereco": endereco.strip(),
                    "draft_numero": v.only_digits(numero) or numero.strip(),
                    "draft_complemento": complemento.strip(),

                    "draft_telefone": v.only_digits(telefone),
                    "draft_celular": celular_d,
                    "draft_tel_com": v.only_digits(tel_com),
                    "draft_email": email.strip(),

                    "draft_registro": v.only_digits(reg) or reg.strip(),
                    "draft_cnh_no": v.only_digits(cnh_no) or cnh_no.strip(),
                    "draft_categoria": categoria.strip(),
                    "draft_validade": validade.strip(),
                    "draft_uf_cnh": uf_cnh,
                })

                nome_padrao = v.make_nome_padrao(sigla_cielo.strip(), nome_n, modalidade)
                st.session_state["draft_nome_padrao"] = nome_padrao

                if st.session_state.get("portal_has_vehicle"):
                    st.session_state["portal_mode"] = "CADASTRO_STEP2"
                else:
                    st.session_state["portal_mode"] = "CADASTRO_REVIEW_NO_VEHICLE"

                st.rerun()

            except Exception as e:
                st.error(str(e))


def cadastro_form_step2_vehicle() -> None:
    st.subheader("Solicitação de Cadastro Courier - Etapa 2 (Veículo)")

    v1, v2, v3 = st.columns(3)
    with v1:
        placa = st.text_input("Placa *", value=st.session_state.get("veh_placa",""))
    with v2:
        tipo = st.selectbox("Tipo de Veículo *", VEICULO_TIPOS)
    with v3:
        chassi = st.text_input("Chassi *", value=st.session_state.get("veh_chassi",""))

    v4, v5, v6 = st.columns(3)
    with v4:
        ano = st.text_input("Ano de Fabricação *", value=st.session_state.get("veh_ano",""))
    with v5:
        marca = st.text_input("Marca *", value=st.session_state.get("veh_marca",""))
    with v6:
        modelo = st.text_input("Modelo *", value=st.session_state.get("veh_modelo",""))

    v7, v8, v9 = st.columns(3)
    with v7:
        cor = st.text_input("Cor *", value=st.session_state.get("veh_cor",""))
    with v8:
        renavam = st.text_input("Renavam *", value=st.session_state.get("veh_renavam",""))
    with v9:
        uf_veic = st.selectbox("UF Veículo *", [""] + UF_LIST)

    v10, v11 = st.columns(2)
    with v10:
        cidade_veic = st.text_input("Cidade *", value=st.session_state.get("veh_cidade_veic",""))
    with v11:
        categoria = st.selectbox("Categoria do Veículo *", VEICULO_CATEGORIA)

    if categoria == "Aluguel":
        rn1, rn2 = st.columns(2)
        with rn1:
            rntrc = st.text_input("RNTRC *", value=st.session_state.get("veh_rntrc",""))
        with rn2:
            validade_rntrc = st.text_input("Validade RNTRC * (dd/mm/aaaa)", value=st.session_state.get("veh_validade_rntrc",""))
    else:
        rntrc = ""
        validade_rntrc = ""

    st.divider()
    st.markdown("### Proprietário do Veículo")

    pt = st.radio("Tipo de Proprietário *", PROPRIETARIO_TIPO, horizontal=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        doc = st.text_input("CPF *" if pt == "Física" else "CNPJ *", value=st.session_state.get("veh_prop_doc",""))
    with p2:
        rg_prop = st.text_input("RG *" if pt == "Física" else "Inscrição Estadual *", value=st.session_state.get("veh_prop_rg",""))
    with p3:
        uf_prop = st.selectbox("UF Proprietário *", [""] + UF_LIST)

    p4, p5 = st.columns(2)
    with p4:
        nome_prop = st.text_input("Nome Proprietário *" if pt == "Física" else "Razão Social *", value=st.session_state.get("veh_prop_nome",""))
    with p5:
        nasc_prop = st.text_input("Data Nascimento * (dd/mm/aaaa)" if pt == "Física" else "Data Nascimento (N/A)", value=st.session_state.get("veh_prop_nasc",""), disabled=(pt!="Física"))

    p6, p7 = st.columns(2)
    with p6:
        mae_prop = st.text_input("Nome da Mãe *" if pt == "Física" else "Nome da Mãe (N/A)", value=st.session_state.get("veh_prop_mae",""), disabled=(pt!="Física"))
    with p7:
        cel_prop = st.text_input("Celular do Proprietário *" if pt == "Física" else "Celular do Proprietário (opcional)", value=st.session_state.get("veh_prop_cel",""))

    st.divider()
    st.markdown("### Rastreamento")
    st.selectbox("Equip. Rastreamento *", EQUIP_RASTREAMENTO)

    st.divider()
    st.warning("CNH não é enviada por este portal. Você deve encaminhar a CNH ao gestor por canal corporativo.")
    cnh_ack = st.checkbox("Estou ciente e vou enviar a CNH ao gestor (obrigatório para solicitar).")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Voltar", use_container_width=True):
            st.session_state["portal_mode"] = "CADASTRO_STEP1"
            st.rerun()

    with colB:
        if st.button("Solicitar Cadastro", type="primary", use_container_width=True):
            try:
                if not cnh_ack:
                    raise ValueError("Confirme o envio da CNH ao gestor para continuar.")

                if not placa.strip():
                    raise ValueError("Placa é obrigatória.")
                if not chassi.strip():
                    raise ValueError("Chassi é obrigatório.")
                if not ano.strip() or not v.only_digits(ano):
                    raise ValueError("Ano de Fabricação é obrigatório (somente números).")
                if not marca.strip() or not modelo.strip() or not cor.strip():
                    raise ValueError("Marca/Modelo/Cor são obrigatórios.")
                if not v.only_digits(renavam):
                    raise ValueError("Renavam é obrigatório (somente números).")
                if not uf_veic:
                    raise ValueError("UF do Veículo é obrigatório.")
                if not cidade_veic.strip():
                    raise ValueError("Cidade do Veículo é obrigatória.")

                if categoria == "Aluguel":
                    if not rntrc.strip():
                        raise ValueError("RNTRC é obrigatório para veículo Aluguel.")
                    v.validate_date_ddmmyyyy("Validade RNTRC", validade_rntrc)

                if pt == "Física":
                    v.validate_exact_digits("CPF do Proprietário", doc, 11)
                    if not v.only_digits(rg_prop):
                        raise ValueError("RG do Proprietário é obrigatório.")
                    if not uf_prop:
                        raise ValueError("UF do Proprietário é obrigatório.")
                    if not nome_prop.strip():
                        raise ValueError("Nome do Proprietário é obrigatório.")
                    v.validate_date_ddmmyyyy("Data Nascimento do Proprietário", nasc_prop)
                    if not mae_prop.strip():
                        raise ValueError("Nome da Mãe do Proprietário é obrigatório.")
                    v.validate_phone("Celular do Proprietário", cel_prop)
                else:
                    v.validate_exact_digits("CNPJ do Proprietário", doc, 14)
                    if not v.only_digits(rg_prop):
                        raise ValueError("Inscrição Estadual é obrigatória (somente números).")
                    if not uf_prop:
                        raise ValueError("UF do Proprietário é obrigatório.")
                    if not nome_prop.strip():
                        raise ValueError("Razão Social é obrigatória.")

                request_id = new_request_id()

                request_row = build_request_row_from_session(request_id=request_id, cnh_ack=cnh_ack)

                vehicle_payload = {
                    "placa": placa.strip().upper(),
                    "tipo_veiculo": tipo,
                    "chassi": chassi.strip(),
                    "ano_fabricacao": v.only_digits(ano),
                    "marca": marca.strip(),
                    "modelo": modelo.strip(),
                    "cor": cor.strip(),
                    "renavam": v.only_digits(renavam),
                    "uf_veiculo": uf_veic,
                    "cidade_veiculo": v.normalize_name(cidade_veic),
                    "categoria_veiculo": categoria,
                    "rntrc": rntrc.strip() if categoria == "Aluguel" else "",
                    "validade_rntrc": validade_rntrc.strip() if categoria == "Aluguel" else "",
                    "proprietario_tipo": pt,
                    "proprietario_doc": v.only_digits(doc),
                    "proprietario_rg_ie": v.only_digits(rg_prop),
                    "proprietario_uf": uf_prop,
                    "proprietario_nome": v.normalize_name(nome_prop) if pt == "Física" else nome_prop.strip(),
                    "proprietario_nascimento": nasc_prop.strip() if pt == "Física" else "",
                    "proprietario_mae": v.normalize_name(mae_prop) if pt == "Física" else "",
                    "proprietario_celular": v.only_digits(cel_prop),
                }

                vehicle_row = {
                    "request_id": request_id,
                    "placa": placa.strip().upper(),
                    "tipo_veiculo": tipo,
                    "chassi": chassi.strip(),
                    "ano_fabricacao": int(v.only_digits(ano)),
                    "marca": marca.strip(),
                    "modelo": modelo.strip(),
                    "cor": cor.strip(),
                    "renavam": v.only_digits(renavam),
                    "uf": uf_veic,
                    "cidade": v.normalize_name(cidade_veic),
                    "categoria": categoria,
                    "rntrc": rntrc.strip() if categoria == "Aluguel" else "",
                    "validade_rntrc": validade_rntrc.strip() if categoria == "Aluguel" else "",
                    "proprietario_tipo": pt,
                    "proprietario_doc": v.only_digits(doc),
                    "proprietario_rg_ie": v.only_digits(rg_prop),
                    "proprietario_uf": uf_prop,
                    "proprietario_nome": v.normalize_name(nome_prop) if pt == "Física" else nome_prop.strip(),
                    "proprietario_nasc": nasc_prop.strip() if pt == "Física" else "",
                    "proprietario_mae": v.normalize_name(mae_prop) if pt == "Física" else "",
                    "proprietario_celular": v.only_digits(cel_prop),
                    "payload_json": vehicle_payload,
                }

                _submit_via_rpc(request_row, vehicle_row)

                st.success(f"Solicitação registrada. Request ID: {request_id}")
                st.info(
                    "Envie a CNH por canal corporativo e informe no assunto:\n"
                    f"CNH - RequestID {request_id} - CPF {request_row['cpf']}"
                )

                clear_draft()
                st.session_state["portal_mode"] = "HOME"
                st.rerun()

            except Exception as e:
                st.error("Falha ao registrar solicitação.")
                with st.expander("Detalhes técnicos"):
                    st.code(str(e))


def cadastro_review_no_vehicle() -> None:
    st.subheader("Revisão final (sem veículo)")
    st.write("Confira os dados e confirme o envio da CNH ao gestor.")

    st.write({
        "Nome": st.session_state.get("draft_nome"),
        "CPF": st.session_state.get("draft_cpf"),
        "Nome Padrão": st.session_state.get("draft_nome_padrao"),
        "Base": st.session_state.get("draft_base_nome"),
        "UF Base": st.session_state.get("draft_base_uf"),
        "Modalidade": st.session_state.get("draft_modalidade"),
    })

    st.warning("CNH não é enviada por este portal. Você deve encaminhar a CNH ao gestor por canal corporativo.")
    cnh_ack = st.checkbox("Estou ciente e vou enviar a CNH ao gestor (obrigatório para solicitar).")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Voltar", use_container_width=True):
            st.session_state["portal_mode"] = "CADASTRO_STEP1"
            st.rerun()

    with colB:
        if st.button("Solicitar Cadastro", type="primary", use_container_width=True):
            try:
                if not cnh_ack:
                    raise ValueError("Confirme o envio da CNH ao gestor para continuar.")
                request_id = new_request_id()
                request_row = build_request_row_from_session(request_id=request_id, cnh_ack=cnh_ack)

                _submit_via_rpc(request_row, None)

                st.success(f"Solicitação registrada. Request ID: {request_id}")
                st.info(
                    "Envie a CNH por canal corporativo e informe no assunto:\n"
                    f"CNH - RequestID {request_id} - CPF {request_row['cpf']}"
                )
                clear_draft()
                st.session_state["portal_mode"] = "HOME"
                st.rerun()
            except Exception as e:
                st.error("Falha ao registrar solicitação.")
                with st.expander("Detalhes técnicos"):
                    st.code(str(e))


def portal_flow() -> None:
    mode = st.session_state.get("portal_mode", "HOME")

    if mode == "HOME":
        portal_home_select_role()
        return

    if mode == "CADASTRO_STEP1":
        cadastro_form_step1()
        return

    if mode == "CADASTRO_STEP2":
        cadastro_form_step2_vehicle()
        return

    if mode == "CADASTRO_REVIEW_NO_VEHICLE":
        cadastro_review_no_vehicle()
        return

    st.session_state["portal_mode"] = "HOME"
    st.rerun()


portal_header()
if "portal_mode" not in st.session_state:
    st.session_state["portal_mode"] = "HOME"
portal_flow()