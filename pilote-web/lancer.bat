@echo off
REM Lance Pilote Web. Double-cliquez sur ce fichier pour travailler.
setlocal
cd /d "%~dp0"
title Pilote Web

if not exist ".venv\Scripts\pythonw.exe" (
  echo Pilote Web n'est pas encore installe.
  echo Double-cliquez d'abord sur installer.bat
  pause
  exit /b 1
)

REM pythonw.exe = pas de fenetre noire derriere l'application.
start "" ".venv\Scripts\pythonw.exe" -m pilote
exit /b 0
