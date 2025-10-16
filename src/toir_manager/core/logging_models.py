"""
Структуры данных для журналирования операций копирования.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Self


class TransferStatus(str, Enum):
    """Статус выполнения операции копирования."""

    SUCCESS = "success"
    ERROR = "error"


class TransferAction(str, Enum):
    """Тип выполняемого действия в рамках пайплайна."""

    COPY_NOTES = "copy_notes"
    COPY_GST = "copy_gst"
    COPY_DESTINATION = "copy_destination"
    COPY_TRA_SUB = "copy_tra_sub"
    CREATE_ARCHIVE = "create_archive"
    COPY_ARCHIVE = "copy_archive"
    RENAME = "rename"


@dataclass(slots=True)
class TransferLogEntry:
    """Журналируемая запись по одному действию."""

    timestamp: datetime
    run_id: str
    action: TransferAction
    status: TransferStatus
    source_path: Path
    target_path: Path | None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_compatible(self) -> dict[str, Any]:
        """Подготовить сериализуемое представление записи."""

        return {
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "action": self.action.value,
            "status": self.status.value,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path) if self.target_path else None,
            "message": self.message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> Self:
        """Восстановить запись из сериализованного словаря."""

        return cls(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            run_id=payload["run_id"],
            action=TransferAction(payload["action"]),
            status=TransferStatus(payload["status"]),
            source_path=Path(payload["source_path"]),
            target_path=(
                Path(payload["target_path"]) if payload.get("target_path") else None
            ),
            message=payload.get("message", ""),
            metadata=payload.get("metadata", {}),
        )


__all__ = [
    "TransferAction",
    "TransferLogEntry",
    "TransferStatus",
]
