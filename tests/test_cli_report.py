"""
Тесты для CLI-репорта.
"""

from __future__ import annotations

import json
from pathlib import Path

from toir_manager.cli import report
from toir_manager.core.logging_models import TransferAction
from toir_manager.services.log_writer import DispatchLogger


def test_report_cli_json_output(tmp_path: Path, capsys) -> None:
    """CLI должен выводить корректную статистику в формате JSON."""

    base_dir = tmp_path / "logs"
    with DispatchLogger(base_dir=base_dir) as logger:
        logger.log_success(
            action=TransferAction.COPY_NOTES,
            source_path=tmp_path / "source.pdf",
            target_path=tmp_path / "notes" / "source.pdf",
            metadata={"notes_dir": "notes"},
        )

    exit_code = report.main(["--base-dir", str(base_dir), "--json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out.strip())
    assert data["total"] == 1
    assert data["success"] == 1
    assert data["errors"] == 0
