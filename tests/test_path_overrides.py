from __future__ import annotations

import importlib
import sys
from pathlib import Path
from datetime import datetime

from toir_manager.core.logging_models import (
    TransferAction,
    TransferLogEntry,
    TransferStatus,
)
from toir_manager.ui.desktop import _collect_processed_projects

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


def test_collect_processed_projects(tmp_path):
    """Папки с ошибками или из других каталогов не попадают в очистку."""

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    project_ok = inbox / "project_ok"
    project_ok.mkdir()
    project_fail = inbox / "project_fail"
    project_fail.mkdir()

    other_inbox = tmp_path / "other"
    other_project = other_inbox / "project_other"

    timestamp = datetime(2025, 1, 1, 0, 0, 0)

    entries = [
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_DESTINATION,
            status=TransferStatus.SUCCESS,
            source_path=project_ok / "file1.pdf",
            target_path=project_ok / "dest.pdf",
        ),
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_GST,
            status=TransferStatus.SUCCESS,
            source_path=project_ok / "file2.pdf",
            target_path=project_ok / "gst.pdf",
        ),
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_NOTES,
            status=TransferStatus.SUCCESS,
            source_path=project_fail / "file.pdf",
            target_path=project_fail / "notes.pdf",
        ),
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_NOTES,
            status=TransferStatus.ERROR,
            source_path=project_fail / "file.pdf",
            target_path=project_fail / "notes.pdf",
            message="fail",
        ),
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_DESTINATION,
            status=TransferStatus.SUCCESS,
            source_path=other_project / "file.pdf",
            target_path=other_project / "dest.pdf",
        ),
        TransferLogEntry(
            timestamp=timestamp,
            run_id="run",
            action=TransferAction.COPY_DESTINATION,
            status=TransferStatus.SUCCESS,
            source_path=(inbox / "missing") / "file.pdf",
            target_path=None,
        ),
    ]

    result = _collect_processed_projects(entries, inbox)
    assert result == [project_ok.resolve()]
