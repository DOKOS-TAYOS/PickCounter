"""Main orchestration: counter_picks and counter_picks_from_dialog."""

from __future__ import annotations

from pathlib import Path

from .classification import classify_pick_color
from .config import COLOR_ORDER
from .detection import detect_picks
from .io import choose_image_file, read_image, validate_image_path
from .output import print_result, save_result


def counter_picks(route: str | Path) -> dict:
    """Count picks in an image and save results to JSON."""
    image_path = Path(route)
    validate_image_path(image_path)

    image = read_image(image_path)
    detections = detect_picks(image)

    color_counts = {color: 0 for color in COLOR_ORDER}
    for candidate in detections:
        color = classify_pick_color(image, candidate)
        color_counts[color] += 1

    ordered_colors = {color: color_counts[color] for color in COLOR_ORDER if color_counts[color] > 0}
    result = {"n_picks": len(detections), "colors": ordered_colors}

    save_result(result, image_path.stem)
    print_result(result)

    return result


def counter_picks_from_dialog(initial_dir: str | Path | None = None) -> dict:
    """Count picks in an image selected via file dialog."""
    image_path = choose_image_file(initial_dir=initial_dir)
    return counter_picks(image_path)
