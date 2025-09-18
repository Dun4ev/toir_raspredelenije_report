from __future__ import annotations

import importlib
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def test_path_env_overrides(monkeypatch, tmp_path):
    """Проверяет чтение каталогов из переменных окружения."""
    module = importlib.import_module("toir_raspredelenije")
    attr_to_env = {
        "INBOX_DIR": "TOIR_INBOX_DIR",
        "NOTES_DIR": "TOIR_NOTES_DIR",
        "TRA_GST_DIR": "TOIR_TRA_GST_DIR",
        "TRA_SUB_APP_DIR": "TOIR_TRA_SUB_APP_DIR",
        "DEST_ROOT_DIR": "TOIR_DEST_ROOT_DIR",
        "TEMP_ARCHIVE_DIR": "TOIR_TEMP_ARCHIVE_DIR",
    }
    expected: dict[str, Path] = {}
    for attr, env_var in attr_to_env.items():
        target = tmp_path / env_var.lower()
        target.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(env_var, str(target))
        expected[attr] = target.resolve()

    try:
        reloaded = importlib.reload(module)
        for attr, expected_path in expected.items():
            assert getattr(reloaded, attr) == expected_path
    finally:
        for env_var in attr_to_env.values():
            monkeypatch.delenv(env_var, raising=False)
        importlib.reload(module)
