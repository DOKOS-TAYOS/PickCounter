from __future__ import annotations

import json
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog

import cv2
import numpy as np

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
CONSOLE_NAMES = {
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


@dataclass(slots=True)
class Candidate:
    mask: np.ndarray
    bbox: tuple[int, int, int, int]
    area: int
    source: str
    color_hint: str | None = None


def counter_picks(route: str | Path) -> dict:
    image_path = Path(route)
    _validate_image_path(image_path)

    image = _read_image(image_path)
    detections = _detect_picks(image, image_path)

    color_counts = {color: 0 for color in COLOR_ORDER}
    for candidate in detections:
        color = _classify_pick_color(image, candidate)
        color_counts[color] += 1

    ordered_colors = {color: color_counts[color] for color in COLOR_ORDER if color_counts[color] > 0}
    result = {"n_picks": len(detections), "colors": ordered_colors}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{image_path.stem}.json"
    output_path.write_text(json.dumps(result, indent=4), encoding="utf-8")

    print(f"Numero de puas: {result['n_picks']}")
    for color in COLOR_ORDER:
        count = ordered_colors.get(color)
        if count:
            print(f"{CONSOLE_NAMES[color]}: {count}")

    return result


def counter_picks_from_dialog(initial_dir: str | Path | None = None) -> dict:
    image_path = choose_image_file(initial_dir=initial_dir)
    return counter_picks(image_path)


def choose_image_file(initial_dir: str | Path | None = None) -> Path:
    start_dir = Path(initial_dir) if initial_dir is not None else REPO_ROOT / "input"
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(
            title="Selecciona una imagen",
            initialdir=str(start_dir),
            filetypes=[
                ("Imagenes", "*.jpg *.jpeg *.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
            ],
        )
    finally:
        root.destroy()

    if not selected:
        raise RuntimeError("No image selected.")
    return Path(selected)


def _validate_image_path(image_path: Path) -> None:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")


def _read_image(image_path: Path) -> np.ndarray:
    raw = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    return image


def _detect_picks(image: np.ndarray, image_path: Path) -> list[Candidate]:
    del image_path
    return _detect_classically(image)


def _detect_classically(image: np.ndarray) -> list[Candidate]:
    if _is_clear_background(image):
        candidates = _detect_on_clear_background(image)
    else:
        candidates = _detect_on_textured_background(image)
        if not candidates:
            candidates = _detect_on_clear_background(image)

    return _sort_candidates(_dedupe_candidates(_split_oversized_candidates(image, candidates)))


def _is_clear_background(image: np.ndarray) -> bool:
    border = _image_border_pixels(image)
    mean_value = float(np.mean(border))
    std_value = float(np.mean(np.std(border, axis=0)))
    return mean_value >= 245.0 and std_value <= 3.5


def _detect_on_clear_background(image: np.ndarray) -> list[Candidate]:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    border_lab = _image_border_pixels(lab)
    background_lab = np.median(border_lab, axis=0)
    distance = np.linalg.norm(lab.astype(np.float32) - background_lab.astype(np.float32), axis=2)

    mask = (distance > 18.0).astype(np.uint8)
    mask = _cleanup_mask(mask, close_size=5, open_size=3, close_iterations=2, open_iterations=1)

    if mask.sum() == 0:
        return []

    distance_map = cv2.distanceTransform((mask * 255).astype(np.uint8), cv2.DIST_L2, 5)
    if float(distance_map.max()) <= 0.0:
        return _extract_candidates_from_mask(mask, "clear-mask")

    sure_fg = (distance_map > 0.45 * float(distance_map.max())).astype(np.uint8)
    sure_fg = _cleanup_mask(sure_fg, close_size=3, open_size=3, close_iterations=1, open_iterations=1)
    expanded = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    unknown = ((expanded - sure_fg) > 0).astype(np.uint8)

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 1] = 0
    watershed = cv2.watershed(image.copy(), markers.astype(np.int32))

    candidates: list[Candidate] = []
    for label in np.unique(watershed):
        if label <= 1:
            continue
        region = (watershed == label).astype(np.uint8)
        candidate = _candidate_from_mask(region, image.shape[:2], "clear-watershed")
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def _detect_on_textured_background(image: np.ndarray) -> list[Candidate]:
    palette_candidates = _detect_textured_palette_candidates(image)
    grabcut_mask = _build_textured_grabcut_mask(image)
    grabcut_candidates = _extract_candidates_from_mask(grabcut_mask, "textured-grabcut")

    if not palette_candidates:
        return grabcut_candidates

    combined = list(palette_candidates)
    for candidate in grabcut_candidates:
        overlap = max((_mask_iou(candidate.mask, existing.mask) for existing in combined), default=0.0)
        if overlap < 0.15:
            combined.append(candidate)
    return combined


def _build_textured_grabcut_mask(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    border_lab = _image_border_pixels(lab)
    background_ab = np.median(border_lab[:, 1:], axis=0)
    chroma_distance = np.linalg.norm(lab[:, :, 1:].astype(np.float32) - background_ab.astype(np.float32), axis=2)
    saturation = hsv[:, :, 1].astype(np.float32)
    value = hsv[:, :, 2].astype(np.float32)
    local_shadow = cv2.GaussianBlur(value, (0, 0), 25) - value

    mask = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    margin = max(10, min(h, w) // 24)
    mask[:margin, :] = cv2.GC_BGD
    mask[-margin:, :] = cv2.GC_BGD
    mask[:, :margin] = cv2.GC_BGD
    mask[:, -margin:] = cv2.GC_BGD

    probable_fg = (saturation > 28.0) | (chroma_distance > 14.0) | (local_shadow > 28.0)
    sure_fg = (saturation > 45.0) | (chroma_distance > 22.0) | (local_shadow > 42.0)
    mask[probable_fg] = cv2.GC_PR_FGD
    mask[sure_fg] = cv2.GC_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    try:
        cv2.grabCut(image, mask, None, background_model, foreground_model, 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return np.zeros((h, w), dtype=np.uint8)

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    return _cleanup_mask(fg_mask, close_size=9, open_size=5, close_iterations=2, open_iterations=1)


def _detect_textured_palette_candidates(image: np.ndarray) -> list[Candidate]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    family_masks = _build_color_family_masks(hsv)

    cleaned_masks = {
        color_hint: _cleanup_mask(mask, close_size=9, open_size=5, close_iterations=2, open_iterations=1)
        for color_hint, mask in family_masks.items()
    }
    colored_union = np.zeros(image.shape[:2], dtype=np.uint8)
    for color_hint, mask in cleaned_masks.items():
        if color_hint not in {"black", "gray", "white"}:
            colored_union = np.maximum(colored_union, mask)

    dilation_size = _odd_kernel(max(15, min(image.shape[:2]) // 50))
    dilated_colored_union = cv2.dilate(colored_union, np.ones((dilation_size, dilation_size), np.uint8), iterations=1)
    cleaned_masks["black"] = ((cleaned_masks["black"] > 0) & (dilated_colored_union == 0)).astype(np.uint8)
    cleaned_masks["black"] = _cleanup_mask(cleaned_masks["black"], close_size=9, open_size=5, close_iterations=2, open_iterations=1)

    candidates: list[Candidate] = []
    for color_hint, cleaned in cleaned_masks.items():
        if color_hint in {"gray", "white"}:
            continue
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            component_mask = np.zeros(cleaned.shape, dtype=np.uint8)
            cv2.drawContours(component_mask, [contour], -1, 1, thickness=cv2.FILLED)
            candidate = _candidate_from_mask(
                component_mask,
                image.shape[:2],
                source=f"palette-{color_hint}",
                color_hint=color_hint,
                textured=True,
            )
            if candidate is not None:
                candidates.append(candidate)

    return _dedupe_candidates(candidates)


def _extract_candidates_from_mask(mask: np.ndarray, source: str) -> list[Candidate]:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    candidates: list[Candidate] = []
    for label in range(1, num_labels):
        if stats[label, cv2.CC_STAT_AREA] <= 0:
            continue
        region = (labels == label).astype(np.uint8)
        candidate = _candidate_from_mask(region, mask.shape, source)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _candidate_from_mask(
    mask: np.ndarray,
    image_shape: tuple[int, int],
    source: str,
    color_hint: str | None = None,
    textured: bool = False,
) -> Candidate | None:
    binary = (mask > 0).astype(np.uint8)
    area = int(binary.sum())
    image_area = image_shape[0] * image_shape[1]
    min_area = max(1000, int(image_area * (0.002 if textured else 0.001)))
    max_area = int(image_area * 0.45)
    if area < min_area or area > max_area:
        return None

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    contour_area = float(cv2.contourArea(contour))
    if contour_area <= 0.0:
        return None

    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = max(w / max(h, 1), h / max(w, 1))
    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = contour_area / hull_area if hull_area else 0.0

    if aspect_ratio > 2.3:
        return None
    if solidity < (0.82 if textured else 0.55):
        return None

    return Candidate(mask=binary, bbox=(x, y, w, h), area=area, source=source, color_hint=color_hint)


def _split_oversized_candidates(image: np.ndarray, candidates: list[Candidate]) -> list[Candidate]:
    if len(candidates) < 2:
        return candidates

    areas = np.array([candidate.area for candidate in candidates], dtype=np.float32)
    median_area = float(np.median(areas))
    if median_area <= 0.0:
        return candidates

    split_candidates: list[Candidate] = []
    for candidate in candidates:
        if candidate.area > median_area * 1.8:
            pieces = _split_candidate_region(image, candidate.mask, median_area, candidate.source, candidate.color_hint)
            if len(pieces) > 1:
                split_candidates.extend(pieces)
                continue
        split_candidates.append(candidate)
    return split_candidates


def _split_candidate_region(
    image: np.ndarray,
    mask: np.ndarray,
    median_area: float,
    source: str,
    color_hint: str | None,
) -> list[Candidate]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return []

    x1 = max(int(xs.min()) - 2, 0)
    y1 = max(int(ys.min()) - 2, 0)
    x2 = min(int(xs.max()) + 3, image.shape[1])
    y2 = min(int(ys.max()) + 3, image.shape[0])

    local_mask = mask[y1:y2, x1:x2].astype(np.uint8)
    distance_map = cv2.distanceTransform((local_mask * 255).astype(np.uint8), cv2.DIST_L2, 5)
    if float(distance_map.max()) <= 0.0:
        return [Candidate(mask=mask, bbox=(x1, y1, x2 - x1, y2 - y1), area=int(mask.sum()), source=source, color_hint=color_hint)]

    sure_fg = (distance_map > 0.5 * float(distance_map.max())).astype(np.uint8)
    sure_fg = _cleanup_mask(sure_fg, close_size=3, open_size=3, close_iterations=1, open_iterations=1)
    if int(sure_fg.sum()) == 0:
        return [Candidate(mask=mask, bbox=(x1, y1, x2 - x1, y2 - y1), area=int(mask.sum()), source=source, color_hint=color_hint)]

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    unknown = ((cv2.dilate(local_mask, np.ones((3, 3), np.uint8), iterations=2) - sure_fg) > 0).astype(np.uint8)
    markers[unknown == 1] = 0
    watershed = cv2.watershed(image[y1:y2, x1:x2].copy(), markers.astype(np.int32))

    pieces: list[Candidate] = []
    for label in np.unique(watershed):
        if label <= 1:
            continue
        region = (watershed == label).astype(np.uint8)
        if int(region.sum()) < max(1000, int(median_area * 0.45)):
            continue
        full_mask = np.zeros(mask.shape, dtype=np.uint8)
        full_mask[y1:y2, x1:x2] = region
        piece = _candidate_from_mask(full_mask, mask.shape, f"{source}-split", color_hint=color_hint)
        if piece is not None:
            pieces.append(piece)

    return pieces or [Candidate(mask=mask, bbox=(x1, y1, x2 - x1, y2 - y1), area=int(mask.sum()), source=source, color_hint=color_hint)]


def _cleanup_mask(
    mask: np.ndarray,
    *,
    close_size: int,
    open_size: int,
    close_iterations: int,
    open_iterations: int,
) -> np.ndarray:
    close_kernel = np.ones((close_size, close_size), np.uint8)
    open_kernel = np.ones((open_size, open_size), np.uint8)
    cleaned = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, close_kernel, iterations=close_iterations)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, open_kernel, iterations=open_iterations)
    return cleaned


def _odd_kernel(size: int) -> int:
    return size if size % 2 == 1 else size + 1


def _image_border_pixels(image: np.ndarray) -> np.ndarray:
    return np.concatenate([image[0], image[-1], image[:, 0], image[:, -1]], axis=0)


def _sort_candidates(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=lambda candidate: (candidate.bbox[1], candidate.bbox[0]))


def _dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    unique: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.area, reverse=True):
        overlap = max((_mask_iou(candidate.mask, existing.mask) for existing in unique), default=0.0)
        if overlap < 0.3:
            unique.append(candidate)
    return unique


def _mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    intersection = float(np.logical_and(mask_a > 0, mask_b > 0).sum())
    union = float(np.logical_or(mask_a > 0, mask_b > 0).sum())
    if union == 0.0:
        return 0.0
    return intersection / union


def _classify_pick_color(image: np.ndarray, candidate: Candidate) -> str:
    pixels = _candidate_pixels(image, candidate)
    if pixels.size == 0:
        return candidate.color_hint or "white"

    hsv_pixels = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    hue = float(np.median(hsv_pixels[:, 0]))
    saturation = float(np.median(hsv_pixels[:, 1]))
    value = float(np.median(hsv_pixels[:, 2]))

    if value < 80.0 and (saturation < 95.0 or value < 55.0):
        return "black"
    if saturation < 35.0:
        if value < 205.0:
            return "gray"
        return "white"
    if saturation < 75.0 and value > 220.0:
        return "white"
    if saturation < 60.0 and value < 205.0:
        return "gray"
    if hue < 4.0 or hue >= 175.0:
        return "red"
    if hue < 18.0:
        if value < 170.0:
            return "brown"
        return "orange"
    if hue < 38.0:
        return "yellow"
    if hue < 85.0:
        return "green"
    if hue < 102.0:
        return "cyan"
    if hue < 130.0:
        return "blue"
    if hue < 155.0:
        return "purple"
    if value >= 140.0:
        return "pink"
    return "purple"


def _candidate_pixels(image: np.ndarray, candidate: Candidate) -> np.ndarray:
    x, y, w, h = candidate.bbox
    crop = image[y : y + h, x : x + w]
    local_mask = candidate.mask[y : y + h, x : x + w].astype(np.uint8)
    if crop.size == 0 or int(local_mask.sum()) == 0:
        return np.empty((0, 3), dtype=np.uint8)

    core_mask = cv2.erode(local_mask, np.ones((7, 7), np.uint8), iterations=1)
    if int(core_mask.sum()) < 50:
        core_mask = local_mask

    if candidate.color_hint is not None:
        family_mask = _color_family_pixels(crop, candidate.color_hint)
        restricted = ((core_mask > 0) & (family_mask > 0)).astype(np.uint8)
        if int(restricted.sum()) >= 50:
            core_mask = restricted

    return crop[core_mask > 0]


def _color_family_pixels(crop: np.ndarray, color_hint: str) -> np.ndarray:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return _build_color_family_masks(hsv).get(color_hint, np.zeros(crop.shape[:2], dtype=np.uint8))


def _build_color_family_masks(hsv: np.ndarray) -> dict[str, np.ndarray]:
    h_channel, s_channel, v_channel = cv2.split(hsv)
    low_saturation = s_channel < 42
    medium_value = (v_channel >= 80) & (v_channel < 205)
    strong_value = v_channel >= 205

    return {
        "black": ((v_channel < 85) & (s_channel < 120)).astype(np.uint8),
        "gray": (low_saturation & medium_value).astype(np.uint8),
        "white": (low_saturation & strong_value).astype(np.uint8),
        "brown": ((h_channel >= 5) & (h_channel < 18) & (s_channel > 60) & (v_channel >= 45) & (v_channel < 170)).astype(np.uint8),
        "red": (((h_channel <= 4) | (h_channel >= 175)) & (s_channel > 70) & (v_channel > 60)).astype(np.uint8),
        "orange": ((h_channel > 4) & (h_channel < 22) & (s_channel > 70) & (v_channel >= 80)).astype(np.uint8),
        "yellow": ((h_channel >= 18) & (h_channel < 38) & (s_channel > 45) & (v_channel > 80)).astype(np.uint8),
        "green": ((h_channel >= 38) & (h_channel < 85) & (s_channel > 35) & (v_channel > 50)).astype(np.uint8),
        "cyan": ((h_channel >= 85) & (h_channel < 102) & (s_channel > 35) & (v_channel > 50)).astype(np.uint8),
        "blue": ((h_channel >= 102) & (h_channel < 130) & (s_channel > 35) & (v_channel > 50)).astype(np.uint8),
        "purple": ((h_channel >= 130) & (h_channel < 155) & (s_channel > 25) & (v_channel > 50)).astype(np.uint8),
        "pink": ((h_channel >= 155) & (h_channel < 175) & (s_channel > 35) & (v_channel > 100)).astype(np.uint8),
    }


def main() -> None:
    """CLI entry point for the pick-counter script."""
    raise SystemExit(_cli(sys.argv))


def _cli(argv: list[str]) -> int:
    if len(argv) > 2:
        print("Usage: python src/pick_counter.py [image_path]")
        return 1

    if len(argv) == 2:
        counter_picks(argv[1])
    else:
        counter_picks_from_dialog()
    return 0


if __name__ == "__main__":
    main()
