"""Output handling: JSON export and console printing."""

from __future__ import annotations

import json
from pathlib import Path

from .config import COLOR_ORDER, CONSOLE_NAMES, OUTPUT_DIR


def save_result(result: dict, image_stem: str) -> Path:
    """Save result dict to JSON in output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{image_stem}.json"
    output_path.write_text(json.dumps(result, indent=4), encoding="utf-8")
    return output_path


def print_result(result: dict) -> None:
    """Print result to console in Spanish."""
    print(f"Numero de puas: {result['n_picks']}")
    ordered_colors = result.get("colors", {})
    for color in COLOR_ORDER:
        count = ordered_colors.get(color)
        if count:
            print(f"{CONSOLE_NAMES[color]}: {count}")
