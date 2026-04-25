SKINS_PUBLIC_PATH = "/skins"
CAPES_PUBLIC_PATH = "/capes"
IMAGES_PUBLIC_PATH = "/images"

ASSET_EXTENSIONS = {
    "skins": (".png",),
    "capes": (".png",),
    "images": (".jpg", ".jpeg", ".png", ".webp", ".gif"),
}

ASSET_PUBLIC_PATHS = {
    "skins": SKINS_PUBLIC_PATH,
    "capes": CAPES_PUBLIC_PATH,
    "images": IMAGES_PUBLIC_PATH,
}

ASSET_ACTION_LABELS = {
    "skins": {"upload": "Загружен скин", "delete": "Удалён скин"},
    "capes": {"upload": "Загружен плащ", "delete": "Удалён плащ"},
    "images": {"upload": "Загружена картинка", "delete": "Удалена картинка"},
}
