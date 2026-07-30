from __future__ import annotations

import pytest

from toir_manager.ui.translations import (
    DEFAULT_UI_LANGUAGE,
    LANGUAGE_NAMES,
    UI_TEXT,
    normalize_language,
    translate,
)


def test_all_languages_define_the_same_ui_keys() -> None:
    english_keys = set(UI_TEXT["en"])
    assert english_keys
    assert set(UI_TEXT["ru"]) == english_keys


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, DEFAULT_UI_LANGUAGE),
        ("", DEFAULT_UI_LANGUAGE),
        ("en", "en"),
        ("English", "en"),
        ("RU", "ru"),
        ("Русский", "ru"),
        ("unsupported", DEFAULT_UI_LANGUAGE),
    ],
)
def test_normalize_language(value: str | None, expected: str) -> None:
    assert normalize_language(value) == expected


def test_translate_formats_both_languages() -> None:
    assert translate("en", "folders_deleted", count=3) == "Folders deleted: 3"
    assert translate("ru", "folders_deleted", count=3) == "Удалено папок: 3"
    assert tuple(LANGUAGE_NAMES.values()) == ("English", "Русский")
