from __future__ import annotations

from pathlib import Path

from toir_manager.services.settings_store import load_ui_paths, save_ui_paths


def test_load_ui_paths_returns_empty_when_file_missing(tmp_path: Path) -> None:
    state = load_ui_paths(config_dir=tmp_path)
    assert state == {}


def test_save_and_load_ui_paths_roundtrip(tmp_path: Path) -> None:
    payload = {
        "TOIR_INBOX_DIR": "C:/data/inbox",
        "TOIR_NOTES_DIR": "C:/data/notes",
    }
    target = save_ui_paths(payload, config_dir=tmp_path)
    assert target.exists()
    restored = load_ui_paths(config_dir=tmp_path)
    assert restored == payload


def test_load_ui_paths_filters_invalid_payload(tmp_path: Path) -> None:
    config_file = tmp_path / "ui_paths.json"
    config_file.write_text('["not", "a", "dict"]', encoding="utf-8")
    state = load_ui_paths(config_dir=tmp_path)
    assert state == {}
