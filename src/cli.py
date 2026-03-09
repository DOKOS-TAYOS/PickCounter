"""CLI entry point for pick-counter."""

from __future__ import annotations

import sys

from .core import counter_picks, counter_picks_from_dialog


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
