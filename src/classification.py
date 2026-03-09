"""Color classification for detected picks."""

from __future__ import annotations

import cv2
import numpy as np

from .models import Candidate


def build_color_family_masks(hsv: np.ndarray) -> dict[str, np.ndarray]:
    """Build per-color masks from HSV image for palette-based detection."""
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


def classify_pick_color(image: np.ndarray, candidate: Candidate) -> str:
    """Classify the color of a pick candidate based on its pixels."""
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
    return build_color_family_masks(hsv).get(color_hint, np.zeros(crop.shape[:2], dtype=np.uint8))
