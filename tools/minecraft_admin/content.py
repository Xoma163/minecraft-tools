from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, UploadFile
from markdown import markdown

from tools.minecraft_admin.config import Settings
from tools.minecraft_admin.models import BuildView
from tools.minecraft_admin.storage import load_metadata, save_metadata


DEFAULT_GUIDE_TEXT = """# Инструкция по установке

1. Скачайте актуальную сборку на вкладке «Сборка».
2. Установите нужную версию Java.
3. Импортируйте архив в ваш лаунчер.
4. При проблемах обновите Java, проверьте память и переустановите сборку.

Здесь можно хранить вашу реальную инструкцию для игроков.
"""


def ensure_content_storage(settings: Settings) -> None:
    settings.builds_dir.mkdir(parents=True, exist_ok=True)
    settings.current_builds_dir.mkdir(parents=True, exist_ok=True)
    settings.pages_dir.mkdir(parents=True, exist_ok=True)
    if not settings.guide_path.exists():
        settings.guide_path.write_text(DEFAULT_GUIDE_TEXT, encoding="utf-8")


def format_size(size_bytes: int) -> str:
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    value = float(size_bytes)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if value < 1024 or candidate == units[-1]:
            break
        value /= 1024
    precision = 0 if unit == "Б" else 1
    return f"{value:.{precision}f} {unit}"


def load_guide_text(settings: Settings) -> str:
    ensure_content_storage(settings)
    return settings.guide_path.read_text(encoding="utf-8").strip()


def guide_excerpt(text: str, max_lines: int = 4) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    excerpt = lines[:max_lines]
    return "\n".join(excerpt)


def guide_html(text: str) -> str:
    return markdown(text, extensions=["extra", "nl2br", "sane_lists"])


def _build_meta(data: dict) -> dict:
    build = data.get("build")
    return build if isinstance(build, dict) else {}


def load_build(settings: Settings) -> BuildView | None:
    ensure_content_storage(settings)
    metadata = load_metadata(settings)
    build = _build_meta(metadata)
    file_name = build.get("file_name")
    if not isinstance(file_name, str) or not file_name:
        return None

    build_path = settings.current_builds_dir / file_name
    if not build_path.exists():
        return None

    version = (
        build.get("version") if isinstance(build.get("version"), str) else "Без версии"
    )
    notes = build.get("notes") if isinstance(build.get("notes"), str) else ""
    updated_at = (
        build.get("updated_at") if isinstance(build.get("updated_at"), str) else ""
    )
    size_bytes = build_path.stat().st_size
    return BuildView(
        file_name=file_name,
        version=version,
        notes=notes,
        size_bytes=size_bytes,
        size_label=format_size(size_bytes),
        updated_at=updated_at,
        download_url="/build/download",
    )


async def save_build(
    settings: Settings, upload: UploadFile, version: str, notes: str
) -> BuildView:
    ensure_content_storage(settings)

    file_name = Path(upload.filename or "").name.strip()
    if not file_name:
        raise HTTPException(status_code=400, detail="Не выбрали файл сборки.")

    settings.current_builds_dir.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(delete=False, dir=settings.current_builds_dir) as temp_file:
        temp_path = Path(temp_file.name)
        size_bytes = 0
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > settings.max_build_size_bytes:
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Файл сборки слишком большой. "
                        f"Максимум {settings.max_build_size_bytes // (1024 * 1024)} МБ."
                    ),
                )
            temp_file.write(chunk)

    for existing_file in settings.current_builds_dir.iterdir():
        if existing_file.is_file() and existing_file != temp_path:
            existing_file.unlink()

    final_path = settings.current_builds_dir / file_name
    temp_path.replace(final_path)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    metadata = load_metadata(settings)
    metadata["build"] = {
        "file_name": file_name,
        "version": version.strip() or "Без версии",
        "notes": notes.strip(),
        "updated_at": timestamp,
    }
    save_metadata(settings, metadata)

    return BuildView(
        file_name=file_name,
        version=metadata["build"]["version"],
        notes=metadata["build"]["notes"],
        size_bytes=size_bytes,
        size_label=format_size(size_bytes),
        updated_at=timestamp,
        download_url="/build/download",
    )


def resolve_build_file(settings: Settings) -> Path:
    build = load_build(settings)
    if build is None:
        raise HTTPException(status_code=404, detail="Файл сборки не загружен.")
    return settings.current_builds_dir / build.file_name
