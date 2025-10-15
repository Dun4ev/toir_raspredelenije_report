"""Тесты для дополнительной раскладки в каталог 05_TRA_SUB_app."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "toir_raspredelenije.py"
spec = importlib.util.spec_from_file_location("toir_raspredelenije", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Не удалось загрузить модуль toir_raspredelenije")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_process_special_grouping_handles_cyrillic_period(tmp_path, monkeypatch):
    """Убеждаемся, что период с кириллической буквой "С" не требует суффикса."""

    report_path = tmp_path / "sample.pdf"
    report_path.write_text("pdf", encoding="utf-8")

    tra_sub_dir = tmp_path / "05_TRA_SUB_app"
    tra_sub_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "TRA_SUB_APP_DIR", tra_sub_dir)
    monkeypatch.setattr(module, "LOGGER", None)

    data = {
        "tz_index": "II.18.2",
        "reserved": "00",
        "period": "С",
        "date": "20250903",
    }

    module.process_special_grouping_for_sub_app(report_path, data, metadata=None)

    expected_folder = tra_sub_dir / "2025" / "09.September" / "II.18.2-00-С"
    expected_file = expected_folder / report_path.name

    assert expected_folder.is_dir()
    assert expected_file.exists()


def test_process_special_grouping_without_date_falls_back(tmp_path, monkeypatch):
    """Проверяем, что при отсутствии даты создаётся fallback-каталог без годового и месячного уровней."""

    report_path = tmp_path / "fallback.pdf"
    report_path.write_text("pdf", encoding="utf-8")

    tra_sub_dir = tmp_path / "05_TRA_SUB_app"
    tra_sub_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "TRA_SUB_APP_DIR", tra_sub_dir)
    monkeypatch.setattr(module, "LOGGER", None)

    data = {
        "tz_index": "II.18.2",
        "reserved": "00",
        "period": "C",
    }

    module.process_special_grouping_for_sub_app(report_path, data, metadata=None)

    expected_folder = tra_sub_dir / "II.18.2-00-C"
    expected_file = expected_folder / report_path.name

    assert expected_folder.is_dir()
    assert expected_file.exists()
