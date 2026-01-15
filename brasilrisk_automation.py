from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

from config import (
    DRIVER_CREATE_URL, VEHICLE_LIST_URL,
    OKTA_HOST_HINTS, SAML_INTERMEDIATE_HINT,
    GENERO_TO_VALUE, FUNCAO_TO_VALUE, PERFIL_TO_VALUE
)
from models import CourierRequest
from settings import pw_profile_dir

class HumanStepRequired(RuntimeError):
    """Raised when human must solve captcha/Okta or any blocking step."""

def _is_okta_or_saml(url: str) -> bool:
    u = (url or "").lower()
    if SAML_INTERMEDIATE_HINT.lower() in u:
        return True
    return any(h in u for h in OKTA_HOST_HINTS)

def _wait_until_not_okta(page, timeout_s: int = 300) -> None:
    """Wait until page is not on OKTA/SAML. User may need to interact."""
    t0 = time.time()
    while True:
        if not _is_okta_or_saml(page.url):
            return
        if time.time() - t0 > timeout_s:
            raise HumanStepRequired("Tempo excedido aguardando autenticação/anti-bot.")
        time.sleep(1.0)

def _wait_until_on_driver_create(page, timeout_s: int = 60) -> None:
    t0 = time.time()
    while True:
        if "/Motorista/Criar".lower() in (page.url or "").lower():
            # Confirm by H1 presence
            try:
                page.wait_for_selector("h1#Motorista", timeout=2_000)
                return
            except PwTimeout:
                pass
        if time.time() - t0 > timeout_s:
            raise RuntimeError("Não consegui chegar na tela Adicionar Motorista (timeout).")
        time.sleep(0.5)

def ensure_logged_in_and_on_driver_create(page) -> None:
    page.goto(DRIVER_CREATE_URL, wait_until="domcontentloaded")
    # If we land on OKTA/SAML/captcha, wait for human solve then navigate back
    if _is_okta_or_saml(page.url):
        _wait_until_not_okta(page, timeout_s=600)
        # Try again
        page.goto(DRIVER_CREATE_URL, wait_until="domcontentloaded")

    # Also sometimes a simple anti-bot checkbox page is used; we don't bypass it.
    # User should click/solve; we detect by "Account/ResponseOKTASAML" or okta host.

    _wait_until_on_driver_create(page)

def attach_cnh_pdf_or_image(page, cnh_path: str) -> None:
    p = Path(cnh_path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo CNH não encontrado: {cnh_path}")

    # PDF modal
    try:
        page.locator("#btnEnviarPdfCNH").click()
        page.wait_for_selector("#modalPdfCNHCreate", timeout=10_000)
        file_input = page.locator("#modalPdfCNHCreate input[type='file']")
        if file_input.count() > 0:
            file_input.first.set_input_files(str(p))
            # Try confirm buttons inside modal
            # Common patterns: a button with id or "Salvar/Enviar"
            for sel in ["#modalPdfCNHCreate button.btn-primary", "#modalPdfCNHCreate button[type='submit']"]:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    break
        # close if still open
        if page.locator("#modalPdfCNHCreate .close").count() > 0:
            page.locator("#modalPdfCNHCreate .close").first.click()
    except PwTimeout:
        # If modal didn't appear, ignore (some tenants disable PDF)
        return
    except Exception:
        return

def fill_step1_driver(page, req: CourierRequest) -> None:
    d = req.driver

    if d.cnh_path:
        attach_cnh_pdf_or_image(page, d.cnh_path)

    # Basic selects and inputs (IDs are from your HTML sample)
    page.fill("#Nome", d.nome)

    # Selects are select2; select_option should still set underlying select
    page.select_option("#CodGenero", value=GENERO_TO_VALUE[d.genero])

    page.fill("#DataNascimento", d.data_nascimento.strftime("%d/%m/%Y"))
    page.fill("#CPF", d.cpf)
    page.fill("#RG", d.rg)
    page.fill("#DataEmissao", d.data_emissao.strftime("%d/%m/%Y"))
    page.fill("#OrgaoExp", d.orgao_exp)

    pai = d.nome_pai or "Não Informado"
    page.fill("#NomePai", pai)
    page.fill("#NomeMae", d.nome_mae)

    page.select_option("#CodMotoristaFuncao", value=FUNCAO_TO_VALUE[d.funcao])
    page.select_option("#CodMotoristaPerfil", value=PERFIL_TO_VALUE["Agregado"])

    # Cost center company by visible label (FEDEX)
    # Underlying select: #CodEmpresaCentroCusto
    try:
        page.select_option("#CodEmpresaCentroCusto", label=d.empresa_centro_custo)
    except Exception:
        # fallback: try partial label
        options = page.locator("#CodEmpresaCentroCusto option").all_inner_texts()
        match = None
        for opt in options:
            if d.empresa_centro_custo.lower() in (opt or "").lower():
                match = opt
                break
        if match:
            page.select_option("#CodEmpresaCentroCusto", label=match)

    # Billing responsible: #CodEmpresaFaturamento
    try:
        page.select_option("#CodEmpresaFaturamento", label=d.responsavel_faturamento)
    except Exception:
        pass

    # Address
    page.fill("#Cep", d.cep)
    page.keyboard.press("Tab")
    time.sleep(0.8)

    page.select_option("#Cidade_UF_CodUF", label=d.uf)
    time.sleep(0.6)
    # city loads after UF
    try:
        page.select_option("#CodCidade", label=d.cidade)
    except Exception:
        # sometimes city values are numeric; try matching by partial label
        options = page.locator("#CodCidade option").all_inner_texts()
        match = None
        for opt in options:
            if d.cidade.lower() in (opt or "").lower():
                match = opt
                break
        if match:
            page.select_option("#CodCidade", label=match)

    page.fill("#Bairro", d.bairro)
    page.fill("#Logradouro", d.logradouro)
    page.fill("#Numero", d.numero)
    if d.complemento:
        page.fill("#Complemento", d.complemento)

    # Contact
    if d.telefone:
        page.fill("#TelResidencial", d.telefone)
    page.fill("#TelCelular", d.celular)
    if d.telefone_comercial:
        page.fill("#TelComercial", d.telefone_comercial)
    if d.email:
        page.fill("#Email", d.email)

    # CNH
    page.fill("#CNHRegistro", d.cnh_registro)
    page.fill("#CNHNumero", d.cnh_numero)
    page.fill("#CNHCategoria", d.cnh_categoria)
    page.fill("#CNHValidade", d.cnh_validade.strftime("%d/%m/%Y"))
    page.select_option("#CNHCodUF", label=d.cnh_uf)

def click_save_driver(page) -> None:
    # provided xpath //*[@id="salvarMotorista"]
    page.click("#salvarMotorista")

def run_step1_driver(
    req_dict: dict[str, Any],
    *,
    headless: bool = False,
    user_data_dir: str | None = None,
) -> dict[str, Any]:
    """Executes STEP1 in a persistent browser context.

    Returns dict with:
      - ok: bool
      - need_human: bool
      - message/logs
    """
    req = CourierRequest.model_validate(req_dict)

    logs: list[str] = []
    def log(s: str) -> None:
        logs.append(s)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir or pw_profile_dir()),
            headless=headless,
            viewport={"width": 1400, "height": 900},
        )
        try:
            page = ctx.new_page()

            log("Abrindo tela de cadastro do motorista…")
            ensure_logged_in_and_on_driver_create(page)

            log("Preenchendo formulário do motorista…")
            fill_step1_driver(page, req)

            log("Salvando…")
            click_save_driver(page)

            # Wait for either success redirect or validation alert
            time.sleep(2.0)

            # Very tenant-specific: you can add checks for toast/alerts
            return {"ok": True, "need_human": False, "message": "Etapa 1 enviada (verifique alerts).", "logs": logs}

        except HumanStepRequired as e:
            return {"ok": False, "need_human": True, "message": str(e), "logs": logs}
        except Exception as e:
            return {"ok": False, "need_human": False, "message": repr(e), "logs": logs}
        finally:
            ctx.close()

def run_step2_vehicle(
    req_dict: dict[str, Any],
    *,
    headless: bool = False,
    user_data_dir: str | None = None,
) -> dict[str, Any]:
    """STEP2 skeleton (Vehicle). Implement selectors after you provide DOM/IDs of the create vehicle page."""
    logs: list[str] = []
    def log(s: str) -> None:
        logs.append(s)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir or pw_profile_dir()),
            headless=headless,
            viewport={"width": 1400, "height": 900},
        )
        try:
            page = ctx.new_page()
            log("Abrindo lista de veículos (para navegar à criação)…")
            page.goto(VEHICLE_LIST_URL, wait_until="domcontentloaded")

            if _is_okta_or_saml(page.url):
                log("Detectado OKTA/SAML/anti-bot. Aguardando interação humana…")
                _wait_until_not_okta(page, timeout_s=600)
                page.goto(VEHICLE_LIST_URL, wait_until="domcontentloaded")

            # TODO: after you provide create vehicle URL/IDs, implement filling and saving.
            return {"ok": False, "need_human": False, "message": "Etapa 2 ainda não implementada (faltam seletores/DOM).", "logs": logs}

        except HumanStepRequired as e:
            return {"ok": False, "need_human": True, "message": str(e), "logs": logs}
        except Exception as e:
            return {"ok": False, "need_human": False, "message": repr(e), "logs": logs}
        finally:
            ctx.close()
