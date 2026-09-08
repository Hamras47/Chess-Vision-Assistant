"""Packaging-safe paths for source checkouts and frozen applications."""
from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
