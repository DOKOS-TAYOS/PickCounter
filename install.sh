#!/usr/bin/env sh
set -eu

REPO_URL="https://github.com/DOKOS-TAYOS/PickCounter.git"
REPO_DIR="pick_counter"

echo "=========================================="
echo "  Pick Counter - Instalador completo"
echo "=========================================="
echo ""

# --- Detectar sistema y paquete ---
detect_pkg_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "yum"
    elif command -v brew >/dev/null 2>&1; then
        echo "brew"
    elif command -v apk >/dev/null 2>&1; then
        echo "apk"
    else
        echo ""
    fi
}

# --- Instalar paquete (con sudo si hace falta) ---
install_pkg() {
    PKG="$1"
    PM=$(detect_pkg_manager)
    case "$PM" in
        apt)  sudo apt-get update && sudo apt-get install -y "$PKG" ;;
        dnf)  sudo dnf install -y "$PKG" ;;
        yum)  sudo yum install -y "$PKG" ;;
        brew) brew install "$PKG" ;;
        apk)  sudo apk add --no-cache "$PKG" ;;
        *)    echo "ERROR: No se detecto gestor de paquetes (apt, dnf, yum, brew, apk). Instala $PKG manualmente."; exit 1 ;;
    esac
}

# --- Comprobar Git ---
echo "[1/4] Comprobando Git..."
if ! command -v git >/dev/null 2>&1; then
    echo "      Git no encontrado. Instalando..."
    install_pkg git
fi
echo "      Git encontrado."
echo ""

# --- Comprobar Python ---
echo "[2/4] Comprobando Python..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "      Python no encontrado. Instalando..."
    PM=$(detect_pkg_manager)
    case "$PM" in
        apt)  install_pkg python3 python3-venv python3-pip ;;
        dnf|yum) install_pkg python3 python3-pip ;;
        brew) install_pkg python@3.12 ;;
        apk)  install_pkg python3 py3-pip ;;
        *)    echo "ERROR: Instala Python 3 manualmente."; exit 1 ;;
    esac
fi
echo "      Python encontrado."
echo ""

# --- Clonar o usar repo existente ---
echo "[3/4] Preparando repositorio..."
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -d "$SCRIPT_DIR/.git" ]; then
    echo "      Ejecutando desde el repositorio clonado."
    REPO_DIR="$SCRIPT_DIR"
elif [ -d "$REPO_DIR/.git" ]; then
    echo "      Repositorio ya clonado en $REPO_DIR. Actualizando..."
    (cd "$REPO_DIR" && git pull) || echo "      Advertencia: No se pudo actualizar. Continuando."
else
    echo "      Clonando repositorio..."
    git clone "$REPO_URL" "$REPO_DIR"
    echo "      Repositorio clonado correctamente."
fi
echo ""

# --- Ejecutar setup ---
echo "[4/4] Ejecutando configuracion del entorno..."
if [ -f "$REPO_DIR/setup.sh" ]; then
    sh "$REPO_DIR/setup.sh"
else
    echo "ERROR: No se encontro setup.sh en $REPO_DIR"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Instalacion completada correctamente."
echo "  Entra en $REPO_DIR y ejecuta ./run.sh"
echo "=========================================="
