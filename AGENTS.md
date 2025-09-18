# Repository Guidelines

## Project Structure & Module Organization
Основной скрипт `toir_raspredelenije.py` управляет разбором и раскладкой PDF. Настроечный файл `Template/TZ_glob.xlsx` используется для подбора суффиксов в `05_TRA_SUB_app`. Результаты раскладываются в дереве `DEST_ROOT_DIR/<год>/<месяц>/{CS,LP}/{pdf,Native}/…`. Интерфейсы и CLI вынесены в пакет `src/toir_manager`, запуск Tkinter-UI — через `run_ui.py`. Тесты живут в `tests/` (unit + CLI). Виртуальное окружение держим в `.venv` и не коммитим.
```
repo/
├─ toir_raspredelenije.py
├─ run_ui.py
├─ src/toir_manager/{core,services,cli,ui}
├─ Template/TZ_glob.xlsx
├─ logs/dispatch/*.jsonl
└─ tests/
```

## Build, Test, and Development Commands
- `python -m venv .venv` и `.venv\Scripts\activate` — подготовка окружения.
- `pip install --upgrade pip` и `pip install openpyxl pytest` — базовые зависимости.
- `python toir_raspredelenije.py` — обработать `INBOX_DIR`; при необходимости задайте `TOIR_INBOX_DIR`.
- `python run_ui.py --base-dir logs/dispatch` — запустить Tkinter UI (вкладки «Распределение» и «Журналы»).
- `python -m toir_manager report --base-dir logs/dispatch --json` — консольный отчёт.
- `pytest -q` — прогон тестов.

## Coding Style & Naming Conventions
Python ≥3.10, PEP8. Отступы 4 пробела, строки ≤100 символов. Докстринги/комментарии — на русском, идентификаторы — латиницей. Все публичные функции типизированы. Форматирование — `black`, линтер — `ruff` (`ruff check --fix`).

## File Routing Logic
- `INBOX_DIR` — ожидаются подпапки проектов с `_All` PDF; обработки других файлов нет.
- `NOTES_DIR` — копия исходного PDF.
- `TRA_GST_DIR` — копирование в папку `YYYY_TWW_GST`, где `WW` — ISO-неделя даты; при наличии архивов с похожим именем выбирается следующая неделя.
- `TRA_SUB_APP_DIR` — папка `<tz_index>-<reserved>-<period>`; для периодов ≠`C` добавляется суффикс из `TZ_glob.xlsx`.
- `DEST_ROOT_DIR/<…>/pdf` —
  - период `C` → «Корректирующее обслуживание»;
  - `LP` → папка по объекту (обрезаем ведущий 0, например `BVS05` → `BVS5`); при необходимости дополняйте словарь `LP_FOLDER_OVERRIDES`.
  - `CS` → поиск существующей папки по индексу ТЗ (например, `II.12*`); при необходимости дополняйте словарь `CS_FOLDER_OVERRIDES` в скрипте (`"II.1.1" → "II.1"`).
- `DEST_ROOT_DIR/<…>/Native` — копия временного zip-архива проекта; временный архив удаляется после копирования.
Все операции пишутся в JSONL `logs/dispatch/<run_id>.jsonl`.

## Testing Guidelines
Unit-тесты прикладывайте при изменении логики (`tests/test_logging_service.py`, `tests/test_cli_report.py`). Критические маршруты — через фиктивные PDF/JSONL. Для UI достаточно ручного тестирования (Tkinter не покрываем автотестами).

## Commit & Pull Request Guidelines
Сообщения коммитов в формате `type: action` (`feat: добавить UI для журналов`). PR содержит описание сценария, риски, список проверок (`pytest -q`). Журналы (каталог `logs/dispatch`) перед коммитами очищаем.

## Security & Configuration Tips
Не хардкодьте боевые пути — переопределяйте через `.env` или переменные окружения (`TOIR_INBOX_DIR`, `PYTHONIOENCODING`). Не коммитьте реальные PDF/архивы. Перед запуском убедитесь, что целевые каталоги доступны для записи.
