@echo off
setlocal
set "ROOT=%~dp0"

echo ==========================================
echo   Pick Counter - Configuracion del entorno
echo ==========================================
echo.

echo [1/4] Creando entorno virtual en .venv...
python -m venv "%ROOT%\.venv"
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual. Verifica que Python este instalado.
    exit /b 1
)
echo       Entorno virtual creado correctamente.
echo.

echo [2/4] Actualizando pip...
call "%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
echo       pip actualizado.
echo.

echo [3/4] Instalando dependencias del proyecto...
call "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias.
    exit /b 1
)
echo       Dependencias instaladas (opencv, numpy, etc.).
echo.

echo [4/4] Instalando herramientas de desarrollo (ruff)...
call "%ROOT%\.venv\Scripts\python.exe" -m pip install ruff
echo       Ruff instalado.
echo.

echo ==========================================
echo   Configuracion completada correctamente.
echo   Ejecuta run.bat para iniciar la aplicacion.
echo ==========================================
