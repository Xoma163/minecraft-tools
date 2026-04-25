from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from tools.minecraft_admin.config import Settings
from tools.minecraft_admin.constants import (
    ASSET_EXTENSIONS,
    ASSET_PUBLIC_PATHS,
)
from tools.minecraft_admin.models import AssetView


def asset_directories(settings: Settings) -> dict[str, Path]:
    return {
        "skins": settings.skins_dir,
        "capes": settings.capes_dir,
        "images": settings.images_dir,
    }


def ensure_storage(settings: Settings) -> None:
    legacy_gifs_dir = settings.data_dir / "gifs"
    if legacy_gifs_dir.exists() and not settings.images_dir.exists():
        legacy_gifs_dir.rename(settings.images_dir)

    settings.skins_dir.mkdir(parents=True, exist_ok=True)
    settings.capes_dir.mkdir(parents=True, exist_ok=True)
    settings.images_dir.mkdir(parents=True, exist_ok=True)
    settings.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings.metadata_path.exists():
        save_metadata(settings, {"skins": {}, "capes": {}, "images": {}})


def normalize_metadata(
    data: dict[str, Any], settings: Settings
) -> dict[str, dict[str, dict[str, str]]]:
    normalized = dict(data)
    legacy_gifs = normalized.get("gifs")
    if "images" not in normalized and isinstance(legacy_gifs, dict):
        normalized["images"] = legacy_gifs

    for kind in asset_directories(settings):
        value = normalized.get(kind)
        normalized[kind] = value if isinstance(value, dict) else {}
    normalized.pop("gifs", None)
    return normalized


def load_metadata(settings: Settings) -> dict[str, dict[str, dict[str, str]]]:
    ensure_storage(settings)
    try:
        return normalize_metadata(
            json.loads(settings.metadata_path.read_text(encoding="utf-8")), settings
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Metadata file is invalid JSON: {settings.metadata_path}"
        ) from exc


def save_metadata(settings: Settings, data: dict[str, Any]) -> None:
    normalized = normalize_metadata(data, settings)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=settings.metadata_path.parent, delete=False
    ) as tmp_file:
        json.dump(normalized, tmp_file, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path = Path(tmp_file.name)
    temp_path.replace(settings.metadata_path)


def normalize_name(name: str) -> str:
    cleaned = Path(name).stem.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Имя файла пустое.")
    if any(ch in cleaned for ch in "\\/"):
        raise HTTPException(
            status_code=400, detail="Имя файла содержит недопустимые символы."
        )
    return cleaned


def candidate_rank(stem: str) -> tuple[int, str]:
    if stem != stem.lower() and stem != stem[:1].upper() + stem[1:].lower():
        return 0, stem
    if stem == stem[:1].upper() + stem[1:].lower() and stem != stem.lower():
        return 1, stem
    return 2, stem


def read_image_dimensions(file_path: Path, kind: str) -> tuple[int, int]:
    try:
        with Image.open(file_path) as image:
            return image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Invalid image file: {file_path}") from exc


def format_image_dimensions(width: int, height: int) -> str:
    return f"{width} × {height}"


def collect_assets(settings: Settings, kind: str) -> list[AssetView]:
    directory = asset_directories(settings)[kind]
    public_path = ASSET_PUBLIC_PATHS[kind]
    extensions = ASSET_EXTENSIONS[kind]
    metadata = load_metadata(settings).get(kind, {})
    grouped: dict[str, list[str]] = {}

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            grouped.setdefault(file_path.stem.lower(), []).append(file_path.name)

    assets: list[AssetView] = []
    for normalized_key, files in grouped.items():
        meta_entry = metadata.get(normalized_key)
        if meta_entry and meta_entry.get("original_file") in files:
            file_name = meta_entry["original_file"]
            display_name = meta_entry["original_name"]
        else:
            file_name = min(
                files,
                key=lambda item: (
                    candidate_rank(Path(item).stem),
                    extensions.index(Path(item).suffix.lower()),
                    item.lower(),
                ),
            )
            display_name = Path(file_name).stem

        width, height = read_image_dimensions(directory / file_name, kind)

        assets.append(
            AssetView(
                display_name=display_name,
                file_name=file_name,
                size_label=format_image_dimensions(width, height),
                url=f"{public_path.rstrip('/')}/{file_name}",
                is_pixelated=kind in {"skins", "capes"},
            )
        )

    return sorted(assets, key=lambda item: item.display_name.lower())


async def read_asset_content(
    settings: Settings, kind: str, upload: UploadFile
) -> tuple[bytes, str]:
    extensions = ASSET_EXTENSIONS[kind]
    file_extension = Path(upload.filename or "").suffix.lower()
    if file_extension not in extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Поддерживаются только файлы: {', '.join(ext.upper() for ext in extensions)}.",
        )

    content = await upload.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Файл слишком большой. Максимум {settings.max_upload_size_bytes // (1024 * 1024)} МБ.",
        )
    return content, file_extension


def upsert_metadata(settings: Settings, kind: str, original_name: str) -> None:
    extensions = ASSET_EXTENSIONS[kind]
    data = load_metadata(settings)
    directory = asset_directories(settings)[kind]
    original_file = next(
        (
            file_path.name
            for file_path in directory.iterdir()
            if file_path.is_file()
            and file_path.stem == original_name
            and file_path.suffix.lower() in extensions
        ),
        f"{original_name}{extensions[0]}",
    )
    data.setdefault(kind, {})[original_name.lower()] = {
        "original_name": original_name,
        "original_file": original_file,
    }
    save_metadata(settings, data)


def delete_asset_files(settings: Settings, kind: str, original_name: str) -> None:
    extensions = ASSET_EXTENSIONS[kind]
    directory = asset_directories(settings)[kind]
    data = load_metadata(settings)
    normalized_key = original_name.lower()
    meta_entry = data.setdefault(kind, {}).get(normalized_key)

    if meta_entry:
        original_file = directory / meta_entry["original_file"]
        if original_file.exists():
            original_file.unlink()

    for file_path in directory.iterdir():
        if (
            file_path.is_file()
            and file_path.suffix.lower() in extensions
            and file_path.stem.lower() == normalized_key
            and file_path.exists()
        ):
            file_path.unlink()

    data.setdefault(kind, {}).pop(normalized_key, None)
    save_metadata(settings, data)


def save_asset(
    settings: Settings,
    kind: str,
    original_name: str,
    content: bytes,
    file_extension: str,
) -> None:
    directory = asset_directories(settings)[kind]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{original_name}{file_extension}").write_bytes(content)


def resolve_asset_file(settings: Settings, kind: str, requested_file: str) -> Path:
    extensions = ASSET_EXTENSIONS[kind]
    directory = asset_directories(settings)[kind]
    requested_path = Path(requested_file)

    if requested_path.suffix:
        if requested_path.suffix.lower() not in extensions:
            raise HTTPException(status_code=404, detail="Файл не найден.")
        normalized_key = requested_path.stem.lower()
    elif kind in {"skins", "capes"}:
        normalized_key = requested_path.name.lower()
    else:
        raise HTTPException(status_code=404, detail="Файл не найден.")

    metadata = load_metadata(settings).get(kind, {})
    meta_entry = metadata.get(normalized_key)

    if meta_entry:
        resolved = directory / meta_entry["original_file"]
        if resolved.exists():
            return resolved

    candidates = [
        file_path
        for file_path in directory.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower() in extensions
        and file_path.stem.lower() == normalized_key
    ]
    if candidates:
        return min(
            candidates,
            key=lambda item: (
                candidate_rank(item.stem),
                extensions.index(item.suffix.lower()),
                item.name.lower(),
            ),
        )

    raise HTTPException(status_code=404, detail="Файл не найден.")
