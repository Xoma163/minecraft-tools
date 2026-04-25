from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from tools.minecraft_admin.auth import make_admin_dependency
from tools.minecraft_admin.config import load_settings
from tools.minecraft_admin.content import (
    ensure_content_storage,
    guide_excerpt,
    guide_html,
    load_build,
    load_guide_text,
    resolve_build_file,
    save_build,
)
from tools.minecraft_admin.constants import ASSET_ACTION_LABELS
from tools.minecraft_admin.storage import (
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
app = FastAPI(title="Minecraft Admin")
app.state.settings = settings
admin_required = make_admin_dependency(settings)


@app.on_event("startup")
def on_startup() -> None:
    ensure_storage(settings)
    ensure_content_storage(settings)


def common_context(request: Request, current_page: str) -> dict[str, object]:
    build = load_build(settings)
    guide_text = load_guide_text(settings)
    return {
        "request": request,
        "current_page": current_page,
        "max_upload_mb": settings.max_upload_size_bytes // (1024 * 1024),
        "build": build,
        "guide_excerpt": guide_excerpt(guide_text),
    }


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
def dashboard(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    _: None = Depends(admin_required),
):
    skins = collect_assets(settings, "skins")
    capes = collect_assets(settings, "capes")
    images = collect_assets(settings, "images")
    context = common_context(request, "dashboard")
    context.update(
        {
            "message": message,
            "error": error,
            "asset_counts": {
                "skins": len(skins),
                "capes": len(capes),
                "images": len(images),
            },
        }
    )
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@app.get("/assets")
def assets_page(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    _: None = Depends(admin_required),
):
    context = common_context(request, "assets")
    context.update(
        {
            "message": message,
            "error": error,
            "skins": collect_assets(settings, "skins"),
            "capes": collect_assets(settings, "capes"),
            "images": collect_assets(settings, "images"),
        }
    )
    return templates.TemplateResponse(
        request=request,
        name="assets.html",
        context=context,
    )


@app.get("/build")
def build_page(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    _: None = Depends(admin_required),
):
    context = common_context(request, "build")
    context.update({"message": message, "error": error})
    return templates.TemplateResponse(
        request=request,
        name="build.html",
        context=context,
    )


@app.post("/build/upload")
async def upload_build(
    version: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
    _: None = Depends(admin_required),
):
    try:
        build = await save_build(settings, file, version, notes)
        return RedirectResponse(
            url=f"/build?message={quote(f'Загружена сборка {build.version}')}",
            status_code=303,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/build?error={quote(str(exc.detail))}",
            status_code=303,
        )


@app.get("/build/download")
def download_build(_: None = Depends(admin_required)):
    build_file = resolve_build_file(settings)
    return FileResponse(build_file, filename=build_file.name)


@app.get("/guide")
def guide_page(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    _: None = Depends(admin_required),
):
    guide_text = load_guide_text(settings)
    context = common_context(request, "guide")
    context.update(
        {
            "message": message,
            "error": error,
            "guide_text": guide_text,
            "guide_html": guide_html(guide_text),
        }
    )
    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context=context,
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
            url=f"/assets?message={quote(message_text)}",
            status_code=303,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/assets?error={quote(str(exc.detail))}",
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
            url=f"/assets?message={quote(message_text)}",
            status_code=303,
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/assets?error={quote(str(exc.detail))}",
            status_code=303,
        )
