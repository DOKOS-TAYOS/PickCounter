"""Configuration constants and paths for pick-counter."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

COLOR_ORDER = [
    "black",
    "gray",
    "white",
    "brown",
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "pink",
]

CONSOLE_NAMES: dict[str, str] = {
    "black": "Negra",
    "gray": "Gris",
    "white": "Blanca",
    "brown": "Marron",
    "red": "Roja",
    "orange": "Naranja",
    "yellow": "Amarilla",
    "green": "Verde",
    "cyan": "Cian",
    "blue": "Azul",
    "purple": "Morada",
    "pink": "Rosa",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
