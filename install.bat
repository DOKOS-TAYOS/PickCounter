@echo off
setlocal
set "REPO_URL=https://github.com/DOKOS-TAYOS/PickCounter.git"
set "REPO_DIR=pick_counter"

echo ==========================================
echo   Pick Counter - Instalador completo
echo ==========================================
echo.

REM --- Comprobar Git ---
echo [1/4] Comprobando Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Git no esta instalado.
    echo.
    echo Descarga Git desde: https://git-scm.com/download/win
    echo O con winget: winget install Git.Git
    echo.
    exit /b 1
)
echo       Git encontrado.
echo.

REM --- Comprobar Python ---
echo [2/4] Comprobando Python...
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: Python no esta instalado.
        echo.
        echo Descarga Python 3.12 desde: https://www.python.org/downloads/
        echo O con winget: winget install Python.Python.3.12
        echo.
        echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
        echo.
        exit /b 1
    )
)
echo       Python encontrado.
echo.

REM --- Clonar o usar repo existente ---
echo [3/4] Preparando repositorio...
if exist "%REPO_DIR%\.git" (
    echo       Repositorio ya clonado en %REPO_DIR%. Actualizando...
    pushd "%REPO_DIR%"
    git pull
    if errorlevel 1 (
        echo       Advertencia: No se pudo actualizar. Continuando con la version actual.
    )
    popd
) else if exist "%~dp0.git" (
    echo       Ejecutando desde el repositorio clonado.
    set "REPO_DIR=%~dp0"
    if "%REPO_DIR:~-1%"=="\" set "REPO_DIR=%REPO_DIR:~0,-1%"
) else (
    echo       Clonando repositorio...
    git clone "%REPO_URL%" "%REPO_DIR%"
    if errorlevel 1 (
        echo ERROR: No se pudo clonar el repositorio.
        exit /b 1
    )
    echo       Repositorio clonado correctamente.
)
echo.

REM --- Ejecutar setup ---
echo [4/4] Ejecutando configuracion del entorno...
if exist "%REPO_DIR%\setup.bat" (
    call "%REPO_DIR%\setup.bat"
    if errorlevel 1 (
        echo ERROR: Fallo en la configuracion.
        exit /b 1
    )
) else (
    echo ERROR: No se encontro setup.bat en %REPO_DIR%
    exit /b 1
)

echo.
echo ==========================================
echo   Instalacion completada correctamente.
echo   Entra en %REPO_DIR% y ejecuta run.bat
echo ==========================================
