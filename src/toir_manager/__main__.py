"""
Главная точка входа для CLI/UI утилит распределения.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from toir_manager.cli import report as report_cli


def build_parser() -> argparse.ArgumentParser:
    """Показать справку по доступным командам."""

    parser = argparse.ArgumentParser(description="Инструменты ТОиР")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("report", help="Показать журналы в консоли")
    ui_parser = subparsers.add_parser("ui", help="Запустить десктопный просмотрщик")
    ui_parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("logs") / "dispatch",
        help="Каталог с журналами",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Основная точка входа."""

    argv = list(argv or sys.argv[1:])
    if not argv:
        build_parser().print_help(sys.stderr)
        return 1

    command = argv[0]
    if command == "report":
        return report_cli.main(argv=argv[1:])

    if command == "ui":
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "--base-dir",
            type=Path,
            default=Path("logs") / "dispatch",
        )
        args = parser.parse_args(argv[1:])
        if os.environ.get("APP_HEADLESS") == "1":
            raise RuntimeError("GUI запрещён при APP_HEADLESS=1")
        from toir_manager.ui import (
            desktop as desktop_ui,
        )  # локальный импорт, чтобы не требовать PySimpleGUI для CLI

        desktop_ui.launch(base_dir=args.base_dir)
        return 0

    print(f"Неизвестная команда: {command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
