from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "toir_raspredelenije.py"


def _load_pipeline_module():
    spec = importlib.util.spec_from_file_location("toir_raspredelenije", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load toir_raspredelenije")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_project(tmp_path: Path, filename: str) -> Path:
    project_dir = tmp_path / filename.replace(".pdf", "")
    project_dir.mkdir()
    pdf_path = project_dir / filename
    pdf_path.write_text("pdf", encoding="utf-8")
    return project_dir


def test_process_project_folder_skips_when_all_flags_disabled(tmp_path, monkeypatch):
    module = _load_pipeline_module()

    notes_dir = tmp_path / "notes"
    gst_dir = tmp_path / "gst"
    tra_sub_dir = tmp_path / "tra_sub"
    dest_root_dir = tmp_path / "dest"
    temp_archive_dir = tmp_path / "temp"

    for path in (notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(module, "TRA_GST_DIR", gst_dir)
    monkeypatch.setattr(module, "TRA_SUB_APP_DIR", tra_sub_dir)
    monkeypatch.setattr(module, "DEST_ROOT_DIR", dest_root_dir)
    monkeypatch.setattr(module, "TEMP_ARCHIVE_DIR", temp_archive_dir)
    monkeypatch.setattr(module, "LOGGER", None)

    monkeypatch.setenv("TOIR_ENABLE_NOTES", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_GST", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_SUB_APP", "0")
    monkeypatch.setenv("TOIR_ENABLE_DEST_ROOT", "0")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf",
    )

    module.process_project_folder(project_dir)

    assert not any(notes_dir.iterdir())
    assert not any(gst_dir.iterdir())
    assert not any(tra_sub_dir.iterdir())
    assert not any(dest_root_dir.rglob("*"))


def test_process_project_folder_skips_tra_sub_app_when_disabled(tmp_path, monkeypatch):
    module = _load_pipeline_module()

    notes_dir = tmp_path / "notes"
    gst_dir = tmp_path / "gst"
    tra_sub_dir = tmp_path / "tra_sub"
    dest_root_dir = tmp_path / "dest"
    temp_archive_dir = tmp_path / "temp"

    for path in (notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(module, "TRA_GST_DIR", gst_dir)
    monkeypatch.setattr(module, "TRA_SUB_APP_DIR", tra_sub_dir)
    monkeypatch.setattr(module, "DEST_ROOT_DIR", dest_root_dir)
    monkeypatch.setattr(module, "TEMP_ARCHIVE_DIR", temp_archive_dir)
    monkeypatch.setattr(module, "LOGGER", None)

    monkeypatch.setenv("TOIR_ENABLE_TRA_SUB_APP", "0")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf",
    )

    module.process_project_folder(project_dir)

    pdf_name = "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf"

    assert not any(tra_sub_dir.iterdir())
    assert (notes_dir / pdf_name).exists()
    assert any(dest_root_dir.rglob(pdf_name))


def test_find_project_folders_detects_nested_inbox(tmp_path):
    module = _load_pipeline_module()

    inbox_dir = tmp_path / "inbox"
    direct_dir = inbox_dir / "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00"
    nested_dir = inbox_dir / "outer" / "inner"

    direct_dir.mkdir(parents=True)
    nested_dir.mkdir(parents=True)

    (direct_dir / "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf").write_text(
        "pdf",
        encoding="utf-8",
    )
    (nested_dir / "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf").write_text(
        "pdf",
        encoding="utf-8",
    )

    result = module.find_project_folders(inbox_dir)

    assert set(result) == {direct_dir, nested_dir}


def _prepare_distribution_context(module, tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    gst_dir = tmp_path / "gst"
    tra_sub_dir = tmp_path / "tra_sub"
    dest_root_dir = tmp_path / "dest"
    temp_archive_dir = tmp_path / "temp"

    for path in (notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(module, "TRA_GST_DIR", gst_dir)
    monkeypatch.setattr(module, "TRA_SUB_APP_DIR", tra_sub_dir)
    monkeypatch.setattr(module, "DEST_ROOT_DIR", dest_root_dir)
    monkeypatch.setattr(module, "TEMP_ARCHIVE_DIR", temp_archive_dir)
    monkeypatch.setattr(module, "LOGGER", None)

    return notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir


def test_process_project_folder_skips_when_part_filter_mismatch(tmp_path, monkeypatch):
    module = _load_pipeline_module()
    notes_dir, gst_dir, tra_sub_dir, dest_root_dir, _ = _prepare_distribution_context(
        module, tmp_path, monkeypatch
    )

    monkeypatch.setenv("TOIR_PART_FILTER", "LP")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-CS-UNIT-I.1.1-00-C-20250101-00_All.pdf",
    )

    module.process_project_folder(project_dir)

    assert not any(notes_dir.iterdir())
    assert not any(gst_dir.iterdir())
    assert not any(tra_sub_dir.iterdir())
    assert not any(dest_root_dir.rglob("*_All.pdf"))


def test_process_project_folder_allows_matching_part_filter(tmp_path, monkeypatch):
    module = _load_pipeline_module()
    notes_dir, gst_dir, tra_sub_dir, dest_root_dir, _ = _prepare_distribution_context(
        module, tmp_path, monkeypatch
    )

    monkeypatch.setenv("TOIR_PART_FILTER", "LP")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf",
    )

    module.process_project_folder(project_dir)

    pdf_name = "CT-DR-B-LP-UNIT-I.1.1-00-C-20250101-00_All.pdf"

    assert (notes_dir / pdf_name).exists()
    assert any(dest_root_dir.rglob(pdf_name))


def test_process_project_folder_creates_cs_destination_from_defaults(
    tmp_path, monkeypatch
):
    module = _load_pipeline_module()

    notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir = (
        _prepare_distribution_context(module, tmp_path, monkeypatch)
    )

    monkeypatch.setenv("TOIR_ENABLE_NOTES", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_GST", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_SUB_APP", "0")
    monkeypatch.setenv("TOIR_ENABLE_DEST_ROOT", "1")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-CS-GCU3-II.18.2-00-1M-20250817-00_All.pdf",
    )

    module.process_project_folder(project_dir)

    pdf_name = "CT-DR-B-CS-GCU3-II.18.2-00-1M-20250817-00_All.pdf"
    base_path = dest_root_dir / "2025" / "08.August" / "CS"
    pdf_dir = base_path / "pdf" / "II.18_UPS"
    native_dir = base_path / "Native" / "II.18_UPS"
    assert (pdf_dir / pdf_name).exists()
    assert native_dir.exists()
    assert (native_dir / f"{project_dir.name}.zip").exists()


def test_process_project_folder_uses_weekly_folder_for_cyrillic_period(
    tmp_path, monkeypatch
):
    module = _load_pipeline_module()

    notes_dir, gst_dir, tra_sub_dir, dest_root_dir, temp_archive_dir = (
        _prepare_distribution_context(module, tmp_path, monkeypatch)
    )

    monkeypatch.setenv("TOIR_ENABLE_NOTES", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_GST", "0")
    monkeypatch.setenv("TOIR_ENABLE_TRA_SUB_APP", "0")
    monkeypatch.setenv("TOIR_ENABLE_DEST_ROOT", "1")

    project_dir = _make_project(
        tmp_path,
        "CT-DR-B-CS-ES-II.2.6-00-С-20250812-02_All.pdf",
    )

    module.process_project_folder(project_dir)

    original_pdf_name = "CT-DR-B-CS-ES-II.2.6-00-С-20250812-02_All.pdf"
    pdf_name = (
        module._transliterate_text(Path(original_pdf_name).stem)
        + Path(original_pdf_name).suffix.lower()
    )
    base_path = dest_root_dir / "2025" / "08.August" / "CS"
    pdf_parent = base_path / "pdf"
    native_parent = base_path / "Native"
    folder_names = {item.name for item in pdf_parent.iterdir()}
    target_folder = (
        "Корректирующее обслуживание"
        if "Корректирующее обслуживание" in folder_names
        else "Корректирующееобслуживание"
    )
    pdf_dir = pdf_parent / target_folder
    native_dir = native_parent / target_folder
    assert (pdf_dir / pdf_name).exists()
    assert native_dir.exists()
    expected_archive = module._transliterate_text(project_dir.name) + ".zip"
    assert (native_dir / expected_archive).exists()
