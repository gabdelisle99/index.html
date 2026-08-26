@echo off
REM ===================================================================
REM  Ouvre VOTRE Chrome de facon que Pilote Web puisse travailler
REM  dans les sessions deja ouvertes (mode "session_ouverte").
REM  Connectez-vous a vos sites dans cette fenetre, puis lancez
REM  Pilote Web normalement.
REM ===================================================================
setlocal
set "PROFIL=%LOCALAPPDATA%\PiloteWeb\chrome-partage"
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
  echo Chrome est introuvable. Installez Chrome, ou utilisez le mode
  echo "profil dedie" dans les reglages de Pilote Web.
  pause
  exit /b 1
)

start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFIL%"
exit /b 0
