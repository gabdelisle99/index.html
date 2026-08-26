@echo off
REM ===================================================================
REM  Pilote Web - installation. Double-cliquez sur ce fichier.
REM  Aucune connaissance technique requise : tout est automatique.
REM ===================================================================
setlocal
cd /d "%~dp0"
title Pilote Web - installation

echo.
echo ===============================================
echo   INSTALLATION DE PILOTE WEB
echo   Cela prend environ 5 minutes.
echo   Laissez cette fenetre ouverte jusqu'a la fin.
echo ===============================================
echo.

REM --- 1. Python present ? -------------------------------------------
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo [X] Python n'est pas installe sur cet ordinateur.
  echo.
  echo     1. Ouvrez le Microsoft Store
  echo     2. Cherchez "Python 3.12" et installez-le
  echo     3. Revenez ici et double-cliquez de nouveau sur installer.bat
  echo.
  pause
  exit /b 1
)
for /f "delims=" %%v in ('py -3 --version') do echo [OK] %%v detecte.

REM --- 2. Espace de travail isole ------------------------------------
if not exist ".venv" (
  echo [..] Creation de l'espace de travail...
  py -3 -m venv .venv
  if errorlevel 1 goto erreur
)
echo [OK] Espace de travail pret.

REM --- 3. Bibliotheques ----------------------------------------------
echo [..] Telechargement des bibliotheques (patience)...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto erreur
echo [OK] Bibliotheques installees.

REM --- 4. Navigateur pilote ------------------------------------------
echo [..] Installation du navigateur pilote (Chromium)...
call ".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto erreur
echo [OK] Navigateur pret.

echo.
echo ===============================================
echo   INSTALLATION TERMINEE
echo.
echo   Etape suivante : double-cliquez sur lancer.bat
echo   puis collez votre cle d'API Anthropic dans
echo   l'onglet Reglages.
echo ===============================================
echo.
pause
exit /b 0

:erreur
echo.
echo [X] L'installation a echoue. Verifiez votre connexion Internet,
echo     puis relancez installer.bat. Si le probleme persiste, envoyez
echo     une photo de cette fenetre.
echo.
pause
exit /b 1
