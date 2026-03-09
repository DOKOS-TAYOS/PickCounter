"""Data models for pick detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Candidate:
    """A detected pick candidate with mask and metadata."""

    mask: np.ndarray
    bbox: tuple[int, int, int, int]
    area: int
    source: str
    color_hint: str | None = None
