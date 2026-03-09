#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

echo "=========================================="
echo "  Pick Counter - Configuracion del entorno"
echo "=========================================="
echo ""

echo "[1/4] Creando entorno virtual en .venv..."
python3 -m venv "$ROOT/.venv"
echo "      Entorno virtual creado correctamente."
echo ""

echo "[2/4] Actualizando pip..."
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
echo "      pip actualizado."
echo ""

echo "[3/4] Instalando dependencias del proyecto..."
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements.txt"
echo "      Dependencias instaladas (opencv, numpy, etc.)."
echo ""

echo "[4/4] Instalando herramientas de desarrollo (ruff)..."
"$ROOT/.venv/bin/python" -m pip install ruff
echo "      Ruff instalado."
echo ""

echo "=========================================="
echo "  Configuracion completada correctamente."
echo "  Ejecuta ./run.sh para iniciar la aplicacion."
echo "=========================================="
