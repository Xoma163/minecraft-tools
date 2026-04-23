# minecraft-things

Набор скриптов и systemd unit-файлов для управления Minecraft-сервером.

## Что есть

- `tools/` — start, stop, backup, restore, install deps;
- `services/` — `minecraft.service`, `minecraft-backup.service`, `minecraft-backup.timer`.

## Конфиг

Локальный конфиг: `minecraft.env` в корне проекта.

```bash
cp minecraft.env.example minecraft.env
```

Основные переменные: `MINECRAFT_HOME`, `SERVER_DIR`, `TOOLS_DIR`, `BACKUP_DIR`, `MCRCON_BIN`.

## Быстрый старт

```bash
/opt/minecraft/tools/install_deps.sh
sudo ln -s /opt/minecraft/services/*.service /etc/systemd/system/
sudo ln -s /opt/minecraft/services/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft.service
sudo systemctl enable --now minecraft-backup.timer
```

## Backup

Таймер запускает backup в `03:00`, `09:00`, `15:00`, `21:00`.

## Проверка

Для shell-скриптов рекомендуется `shellcheck`.
