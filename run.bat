@echo off
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%.venv" (
    echo ERROR: No existe el entorno virtual (.venv^).
    echo Ejecuta primero: setup.bat
    exit /b 1
)

echo Iniciando Pick Counter...
echo   - Si no pasas argumentos, se abrira un dialogo para elegir una imagen.
echo   - Puedes pasar la ruta de una imagen: run.bat ruta\imagen.jpg
echo.

call "%ROOT%\.venv\Scripts\python.exe" "%ROOT%src\pick_counter.py" %*
