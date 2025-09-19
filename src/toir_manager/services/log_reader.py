"""
Чтение и агрегация журналов копирования.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from toir_manager.core.logging_models import TransferLogEntry, TransferStatus
from toir_manager.services.log_writer import iter_logs, iter_run_logs


@dataclass(slots=True)
class RunInfo:
    """Метаданные по запуску журнала."""

    run_id: str
    file_path: Path
    started_at: datetime
    total_records: int


def list_runs(base_dir: Path | None = None) -> list[RunInfo]:
    """Собрать сводку по всем запускам."""

    root = (base_dir or Path("logs") / "dispatch").resolve()
    if not root.exists():
        return []

    result: list[RunInfo] = []
    for path in sorted(root.glob("*.jsonl"), reverse=True):
        run_id = path.stem
        first_entry: TransferLogEntry | None = None
        total = 0
        for entry in iter_run_logs(run_id, base_dir=root):
            total += 1
            if first_entry is None:
                first_entry = entry
        if first_entry is None:
            continue
        result.append(
            RunInfo(
                run_id=run_id,
                file_path=path,
                started_at=first_entry.timestamp,
                total_records=total,
            )
        )
    return result


def summarize_entries(entries: Iterable[TransferLogEntry]) -> dict[str, int | float]:
    """Набор агрегатов для отображения в CLI/UI."""

    entries = list(entries)
    total = len(entries)
    status_counter = Counter(entry.status for entry in entries)
    return {
        "total": total,
        "success": status_counter.get(TransferStatus.SUCCESS, 0),
        "errors": status_counter.get(TransferStatus.ERROR, 0),
    }


def iter_all_logs(base_dir: Path | None = None) -> Iterator[TransferLogEntry]:
    """Синоним для экспорта: возвращает все записи."""

    yield from iter_logs(base_dir=base_dir)


__all__ = [
    "RunInfo",
    "iter_all_logs",
    "list_runs",
    "summarize_entries",
]
