@echo off
chcp 65001 >nul
title SIGAE WEB - iniciando
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python nao foi encontrado neste computador.
  echo  Instale em https://www.python.org/downloads/
  echo  e marque a opcao "Add Python to PATH" durante a instalacao.
  echo.
  pause
  exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
  echo  Instalando o Flask - so acontece na primeira vez...
  python -m pip install -r requirements.txt
)

start "SIGAE WEB - servidor (feche esta janela para desligar)" /min cmd /k python app.py

start "" "%~dp0index.html"
exit /b 0
