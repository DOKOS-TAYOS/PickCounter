"""Image I/O, validation, and file dialogs."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import cv2
import numpy as np

from .config import REPO_ROOT, SUPPORTED_EXTENSIONS


def choose_image_file(initial_dir: str | Path | None = None) -> Path:
    """Open a file dialog to select an image file."""
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


def validate_image_path(image_path: Path) -> None:
    """Validate that the path exists and has a supported extension."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")


def read_image(image_path: Path) -> np.ndarray:
    """Read an image from disk into a numpy array (BGR)."""
    raw = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    return image
