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

REM --- 1. Trouver Python (3.10 ou plus recent) ------------------------
REM  On essaie toutes les facons dont Python peut etre installe sur
REM  Windows : le lanceur "py", les commandes "python"/"python3", puis
REM  les emplacements habituels du Store et de python.org.
set "PYEXE="
echo [..] Recherche de Python...

call :essai py -3.13
call :essai py -3.12
call :essai py -3.11
call :essai py -3
call :essai python
call :essai python3
call :essai "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :essai "%%~D\python.exe"
for /d %%D in ("%ProgramFiles%\Python3*") do call :essai "%%~D\python.exe"
for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :essai "%%~D\python.exe"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Launcher") do call :essai "%%~D\py.exe" -3

if not defined PYEXE goto pas_de_python

echo [OK] Python trouve :
%PYEXE% --version

REM --- 2. Espace de travail isole ------------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo [..] Creation de l'espace de travail...
  %PYEXE% -m venv .venv
  if errorlevel 1 goto erreur
)
set "VPY=.venv\Scripts\python.exe"
echo [OK] Espace de travail pret.

REM --- 3. Bibliotheques indispensables --------------------------------
echo [..] Telechargement des bibliotheques (patience)...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto erreur
echo [OK] Bibliotheques installees.

REM --- 4. Voix (facultative : un echec n'est pas bloquant) -------------
echo [..] Installation de la voix et de la dictee...
"%VPY%" -m pip install -r requirements-voix.txt --quiet
if errorlevel 1 (
  echo [!] La voix n'a pas pu etre installee. Ce n'est PAS bloquant :
  echo     vous ecrirez vos consignes au clavier et lirez les reponses
  echo     a l'ecran. Tout le reste fonctionne.
) else (
  echo [OK] Voix installee.
)

REM --- 5. Navigateur pilote ------------------------------------------
echo [..] Installation du navigateur pilote (Chromium)...
"%VPY%" -m playwright install chromium
if errorlevel 1 goto erreur
echo [OK] Navigateur pret.

echo.
echo ===============================================
echo   INSTALLATION TERMINEE
echo.
echo   1. Verifiez que tout marche : tester.bat
echo   2. Lancez l'application      : lancer.bat
echo   3. Collez votre cle d'API dans l'onglet Reglages
echo ===============================================
echo.
pause
exit /b 0

REM ===================================================================
REM  Sous-programme : garde le premier Python qui repond et qui est
REM  assez recent. Les raccourcis du Microsoft Store qui ouvrent le
REM  Store au lieu de demarrer Python echouent ici, donc sont ignores.
REM ===================================================================
:essai
if defined PYEXE goto :eof
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PYEXE=%*"
goto :eof

:pas_de_python
echo.
echo [X] Je n'arrive pas a demarrer Python sur cet ordinateur.
echo.
echo     J'ai essaye : py -3.13, py -3.12, py -3.11, py -3, python,
echo     python3, et les dossiers d'installation habituels.
echo.
echo     Si Python est deja installe, c'est presque toujours l'une
echo     de ces deux causes :
echo.
echo     A) Python est installe mais pas accessible.
echo        Ouvrez le menu Demarrer, tapez "invite de commandes",
echo        ouvrez-la, tapez :   where python
echo        Envoyez-moi ce qui s'affiche.
echo.
echo     B) Les "alias d'execution d'application" sont desactives.
echo        Menu Demarrer - Parametres - Applications -
echo        Parametres avances des applications -
echo        Alias d'execution d'application :
echo        activez "python.exe" et "python3.exe", puis relancez ce fichier.
echo.
echo     Si Python n'est pas installe : Microsoft Store, cherchez
echo     "Python 3.12" (3.11 et 3.13 conviennent aussi), installez,
echo     puis relancez installer.bat.
echo.
pause
exit /b 1

:erreur
echo.
echo [X] L'installation a echoue. Verifiez votre connexion Internet,
echo     puis relancez installer.bat. Si le probleme persiste, faites
echo     une capture de cette fenetre et envoyez-la.
echo.
pause
exit /b 1
