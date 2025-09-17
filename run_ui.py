"""
Простая точка входа для запуска Tkinter UI без настройки PYTHONPATH.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toir_manager.ui.desktop import launch


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов для запуска UI."""

    parser = argparse.ArgumentParser(description="Просмотр журналов распределения PDF")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("logs") / "dispatch",
        help="Каталог с JSONL-журналами",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запустить Tkinter UI."""

    args = build_parser().parse_args(argv)
    launch(base_dir=args.base_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
