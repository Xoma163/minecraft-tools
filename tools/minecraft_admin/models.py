from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AssetView:
    display_name: str
    file_name: str
    size_label: str
    url: str
    is_pixelated: bool


@dataclass(slots=True)
class BuildView:
    file_name: str
    version: str
    notes: str
    size_bytes: int
    size_label: str
    updated_at: str
    download_url: str
