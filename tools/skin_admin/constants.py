PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GIF_SIGNATURES = (b"GIF87a", b"GIF89a")

SKINS_PUBLIC_PATH = "/skins"
CAPES_PUBLIC_PATH = "/capes"
GIFS_PUBLIC_PATH = "/gifs"

ASSET_EXTENSIONS = {
    "skins": ".png",
    "capes": ".png",
    "gifs": ".gif",
}

ASSET_PUBLIC_PATHS = {
    "skins": SKINS_PUBLIC_PATH,
    "capes": CAPES_PUBLIC_PATH,
    "gifs": GIFS_PUBLIC_PATH,
}

ASSET_ACTION_LABELS = {
    "skins": {"upload": "Загружен скин", "delete": "Удалён скин"},
    "capes": {"upload": "Загружен плащ", "delete": "Удалён плащ"},
    "gifs": {"upload": "Загружена гифка", "delete": "Удалена гифка"},
}
