"""Обёртка запуска Tkinter UI с настройкой PYTHONPATH."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toir_manager.ui.desktop import launch  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов для UI и служебных режимов."""

    parser = argparse.ArgumentParser(
        description="Графический интерфейс распределения PDF"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("logs") / "dispatch",
        help="Каталог с JSONL-журналами",
    )
    parser.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Запустить конвейер распределения PDF без UI.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа UI или конвейера в зависимости от аргументов."""

    args = build_parser().parse_args(argv)
    if args.run_pipeline:
        from toir_raspredelenije import main as pipeline_main  # noqa: E402

        pipeline_main()
        return 0
    launch(base_dir=args.base_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
