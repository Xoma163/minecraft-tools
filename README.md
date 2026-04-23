# minecraft-things

Набор скриптов, systemd unit-файлов и маленьких сервисов для управления Minecraft-сервером.

## Что есть

- `tools/` — start, stop, backup, restore, install deps;
- `services/` — systemd unit-файлы;
- `tools/skin_admin/` — FastAPI-админка скинов.

## Конфиг

Локальный конфиг сервера: `minecraft.env` в корне проекта.

```bash
cp minecraft.env.example minecraft.env
```

Основные переменные: `MINECRAFT_HOME`, `SERVER_DIR`, `TOOLS_DIR`, `BACKUP_DIR`, `MCRCON_BIN`, `SKIN_ADMIN_DATA_DIR`.

## Быстрый старт

```bash
/opt/minecraft/tools/install_deps.sh
sudo ln -s /opt/minecraft/services/*.service /etc/systemd/system/
sudo ln -s /opt/minecraft/services/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft.service
sudo systemctl enable --now minecraft-backup.timer
```

## Skin admin

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
source ./minecraft.env
set +a
uv run uvicorn tools.skin_admin.app:app --reload --port 8010
```

Локально админка будет доступна на `/`.

Важно: `SKIN_ADMIN_DATA_DIR` обязателен. Без него приложение не стартует.

### Переменные окружения

- `SKIN_ADMIN_DATA_DIR` — корневая папка, внутри которой приложение использует:
  - `skins/`
  - `capes/`
  - `gifs/`
  - `skin_admin_metadata.json`
- `SKIN_ADMIN_USERNAME` — логин для админки;
- `SKIN_ADMIN_PASSWORD` — пароль для админки.

В боевом окружении удобно держать это в `minecraft.env`, например:

```bash
SKIN_ADMIN_DATA_DIR=$MINECRAFT_HOME/data/skin_admin
SKIN_ADMIN_USERNAME=change-me
SKIN_ADMIN_PASSWORD=change-me
```

То есть внутри этой папки будут лежать:

- `$SKIN_ADMIN_DATA_DIR/skins/`
- `$SKIN_ADMIN_DATA_DIR/capes/`
- `$SKIN_ADMIN_DATA_DIR/gifs/`
- `$SKIN_ADMIN_DATA_DIR/skin_admin_metadata.json`

Публичные пути в приложении зафиксированы:

- скины: `/skins`
- плащи: `/capes`
- гифки: `/gifs`

### Пример systemd unit

В репозитории есть:

- `services/minecraft-skins-admin.service`
- `tools/start_skin_admin.sh`
- `tools/stop_skin_admin.sh`
- `tools/skin_admin/`

Они устроены по той же схеме, что и остальные сервисы проекта: читают `/opt/minecraft/minecraft.env`, используют `TOOLS_DIR` и запускают приложение через shell-скрипт. Остановка сервиса в `systemd` идёт штатно через сигнал основному `uvicorn`-процессу.

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

- приложение принимает только `.png` для скинов/плащей и `.gif` для GIF;
- максимальный размер одного загружаемого файла — `100 МБ`;
- на диске хранится только оригинальное имя файла, а регистрозависимые варианты обрабатываются на GET через metadata;
- удаление работает по оригинальному имени и заодно чистит старые дубли, если они остались от предыдущей схемы;
- старые файлы без метаданных тоже будут видны в интерфейсе, но отображаемое имя для них определяется best-effort логикой;
- если `SKIN_ADMIN_*` переменные не заданы или metadata повреждена, приложение теперь падает сразу на старте, а не работает в частично сломанном состоянии.

## Backup

Таймер запускает backup в `03:00`, `09:00`, `15:00`, `21:00`.

## Проверка

- для shell-скриптов рекомендуется `shellcheck`;
- для Python-сервиса достаточно поднять `uvicorn` и проверить загрузку/удаление вручную.
