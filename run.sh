#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if [ ! -d "$ROOT/.venv" ]; then
    echo "ERROR: No existe el entorno virtual (.venv)."
    echo "Ejecuta primero: ./setup.sh"
    exit 1
fi

echo "Iniciando Pick Counter..."
echo "  - Si no pasas argumentos, se abrira un dialogo para elegir una imagen."
echo "  - Puedes pasar la ruta de una imagen: ./run.sh ruta/imagen.jpg"
echo ""

"$ROOT/.venv/bin/python" "$ROOT/src/pick_counter.py" "$@"
