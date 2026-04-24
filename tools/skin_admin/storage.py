from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, UploadFile

from tools.skin_admin.config import Settings
from tools.skin_admin.constants import (
    ASSET_EXTENSIONS,
    ASSET_PUBLIC_PATHS,
    GIF_SIGNATURES,
    PNG_SIGNATURE,
)
from tools.skin_admin.models import AssetView


def asset_directories(settings: Settings) -> dict[str, Path]:
    return {
        "skins": settings.skins_dir,
        "capes": settings.capes_dir,
        "gifs": settings.gifs_dir,
    }


def ensure_storage(settings: Settings) -> None:
    settings.skins_dir.mkdir(parents=True, exist_ok=True)
    settings.capes_dir.mkdir(parents=True, exist_ok=True)
    settings.gifs_dir.mkdir(parents=True, exist_ok=True)
    settings.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings.metadata_path.exists():
        save_metadata(settings, {"skins": {}, "capes": {}, "gifs": {}})


def normalize_metadata(
    data: dict[str, Any], settings: Settings
) -> dict[str, dict[str, dict[str, str]]]:
    normalized = dict(data)
    for kind in asset_directories(settings):
        value = normalized.get(kind)
        normalized[kind] = value if isinstance(value, dict) else {}
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
    header = file_path.read_bytes()[:24]

    if kind in {"skins", "capes"}:
        if len(header) < 24 or not header.startswith(PNG_SIGNATURE):
            raise ValueError(f"Invalid PNG file: {file_path}")
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        return width, height

    if len(header) < 10 or not any(
        header.startswith(signature) for signature in GIF_SIGNATURES
    ):
        raise ValueError(f"Invalid GIF file: {file_path}")
    width = int.from_bytes(header[6:8], "little")
    height = int.from_bytes(header[8:10], "little")
    return width, height


def format_image_dimensions(width: int, height: int) -> str:
    return f"{width} × {height}"


def collect_assets(settings: Settings, kind: str) -> list[AssetView]:
    directory = asset_directories(settings)[kind]
    public_path = ASSET_PUBLIC_PATHS[kind]
    extension = ASSET_EXTENSIONS[kind]
    metadata = load_metadata(settings).get(kind, {})
    grouped: dict[str, list[str]] = {}

    for file_path in directory.glob(f"*{extension}"):
        grouped.setdefault(file_path.stem.lower(), []).append(file_path.name)

    assets: list[AssetView] = []
    for normalized_key, files in grouped.items():
        meta_entry = metadata.get(normalized_key)
        if meta_entry and meta_entry.get("original_file") in files:
            file_name = meta_entry["original_file"]
            display_name = meta_entry["original_name"]
        else:
            file_name = min(files, key=lambda item: candidate_rank(Path(item).stem))
            display_name = Path(file_name).stem

        width, height = read_image_dimensions(directory / file_name, kind)

        assets.append(
            AssetView(
                display_name=display_name,
                file_name=file_name,
                size_label=format_image_dimensions(width, height),
                url=f"{public_path.rstrip('/')}/{file_name}",
                is_pixelated=extension == ".png",
            )
        )

    return sorted(assets, key=lambda item: item.display_name.lower())


async def read_asset_content(
    settings: Settings, kind: str, upload: UploadFile
) -> bytes:
    extension = ASSET_EXTENSIONS[kind]
    if Path(upload.filename or "").suffix.lower() != extension:
        raise HTTPException(
            status_code=400,
            detail=f"Поддерживаются только {extension.upper()}-файлы.",
        )

    content = await upload.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Файл слишком большой. Максимум {settings.max_upload_size_bytes // (1024 * 1024)} МБ.",
        )

    if kind in {"skins", "capes"} and not content.startswith(PNG_SIGNATURE):
        raise HTTPException(status_code=400, detail="Файл не похож на PNG.")
    if kind == "gifs" and not any(
        content.startswith(signature) for signature in GIF_SIGNATURES
    ):
        raise HTTPException(status_code=400, detail="Файл не похож на GIF.")
    return content


def upsert_metadata(settings: Settings, kind: str, original_name: str) -> None:
    extension = ASSET_EXTENSIONS[kind]
    data = load_metadata(settings)
    data.setdefault(kind, {})[original_name.lower()] = {
        "original_name": original_name,
        "original_file": f"{original_name}{extension}",
    }
    save_metadata(settings, data)


def delete_asset_files(settings: Settings, kind: str, original_name: str) -> None:
    extension = ASSET_EXTENSIONS[kind]
    directory = asset_directories(settings)[kind]
    data = load_metadata(settings)
    normalized_key = original_name.lower()
    meta_entry = data.setdefault(kind, {}).get(normalized_key)

    if meta_entry:
        original_file = directory / meta_entry["original_file"]
        if original_file.exists():
            original_file.unlink()

    for file_path in directory.glob(f"*{extension}"):
        if file_path.stem.lower() == normalized_key and file_path.exists():
            file_path.unlink()

    data.setdefault(kind, {}).pop(normalized_key, None)
    save_metadata(settings, data)


def save_asset(
    settings: Settings, kind: str, original_name: str, content: bytes
) -> None:
    extension = ASSET_EXTENSIONS[kind]
    directory = asset_directories(settings)[kind]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{original_name}{extension}").write_bytes(content)


def resolve_asset_file(settings: Settings, kind: str, requested_file: str) -> Path:
    extension = ASSET_EXTENSIONS[kind]
    directory = asset_directories(settings)[kind]
    requested_path = Path(requested_file)
    if requested_path.suffix.lower() != extension:
        raise HTTPException(status_code=404, detail="Файл не найден.")

    normalized_key = requested_path.stem.lower()
    metadata = load_metadata(settings).get(kind, {})
    meta_entry = metadata.get(normalized_key)

    if meta_entry:
        resolved = directory / meta_entry["original_file"]
        if resolved.exists():
            return resolved

    candidates = [
        file_path
        for file_path in directory.glob(f"*{extension}")
        if file_path.stem.lower() == normalized_key
    ]
    if candidates:
        return min(candidates, key=lambda item: candidate_rank(item.stem))

    raise HTTPException(status_code=404, detail="Файл не найден.")
