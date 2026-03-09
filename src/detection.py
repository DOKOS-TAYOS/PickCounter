"""Pick detection logic for clear and textured backgrounds."""

from __future__ import annotations

import cv2
import numpy as np

from .config import GRABCUT_ITERATIONS
from .models import Candidate


def detect_picks(image: np.ndarray) -> list[Candidate]:
    """Detect pick candidates in an image."""
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
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    palette_candidates = _detect_textured_palette_candidates(image, hsv)
    grabcut_mask = _build_textured_grabcut_mask(image, hsv, lab)
    grabcut_candidates = _extract_candidates_from_mask(grabcut_mask, "textured-grabcut")

    if not palette_candidates:
        return grabcut_candidates

    combined = list(palette_candidates)
    for candidate in grabcut_candidates:
        overlap = max((_mask_iou(candidate.mask, existing.mask) for existing in combined), default=0.0)
        if overlap < 0.15:
            combined.append(candidate)
    return combined


def _build_textured_grabcut_mask(
    image: np.ndarray,
    hsv: np.ndarray,
    lab: np.ndarray,
) -> np.ndarray:
    h, w = image.shape[:2]
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
        cv2.grabCut(image, mask, None, background_model, foreground_model, GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return np.zeros((h, w), dtype=np.uint8)

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    return _cleanup_mask(fg_mask, close_size=9, open_size=5, close_iterations=2, open_iterations=1)


def _detect_textured_palette_candidates(image: np.ndarray, hsv: np.ndarray) -> list[Candidate]:
    from .classification import build_color_family_masks

    family_masks = build_color_family_masks(hsv)

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


def _bbox_iou(bbox_a: tuple[int, int, int, int], bbox_b: tuple[int, int, int, int]) -> float:
    """Fast bbox IoU; returns 0 if bboxes do not overlap."""
    x1, y1, w1, h1 = bbox_a
    x2, y2, w2, h2 = bbox_b
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0.0


def _dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    unique: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.area, reverse=True):
        overlap = 0.0
        for existing in unique:
            if _bbox_iou(candidate.bbox, existing.bbox) < 0.1:
                continue
            overlap = max(overlap, _mask_iou(candidate.mask, existing.mask))
        if overlap < 0.3:
            unique.append(candidate)
    return unique


def _mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    intersection = float(np.logical_and(mask_a > 0, mask_b > 0).sum())
    union = float(np.logical_or(mask_a > 0, mask_b > 0).sum())
    if union == 0.0:
        return 0.0
    return intersection / union
