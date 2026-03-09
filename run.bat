@echo off
setlocal
set "ROOT=%~dp0"
call "%ROOT%\.venv\Scripts\python.exe" "%ROOT%src\pick_counter.py"
