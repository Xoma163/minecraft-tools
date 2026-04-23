from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AssetView:
    display_name: str
    file_name: str
    url: str
    is_pixelated: bool
