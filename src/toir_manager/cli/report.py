"""
CLI-команда для чтения журналов копирования PDF.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from toir_manager.services.log_reader import list_runs, summarize_entries
from toir_manager.services.log_writer import iter_run_logs


def build_parser() -> argparse.ArgumentParser:
    """Построить парсер аргументов."""

    parser = argparse.ArgumentParser(
        prog="python -m toir_manager report",
        description="Просмотр журналов распределения PDF",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("logs") / "dispatch",
        help="Каталог, где лежат файлы журналов",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="Показать доступные запуски и выйти",
    )
    parser.add_argument(
        "--run-id",
        help="Идентификатор запуска (имя файла без расширения)",
    )
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Выводить помимо сводки построчные записи",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Печать сводки в формате JSON",
    )
    return parser


def render_runs_table(base_dir: Path) -> int:
    """Вывести список запусков таблицей."""

    runs = list_runs(base_dir=base_dir)
    if not runs:
        print("Журналы не найдены. Запустите основной скрипт и повторите.")
        return 1

    print("Доступные запуски:")
    print("run_id           | started_at          | records | путь")
    print(
        "-----------------+---------------------+---------+---------------------------"
    )
    for info in runs:
        print(
            f"{info.run_id:<16} | {info.started_at:%Y-%m-%d %H:%M:%S} | "
            f"{info.total_records:7d} | {info.file_path}"
        )
    return 0


def render_run_summary(
    base_dir: Path, run_id: str | None, show_details: bool, as_json: bool
) -> int:
    """Вывести суммарную статистику по запуску."""

    if not run_id:
        runs = list_runs(base_dir=base_dir)
        if not runs:
            print("Журналы не найдены. Запустите основной скрипт и повторите.")
            return 1
        run_id = runs[0].run_id

    entries = list(iter_run_logs(run_id, base_dir=base_dir))
    if not entries:
        print(f"Файл журнала для запуска {run_id} пуст или отсутствует.")
        return 1

    summary = summarize_entries(entries)
    if as_json:
        print(json.dumps({"run_id": run_id, **summary}, ensure_ascii=False))
    else:
        print(f"Запуск: {run_id}")
        print(
            "Всего операций: {total}, успехов: {success}, ошибок: {errors}".format(
                total=summary["total"],
                success=summary["success"],
                errors=summary["errors"],
            )
        )

    if show_details:
        print("\nПодробности:")
        for entry in entries:
            target = str(entry.target_path) if entry.target_path else "-"
            print(
                f"[{entry.timestamp:%H:%M:%S}] {entry.action.value:<18} "
                f"{entry.status.value:<7} → {target}"
            )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    base_dir = args.base_dir
    if args.list_runs:
        return render_runs_table(base_dir)

    return render_run_summary(
        base_dir=base_dir,
        run_id=args.run_id,
        show_details=args.show_details,
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
