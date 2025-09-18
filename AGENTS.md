# Repository Guidelines

## Project Structure & Module Organization
Core processing lives in `toir_raspredelenije.py`, which orchestrates PDF classification and dispatch. Tkinter UI helpers are under `src/toir_manager/ui/`, CLI tools in `src/toir_manager/cli/`, and shared logic in `src/toir_manager/core/` and `src/toir_manager/services/`. Test suites reside in `tests/`. Configuration artefacts (templates, logs) sit in `Template/` and `logs/dispatch/`. Keep new modules inside the existing `src/toir_manager/<layer>` hierarchy to preserve clean boundaries.

## Build, Test, and Development Commands
Use `python -m venv .venv` followed by `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix) to bootstrap a virtualenv. Install dependencies with `pip install -r requirements.txt` (regenerate via `pip-compile requirements.in` when pinning changes). Run batch processing with `python toir_raspredelenije.py` (override inbox via `TOIR_INBOX_DIR`). Start the desktop UI using `python run_ui.py --base-dir logs/dispatch`. Launch the JSON summary CLI by `python -m toir_manager report --base-dir logs/dispatch --json`.

## Coding Style & Naming Conventions
Target Python 3.10+. Format with `black` (4-space indents, 100-char line cap) and lint with `ruff`. Enforce typing on public functions. Use English identifiers; Russian comments/docstrings are acceptable. Follow existing naming: directories in ALL_CAPS for root paths, camel-case keys only when mirroring external specs.

## Testing Guidelines
Pytest is the test runner (`python -m pytest -q`). Place scenario-specific fixtures in `tests/conftest.py`. Name new tests `test_<module>_<behavior>`. Aim for coverage of critical routing logic (note routing, TRA folders) before refactoring pipelines.

## Commit & Pull Request Guidelines
Use `type: summary` commit messages (`fix: guard log pruning`). For PRs, describe the scenario, affected layers, validation commands (`pytest`, `ruff`), and attach UI screenshots when modifying `desktop.py`. Link tracker tickets where applicable.

## Security & Configuration Tips
Never hardcode credentials or production paths. All configurable directories must stay overridable via environment variables (`TOIR_*`). Validate external input (filenames, spreadsheets) before use and log anomalies for auditing.
