@echo off
REM ===================================================================
REM  Verifie que Pilote Web fonctionne, SANS appeler l'API Anthropic.
REM  Ces tests ne coutent rien. A lancer apres installer.bat.
REM ===================================================================
setlocal
cd /d "%~dp0"
title Pilote Web - verification

if not exist ".venv\Scripts\python.exe" (
  echo Pilote Web n'est pas encore installe.
  echo Double-cliquez d'abord sur installer.bat
  echo.
  pause
  exit /b 1
)

set ECHECS=0

echo.
echo ===============================================
echo   VERIFICATION DE PILOTE WEB
echo   Aucun appel a l'API : ces tests sont gratuits.
echo ===============================================
echo.

echo --- 1/3 Socle : reglages, journal, regle lecture/ecriture
call ".venv\Scripts\python.exe" tests\test_socle.py
if errorlevel 1 set /a ECHECS+=1
echo.

echo --- 2/3 Boucle de raisonnement : plafonds, historique, arret propre
call ".venv\Scripts\python.exe" tests\test_boucle.py
if errorlevel 1 set /a ECHECS+=1
echo.

echo --- 3/3 Essai complet sur une fausse page de CRM (vrai navigateur)
echo     Le navigateur travaille SANS FENETRE : c'est normal de ne rien
echo     voir s'ouvrir a l'ecran. Seul le resultat ci-dessous compte.
call ".venv\Scripts\python.exe" tests\test_integration.py
if errorlevel 1 set /a ECHECS+=1
echo.

if %ECHECS%==0 (
  echo ===============================================
  echo   TOUT FONCTIONNE.
  echo   Vous pouvez lancer l'application : lancer.bat
  echo ===============================================
) else (
  echo ===============================================
  echo   %ECHECS% verification(s) en echec.
  echo   Faites une capture de cette fenetre et
  echo   envoyez-la : la ligne "ECHEC" dit quoi corriger.
  echo ===============================================
)
echo.
pause
exit /b %ECHECS%
