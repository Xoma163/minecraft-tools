# minecraft-tools

Набор скриптов, systemd unit-файлов и маленьких сервисов для управления Minecraft-сервером.

## Что есть

- `tools/` — start, stop, backup, restore, install deps;
- `services/` — systemd unit-файлы;
- `tools/minecraft_admin/` — FastAPI-админка для сборки, инструкции и ассетов.

## Конфиг

Локальный конфиг сервера: `.env` в корне проекта.

```bash
cp .env.example .env
```

Основные переменные: `MINECRAFT_HOME`, `SERVER_DIR`, `TOOLS_DIR`, `BACKUP_DIR`, `MCRCON_BIN`, `MINECRAFT_ADMIN_DATA_DIR`.

## Быстрый старт

```bash
/opt/minecraft/tools/install_deps.sh
sudo ln -s /opt/minecraft/services/minecraft.service /etc/systemd/system/
sudo ln -s /opt/minecraft/services/minecraft-admin.service /etc/systemd/system/
sudo ln -s /opt/minecraft/services/minecraft-backup.service /etc/systemd/system/
sudo ln -s /opt/minecraft/services/minecraft-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-admin.service
sudo systemctl enable --now minecraft.service
sudo systemctl enable --now minecraft-backup.timer
```

## Minecraft admin

Админка предназначена для ручного управления файлами, которые потом читает `OfflineSkins`:

- скины: `https://minecraft.andrewsha.net/skins/%name%`
- плащи: `https://minecraft.andrewsha.net/capes/%name%`

Файлы раздаются самим FastAPI-приложением.

Авторизация админки тоже проверяется в FastAPI через HTTP Basic Auth.

### Что умеет

- показать все скины;
- показать все плащи;
- загрузить PNG-файл скина или плаща;
- удалить скин или плащ;
- хранить только один оригинальный PNG-файл;
- по запросу `original`, `Capitalized` или `lowercase` имени всё равно отдавать этот же файл.

В интерфейсе показывается только оригинальное имя.

### Установка зависимостей

```bash
uv sync
```

### Локальный запуск

```bash
set -a
source ./.env
set +a
uv run uvicorn tools.minecraft_admin.app:app --reload --port 8010
```

Локально админка будет доступна на `/`.

Важно: `MINECRAFT_ADMIN_DATA_DIR` обязателен. Без него приложение не стартует.

### Переменные окружения

- `MINECRAFT_ADMIN_DATA_DIR` — корневая папка, внутри которой приложение использует:
  - `skins/`
  - `capes/`
  - `images/`
  - `minecraft_admin_metadata.json`
- `MINECRAFT_ADMIN_USERNAME` — логин для админки;
- `MINECRAFT_ADMIN_PASSWORD` — пароль для админки.

В боевом окружении удобно держать это в `.env`, например:

```bash
MINECRAFT_ADMIN_DATA_DIR=$MINECRAFT_HOME/data/minecraft_admin
MINECRAFT_ADMIN_USERNAME=change-me
MINECRAFT_ADMIN_PASSWORD=change-me
```

То есть внутри этой папки будут лежать:

- `$MINECRAFT_ADMIN_DATA_DIR/skins/`
- `$MINECRAFT_ADMIN_DATA_DIR/capes/`
- `$MINECRAFT_ADMIN_DATA_DIR/images/`
- `$MINECRAFT_ADMIN_DATA_DIR/minecraft_admin_metadata.json`

Публичные пути в приложении зафиксированы:

- скины: `/skins`
- плащи: `/capes`
- картинки: `/images`

### Online Displays

Online Displays adds one block: Display.
It allows setting up an image, positioning, rotating, and scaling it to your exact need so that everyone can see it.
Additionally, its lighting may be disabled, essentially rendering it emissive.
The Display block supports a variety of image formats, such as JPG/JPEG, PNG, WebP, and GIF.
GIFs are partially supported, but you might see weird artifacts on GIFs with specific encoding.

### Пример systemd unit

В репозитории есть:

- `services/minecraft-admin.service`
- `tools/start_minecraft_admin.sh`
- `tools/stop_minecraft_admin.sh`
- `tools/minecraft_admin/`

Они устроены по той же схеме, что и остальные сервисы проекта: `systemd` читает `/opt/minecraft/.env`, а `ExecStart`/`ExecStop` вызывают shell-скрипты напрямую. Сами скрипты уже подгружают `lib.sh` и нужную конфигурацию. Остановка сервиса в `systemd` идёт штатно через сигнал основному `uvicorn`-процессу.

Если `uv` установлен через официальный install script в `~/.local/bin`, добавь этот путь в `PATH` прямо в systemd unit через `Environment=`, чтобы сервисы находили бинарник без login shell.

### Nginx

Готовый конфиг вынесен в отдельный файл:

- `nginx/minecraft.andrewsha.net.conf`

В нём весь трафик просто проксируется в FastAPI, а проверка логина и пароля происходит на бэке.

Его можно положить, например, в:

```bash
sudo ln -s /opt/minecraft/nginx/minecraft.andrewsha.net.conf /etc/nginx/sites-enabled/minecraft.andrewsha.net
sudo nginx -t
sudo systemctl reload nginx
```

### Примечания

- приложение принимает только `.png` для скинов/плащей и `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` для картинок;
- максимальный размер одного загружаемого файла — `10 МБ`;
- на диске хранится только оригинальное имя файла, а регистрозависимые варианты обрабатываются на GET через metadata;
- удаление работает по оригинальному имени и заодно чистит старые дубли, если они остались от предыдущей схемы;
- старые файлы без метаданных тоже будут видны в интерфейсе, но отображаемое имя для них определяется best-effort логикой;
- если `MINECRAFT_ADMIN_*` переменные не заданы или metadata повреждена, приложение теперь падает сразу на старте, а не работает в частично сломанном состоянии.

## Backup

Таймер запускает backup в `03:00`, `09:00`, `15:00`, `21:00`.

## Проверка

- для shell-скриптов рекомендуется `shellcheck`;
- для Python-сервиса достаточно поднять `uvicorn` и проверить загрузку/удаление вручную.
