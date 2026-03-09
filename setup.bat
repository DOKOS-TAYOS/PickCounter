@echo off
setlocal
set "ROOT=%~dp0"

python -m venv "%ROOT%\.venv"
call "%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
call "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
call "%ROOT%\.venv\Scripts\python.exe" -m pip install ruff
