"""Main orchestration: counter_picks and counter_picks_from_dialog."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .classification import classify_pick_colors_batch
from .config import COLOR_ORDER, MAX_DETECTION_DIMENSION
from .detection import detect_picks
from .io import choose_image_file, read_image, validate_image_path
from .models import Candidate
from .output import print_result, save_result


def _scale_candidates_to_original(
    candidates: list[Candidate],
    scale: float,
    target_shape: tuple[int, int],
) -> list[Candidate]:
    """Scale candidates from detection image (scaled) back to original image size."""
    if scale >= 1.0:
        return candidates
    target_h, target_w = target_shape
    scaled: list[Candidate] = []
    for c in candidates:
        mask_resized = cv2.resize(
            c.mask.astype(np.uint8),
            (target_w, target_h),
            interpolation=cv2.INTER_NEAREST,
        )
        mask_binary = (mask_resized > 0).astype(np.uint8)
        contours, _ = cv2.findContours(  # noqa: S404
            mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        scaled.append(
            Candidate(
                mask=mask_binary,
                bbox=(x, y, w, h),
                area=int(mask_binary.sum()),
                source=c.source,
                color_hint=c.color_hint,
            )
        )
    return scaled


def counter_picks(route: str | Path) -> dict:
    """Count picks in an image and save results to JSON."""
    image_path = Path(route)
    validate_image_path(image_path)

    image = read_image(image_path)
    h, w = image.shape[:2]
    max_dim = max(h, w)
    if max_dim > MAX_DETECTION_DIMENSION:
        scale = MAX_DETECTION_DIMENSION / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        detection_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        detections = detect_picks(detection_image)
        detections = _scale_candidates_to_original(detections, scale, (h, w))
    else:
        detections = detect_picks(image)

    color_counts = {color: 0 for color in COLOR_ORDER}
    colors = classify_pick_colors_batch(image, detections)
    for color in colors:
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
