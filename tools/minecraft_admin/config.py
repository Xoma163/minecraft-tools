from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_BUILD_SIZE_BYTES = 1024 * 1024 * 1024


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value



def required_env_path(name: str) -> Path:
    return Path(required_env(name)).expanduser().resolve()



@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    skins_dir: Path
    capes_dir: Path
    images_dir: Path
    builds_dir: Path
    current_builds_dir: Path
    pages_dir: Path
    guide_path: Path
    metadata_path: Path
    admin_username: str
    admin_password: str
    max_upload_size_bytes: int = MAX_UPLOAD_SIZE_BYTES
    max_build_size_bytes: int = MAX_BUILD_SIZE_BYTES


def load_settings() -> Settings:
    data_dir = required_env(
        "MINECRAFT_ADMIN_DATA_DIR",
    )
    return Settings(
        data_dir=data_dir,
        skins_dir=data_dir / "skins",
        capes_dir=data_dir / "capes",
        images_dir=data_dir / "images",
        builds_dir=data_dir / "builds",
        current_builds_dir=data_dir / "builds" / "current",
        pages_dir=data_dir / "pages",
        guide_path=data_dir / "pages" / "guide.md",
        metadata_path=data_dir / "minecraft_admin_metadata.json",
        admin_username=required_env(
            "MINECRAFT_ADMIN_USERNAME",
        ),
        admin_password=required_env(
            "MINECRAFT_ADMIN_PASSWORD",
        ),
    )
