from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from tools.skin_admin.auth import make_admin_dependency
from tools.skin_admin.config import load_settings
from tools.skin_admin.constants import ASSET_ACTION_LABELS
from tools.skin_admin.storage import (
    asset_directories,
    collect_assets,
    delete_asset_files,
    ensure_storage,
    normalize_name,
    read_asset_content,
    resolve_asset_file,
    save_asset,
    upsert_metadata,
)


templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

settings = load_settings()
app = FastAPI(title="Minecraft Skin Admin")
app.state.settings = settings
admin_required = make_admin_dependency(settings)


@app.on_event("startup")
def on_startup() -> None:
    ensure_storage(settings)


@app.get("/skins/{file_name}")
def get_skin(file_name: str):
    return FileResponse(resolve_asset_file(settings, "skins", file_name))


@app.get("/capes/{file_name}")
def get_cape(file_name: str):
    return FileResponse(resolve_asset_file(settings, "capes", file_name))


@app.get("/images/{file_name}")
def get_image(file_name: str):
    return FileResponse(resolve_asset_file(settings, "images", file_name))


@app.get("/gifs/{file_name}")
def get_legacy_gif(file_name: str):
    return FileResponse(resolve_asset_file(settings, "images", file_name))


@app.get("/")
def index(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    _: None = Depends(admin_required),
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "message": message,
            "error": error,
            "skins": collect_assets(settings, "skins"),
            "capes": collect_assets(settings, "capes"),
            "images": collect_assets(settings, "images"),
            "max_upload_mb": settings.max_upload_size_bytes // (1024 * 1024),
        },
    )


@app.post("/upload/{kind}")
async def upload_asset(
    kind: str,
    name: str = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(admin_required),
):
    try:
        if kind not in asset_directories(settings):
            raise HTTPException(status_code=404, detail="Неизвестный тип ассета.")

        original_name = normalize_name(name)
        content, file_extension = await read_asset_content(settings, kind, file)

        save_asset(settings, kind, original_name, content, file_extension)
        upsert_metadata(settings, kind, original_name)
        message_text = f"{ASSET_ACTION_LABELS[kind]['upload']} {original_name}"

        return RedirectResponse(
            url=f"/?message={quote(message_text)}",
            status_code=303,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/?error={quote(str(exc.detail))}",
            status_code=303,
        )


@app.post("/delete/{kind}")
def delete_asset(
    kind: str,
    name: str = Form(...),
    _: None = Depends(admin_required),
):
    try:
        if kind not in asset_directories(settings):
            raise HTTPException(status_code=404, detail="Неизвестный тип ассета.")

        original_name = normalize_name(name)
        delete_asset_files(settings, kind, original_name)
        message_text = f"{ASSET_ACTION_LABELS[kind]['delete']} {original_name}"

        return RedirectResponse(
            url=f"/?message={quote(message_text)}",
            status_code=303,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/?error={quote(str(exc.detail))}",
            status_code=303,
        )
