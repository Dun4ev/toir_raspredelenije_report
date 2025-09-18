"""
Юнит-тесты для сервиса журналирования.
"""
from __future__ import annotations

import json
from pathlib import Path

from toir_manager.core.logging_models import TransferAction, TransferStatus
from toir_manager.services.log_reader import list_runs, summarize_entries
from toir_manager.services.log_writer import DispatchLogger, iter_run_logs


def test_dispatch_logger_writes_jsonl(tmp_path: Path) -> None:
    """Проверить запись и чтение JSONL-файла."""

    base_dir = tmp_path / "logs"
    with DispatchLogger(base_dir=base_dir) as logger:
        logger.log_success(
            action=TransferAction.COPY_NOTES,
            source_path=tmp_path / "source.pdf",
            target_path=tmp_path / "notes" / "source.pdf",
            metadata={"notes_dir": "notes"},
        )
        logger.log_error(
            action=TransferAction.COPY_DESTINATION,
            source_path=tmp_path / "source.pdf",
            target_path=tmp_path / "dest" / "source.pdf",
            message="Ошибка тестирования",
            metadata={"destination_path": "dest"},
        )
        run_id = logger.run_id
        log_file = logger.file_path

    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    payload = json.loads(lines[0])
    assert payload["status"] == TransferStatus.SUCCESS.value

    entries = list(iter_run_logs(run_id, base_dir=base_dir))
    assert len(entries) == 2
    assert entries[0].status is TransferStatus.SUCCESS

    runs = list_runs(base_dir=base_dir)
    assert runs and runs[0].total_records == 2

    summary = summarize_entries(entries)
    assert summary == {"total": 2, "success": 1, "errors": 1}
