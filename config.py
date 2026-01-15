from __future__ import annotations

# URLs
BR_HOME = "https://sistema.brasilrisk.com.br/"
DRIVER_CREATE_URL = "https://br2.brasilrisk.com.br/Motorista/Criar"
DRIVER_LIST_URL   = "https://br2.brasilrisk.com.br/Motorista/Listar"
VEHICLE_LIST_URL  = "https://br2.brasilrisk.com.br/Veiculo/Listar"

# Auth/captcha detection
OKTA_HOST_HINTS = ("okta.com", "purpleid.okta.com")
SAML_INTERMEDIATE_HINT = "/Account/ResponseOKTASAML"

# Fixed/default business rules (your spec)
DEFAULT_PERFIL = "Agregado"
DEFAULT_CC_EMPRESA = "FEDEX"
DEFAULT_RESP_FATURAMENTO = "FEDEX BRASIL"

# Mappings: values come from <option value="..."> in the HTML
# Gender values from your HTML sample:
#   CodGenero: 1=Feminino, 2=Masculino, 3=Outros
GENERO_TO_VALUE = {
    "Feminino": "1",
    "Masculino": "2",
    "Outros": "3",
}

# Função values from your HTML sample:
#   CodMotoristaFuncao: 1=Motorista, 2=Ajudante, 3=Outros, ...
FUNCAO_TO_VALUE = {
    "Motorista": "1",
    "Ajudante": "2",
}

# Perfil values from your HTML sample:
#   CodMotoristaPerfil: 1=Frota, 2=Agregado, 3=Autónomo
PERFIL_TO_VALUE = {
    "Agregado": "2",
}

# Cost Center / Billing responsible: values vary per tenant.
# For MVP we will select by visible label (recommended), but you can replace by numeric values if you prefer.
