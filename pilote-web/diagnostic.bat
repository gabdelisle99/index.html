@echo off
REM ===================================================================
REM  Etat des lieux : ce fichier ne modifie rien. Il regarde ce qui est
REM  installe sur l'ordinateur et ecrit le resultat dans diagnostic.txt,
REM  a envoyer en cas de probleme d'installation.
REM ===================================================================
setlocal
cd /d "%~dp0"
title Pilote Web - diagnostic
set "RAPPORT=%~dp0diagnostic.txt"

> "%RAPPORT%" echo === DIAGNOSTIC PILOTE WEB ===
>> "%RAPPORT%" echo Date : %DATE% %TIME%
>> "%RAPPORT%" echo Dossier : %~dp0
>> "%RAPPORT%" echo Windows : %OS% %PROCESSOR_ARCHITECTURE%
>> "%RAPPORT%" echo.

>> "%RAPPORT%" echo --- Ou se trouve Python ---
>> "%RAPPORT%" echo [where python]
where python >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo [where python3]
where python3 >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo [where py]
where py >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo.

>> "%RAPPORT%" echo --- Quelles versions repondent ---
>> "%RAPPORT%" echo [python --version]
python --version >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo [python3 --version]
python3 --version >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo [py -3 --version]
py -3 --version >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo [py --list]
py --list >> "%RAPPORT%" 2>&1
>> "%RAPPORT%" echo.

>> "%RAPPORT%" echo --- Dossiers d'installation habituels ---
if exist "%LOCALAPPDATA%\Programs\Python" (
  dir /b "%LOCALAPPDATA%\Programs\Python" >> "%RAPPORT%" 2>&1
) else (
  >> "%RAPPORT%" echo aucun dossier %LOCALAPPDATA%\Programs\Python
)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" (
  >> "%RAPPORT%" echo raccourci Microsoft Store present : python3.exe
) else (
  >> "%RAPPORT%" echo pas de raccourci Microsoft Store python3.exe
)
>> "%RAPPORT%" echo.

>> "%RAPPORT%" echo --- Installation de Pilote Web ---
if exist ".venv\Scripts\python.exe" (
  >> "%RAPPORT%" echo espace de travail present
  ".venv\Scripts\python.exe" --version >> "%RAPPORT%" 2>&1
  ".venv\Scripts\python.exe" -m pip list >> "%RAPPORT%" 2>&1
) else (
  >> "%RAPPORT%" echo espace de travail absent : installer.bat n'a pas encore reussi
)

echo.
echo ===============================================
echo   DIAGNOSTIC TERMINE
echo.
echo   Le rapport est ici :
echo   %RAPPORT%
echo.
echo   Ouvrez-le et envoyez-le moi (ou une capture).
echo ===============================================
echo.
type "%RAPPORT%"
echo.
pause
exit /b 0
