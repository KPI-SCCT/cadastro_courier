# Cadastro Courier — MVP (Portal + Console Admin + Worker Playwright)

## 1) O que é
Este MVP tem:
- **Portal (Streamlit)**: usuário preenche dados do courier (e veículo quando aplicável) e cria uma solicitação.
- **Console Admin (Streamlit)**: admin visualiza solicitações e **enfileira** execução de Etapa 1 e Etapa 2.
- **Worker (Python + Playwright)**: roda no PC do admin, abre browser, e executa automação.
  - Se cair em **OKTA/SAML/anti-bot**, o fluxo **aguarda ação humana** (resolver captcha/login) e depois continua.

## 2) Estrutura
Arquivos principais:
- `app_streamlit.py` (Portal + Admin no mesmo app)
- `worker.py` (processa jobs)
- `brasilrisk_automation.py` (playwright step1 e esqueleto step2)
- `db.py` (sqlite)
- `storage.py` (uploads temporários CNH)
- `settings.py` (paths de runtime fora do OneDrive)

## 3) Setup (Windows)
Na pasta do projeto:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 4) Rodando
### 4.1) Defina runtime fora do OneDrive (recomendado)
Exemplo:
```powershell
$env:CCR_RUNTIME_DIR="C:\temp\Cadastro_Brasil_Risk_runtime"
```

### 4.2) Rodar Portal/Admin
```powershell
streamlit run app_streamlit.py
```

### 4.3) Rodar Worker (outro terminal)
```powershell
python worker.py
```

## 5) Fluxo de trabalho
1) Usuário cria solicitação no Portal.
2) Admin abre Console Admin, escolhe o request e enfileira Etapa 1.
3) Worker executa Etapa 1. Se aparecer captcha/OKTA, admin resolve no navegador.
4) Após Etapa 1 DONE, admin enfileira Etapa 2 (quando aplicável).

## 6) Observações importantes
- Captcha/OKTA **não** é burlado pelo sistema (por estabilidade e compliance). O worker pausa e aguarda ação humana.
- A Etapa 2 (veículo) está como esqueleto até você fornecer os seletores reais da tela de criação do veículo.

## 7) Runtime fora do OneDrive (recomendado)
Para evitar erros de sincronização/bloqueio do OneDrive (SQLite e perfil do Chromium), este MVP suporta variáveis de ambiente:

- `CCR_RUNTIME_DIR` (recomendado): pasta raiz para **DB**, **uploads**, **logs**, **pw_profile**
- `CCR_DB_PATH` (opcional): caminho completo do SQLite
- `CCR_PW_PROFILE_DIR` (opcional): pasta do perfil persistente do Playwright
- `CCR_UPLOADS_DIR` (opcional): pasta de uploads temporários
- `CCR_LOGS_DIR` (opcional): pasta de logs

### Exemplo (Windows / PowerShell)
Crie uma pasta local (fora do OneDrive), por exemplo:
`C:\temp\Cadastro_Brasil_Risk_runtime`

Depois, no PowerShell:
```powershell
$env:CCR_RUNTIME_DIR="C:\temp\Cadastro_Brasil_Risk_runtime"
streamlit run app_streamlit.py
```

Em outro terminal, no mesmo PowerShell (ou repetindo a variável):
```powershell
$env:CCR_RUNTIME_DIR="C:\temp\Cadastro_Brasil_Risk_runtime"
python worker.py
```

> Se você preferir tornar permanente, use `setx CCR_RUNTIME_DIR "C:\temp\Cadastro_Brasil_Risk_runtime"` e reabra o terminal.
