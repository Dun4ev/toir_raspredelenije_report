from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

DEFAULT_SUBDIR = ".toir_manager"
DEFAULT_FILENAME = "ui_paths.json"
ENV_CONFIG_DIR = "TOIR_UI_CONFIG_DIR"
ENV_CONFIG_FILE = "TOIR_UI_CONFIG_FILE"


def _resolve_config_path(
    *,
    config_dir: Path | None = None,
    config_file: Path | None = None,
) -> Path:
    """Определить полный путь к файлу настроек UI."""

    if config_file is not None:
        return Path(config_file)
    env_file = os.getenv(ENV_CONFIG_FILE)
    if env_file:
        return Path(env_file)
    directory = config_dir or Path(os.getenv(ENV_CONFIG_DIR, ""))
    if not directory:
        directory = Path.home() / DEFAULT_SUBDIR
    return Path(directory) / DEFAULT_FILENAME


def load_ui_paths(
    *, config_dir: Path | None = None, config_file: Path | None = None
) -> dict[str, str]:
    """Прочитать сохранённые пути для UI."""

    target = _resolve_config_path(config_dir=config_dir, config_file=config_file)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            result[key] = value
    return result


def save_ui_paths(
    paths: Mapping[str, str],
    *,
    config_dir: Path | None = None,
    config_file: Path | None = None,
) -> Path:
    """Сохранить пути, выбранные пользователем, в JSON-файл."""

    target = _resolve_config_path(config_dir=config_dir, config_file=config_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {key: value for key, value in paths.items() if isinstance(key, str)}
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target
