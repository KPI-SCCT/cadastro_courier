@echo off
setlocal

REM Vai para a pasta onde este .cmd está
cd /d "%~dp0"

REM Ativa o virtualenv (ajuste se seu venv tiver outro nome)
if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
)

REM (Opcional) Força uso de certificado corporativo se existir na pasta /certs
set "CA_PEM=%~dp0certs\corp-ca.pem"
if exist "%CA_PEM%" (
  set "SSL_CERT_FILE=%CA_PEM%"
  set "REQUESTS_CA_BUNDLE=%CA_PEM%"
  set "CURL_CA_BUNDLE=%CA_PEM%"
)

REM Porta fixa para não conflitar com o portal (ajuste se quiser)
streamlit run admin.py --server.port 8504

endlocal