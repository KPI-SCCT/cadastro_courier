@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
)

set "CA_PEM=%~dp0certs\corp-ca.pem"
if exist "%CA_PEM%" (
  set "SSL_CERT_FILE=%CA_PEM%"
  set "REQUESTS_CA_BUNDLE=%CA_PEM%"
  set "CURL_CA_BUNDLE=%CA_PEM%"
)

streamlit run portal.py --server.port 8503
endlocal