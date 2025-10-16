# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.0] - 2025-10-16

### Added
- Инструкция по сборке PyInstaller-дистрибутива и описание расположения логов в README.
- Переменная окружения `TOIR_DISPATCH_DIR` для явного указания каталога журналов.
- Сообщение-журнал о несоответствии имени шаблону (подсказка по кириллице).

### Changed
- Собранный бинарь переименован в `toir_raspredelenije.exe`.
- UI и конвейер при запуске из exe всегда пишут логи в `logs/dispatch` рядом с приложением.
- Флаг `--run-pipeline` добавлен в `run_ui.py` для запуска конвейера без UI.
- Временные архивы теперь формируются в `logs/temp` рядом с приложением (переопределяются через `TOIR_TEMP_ARCHIVE_DIR`).
