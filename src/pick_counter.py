"""Pick counter: count guitar picks in images and export results as JSON.

This module re-exports the public API for backward compatibility.
"""

from __future__ import annotations

from .cli import main
from .core import counter_picks, counter_picks_from_dialog
from .io import choose_image_file

__all__ = ["choose_image_file", "counter_picks", "counter_picks_from_dialog", "main"]

if __name__ == "__main__":
    main()
