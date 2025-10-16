"""
Сервисы для записи и чтения журналов копирования.
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from toir_manager.core.logging_models import (
    TransferAction,
    TransferLogEntry,
    TransferStatus,
)


class DispatchLogger(AbstractContextManager["DispatchLogger"]):
    """Потокобезопасный писатель JSONL-журнала."""

    def __init__(
        self,
        base_dir: Path | None = None,
        run_id: str | None = None,
    ) -> None:
        env_override = os.environ.get("TOIR_DISPATCH_DIR")
        if base_dir is not None:
            candidate = Path(base_dir)
        elif env_override:
            candidate = Path(env_override).expanduser()
        else:
            candidate = Path("logs") / "dispatch"
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        self._base_dir = candidate
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._file_path = self._base_dir / f"{self._run_id}.jsonl"
        self._lock = threading.Lock()

    def __enter__(self) -> "DispatchLogger":
        """Вернуть self для использования в with."""

        return self

    @property
    def run_id(self) -> str:
        """Вернуть идентификатор текущего запуска."""

        return self._run_id

    @property
    def file_path(self) -> Path:
        """Вернуть путь к файлу журнала."""

        return self._file_path

    def log(
        self,
        *,
        action: TransferAction,
        status: TransferStatus,
        source_path: Path,
        target_path: Path | None,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Записать одну строку в журнал."""

        entry = TransferLogEntry(
            timestamp=datetime.now(),
            run_id=self._run_id,
            action=action,
            status=status,
            source_path=source_path,
            target_path=target_path,
            message=message,
            metadata=metadata or {},
        )

        payload = json.dumps(entry.to_json_compatible(), ensure_ascii=False)
        with self._lock:
            with self._file_path.open("a", encoding="utf-8") as handler:
                handler.write(payload)
                handler.write("\n")

    def log_success(
        self,
        *,
        action: TransferAction,
        source_path: Path,
        target_path: Path | None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Сокращённая запись успешной операции."""

        self.log(
            action=action,
            status=TransferStatus.SUCCESS,
            source_path=source_path,
            target_path=target_path,
            metadata=metadata,
        )

    def log_error(
        self,
        *,
        action: TransferAction,
        source_path: Path,
        target_path: Path | None,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Сокращённая запись ошибки."""

        self.log(
            action=action,
            status=TransferStatus.ERROR,
            source_path=source_path,
            target_path=target_path,
            message=message,
            metadata=metadata,
        )

    def __exit__(self, *_exc: object) -> Optional[bool]:
        """Контекстный менеджер для совместимости."""

        return None


def iter_logs(base_dir: Path | None = None) -> Iterator[TransferLogEntry]:
    """Итерироваться по всем JSONL-журналам в хронологическом порядке."""

    root = (base_dir or Path("logs") / "dispatch").resolve()
    if not root.exists():
        return iter(())

    files = sorted(root.glob("*.jsonl"))

    def generator() -> Iterator[TransferLogEntry]:
        for file_path in files:
            with file_path.open(encoding="utf-8") as handler:
                for line in handler:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield TransferLogEntry.from_json(payload)

    return generator()


def iter_run_logs(
    run_id: str, base_dir: Path | None = None
) -> Iterator[TransferLogEntry]:
    """Вернуть итератор по конкретному файлу запуска."""

    root = (base_dir or Path("logs") / "dispatch").resolve()
    file_path = root / f"{run_id}.jsonl"
    if not file_path.exists():
        return iter(())

    def generator() -> Iterator[TransferLogEntry]:
        with file_path.open(encoding="utf-8") as handler:
            for line in handler:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield TransferLogEntry.from_json(payload)

    return generator()


__all__ = [
    "DispatchLogger",
    "iter_logs",
    "iter_run_logs",
]
