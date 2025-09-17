import re
import shutil
from pathlib import Path
import sys
from datetime import datetime
from itertools import chain
import json

# Для работы с Excel требуется установка библиотеки openpyxl: pip install openpyxl
try:
    from openpyxl import load_workbook
except ImportError:
    print("[КРИТИЧЕСКАЯ ОШИБКА] Библиотека openpyxl не найдена. Пожалуйста, установите ее: pip install openpyxl")
    sys.exit(1)

# Настройка UTF-8 вывода в Windows-консоли
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# === НАСТРОЙКИ ПУТЕЙ ===
# Замените пути на актуальные для вашей системы.
# Используйте r"..." для путей в Windows, чтобы избежать проблем с \

# 1. Папка, где лежат исходные проекты для обработки (внутри которой папки с отчетами)
INBOX_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel\\00_Inbox")

# 2. Папка для копирования PDF-файлов (примечания)
NOTES_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel\\03_Notes")

# 3. Папка для копирования PDF-файлов (трансмиттал)
TRA_GST_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel\\04_TRA_GST")

# 4. Папка для специальной группировки
TRA_SUB_APP_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel\\05_TRA_SUB_app")

# 5. Корневая папка для создаваемой структуры (Год/Месяц/Part/pdf и Native)
DEST_ROOT_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel")

# 6. Временная папка для создания архивов (может совпадать с DEST_ROOT_DIR)
TEMP_ARCHIVE_DIR = Path(r"D:\\Code_and_Scripts_local\\_TEST_for\\toir_raspredelenije_test2_cel")

# 7. Путь к файлу-справочнику
TZ_FILE_PATH = Path("Template/TZ_glob.xlsx")


# === НАСТРОЙКИ ЛОГИКИ ===

# Регулярное выражение для разбора имени файла на основе предоставленной схемы
RE_FILENAME = re.compile(
    r"""^CT-
    (?P<type>CL|DR)-
    (?P<scope>[A-Z0-9]+)-
    (?P<part>CS|LP)-
    (?P<object_name>[A-Z0-9]+)-
    (?P<tz_index>[\w\.]+)-
    (?P<reserved>\d{2})-
    (?P<period>\w+)-
    (?P<date>\d{8})-
    (?P<revision>\d{2})
    _All.*?\.pdf$""",  # Ищем _All, затем любые символы, и только .pdf
    re.IGNORECASE | re.VERBOSE
)


# Словарь для перевода номера месяца в название
MONTH_MAP = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December"
}

# Настройки для файла-справочника TZ_glob.xlsx
TZ_SHEET_NAME = "gen_cl"
TZ_LOOKUP_COL = "B"  # Колонка с индексами (I.7.5)
TZ_SUFFIX_COL = "G"  # Колонка с суффиксами (краткая аббревиатура)


def find_suffix_in_tz_file(lookup_key: str) -> str | None:
    """
    Ищет индекс в файле TZ_glob.xlsx и возвращает суффикс.
    """
    if not TZ_FILE_PATH.exists():
        print(f"  - [ОШИБКА] Файл-справочник не найден: {TZ_FILE_PATH}")
        return None

    try:
        wb = load_workbook(TZ_FILE_PATH, data_only=True)
        if TZ_SHEET_NAME not in wb.sheetnames:
            print(f"  - [ОШИБКА] Лист '{TZ_SHEET_NAME}' не найден в файле {TZ_FILE_PATH}")
            return None
        
        ws = wb[TZ_SHEET_NAME]
        
        lookup_col_idx = ord(TZ_LOOKUP_COL.upper()) - ord('A') + 1
        suffix_col_idx = ord(TZ_SUFFIX_COL.upper()) - ord('A') + 1

        for row in ws.iter_rows(min_row=2, values_only=True): # Начинаем со второй строки, пропуская заголовок
            cell_value = str(row[lookup_col_idx - 1]).strip().lower() if row[lookup_col_idx - 1] else ""
            if cell_value == lookup_key.strip().lower():
                suffix = row[suffix_col_idx - 1]
                return str(suffix).strip() if suffix else None
        
        return None
    except Exception as e:
        print(f"  - [ОШИБКА] Ошибка при чтении файла {TZ_FILE_PATH}: {e}")
        return None


def process_special_grouping_for_sub_app(report_file: Path, data: dict):
    """
    Выполняет специальную группировку и копирование в папку 05_TRA_SUB_app.
    """
    print(f"  - Применение специальной группировки для {TRA_SUB_APP_DIR.name}...")
    try:
        # 1. Формируем ключ группировки
        grouping_key = f"{data['tz_index']}-{data['reserved']}-{data['period']}"
        period = data['period'].upper()
        
        folder_name = ""

        # 2. Определяем имя папки
        if period == 'C':
            folder_name = grouping_key
            print(f"    - Группа 'Корректирующее'. Имя папки: {folder_name}")
        else:
            tz_index = data['tz_index']
            print(f"    - Поиск суффикса для индекса: {tz_index}")
            suffix = find_suffix_in_tz_file(tz_index)
            
            if not suffix:
                print(f"    - [ПРЕДУПРЕЖДЕНИЕ] Суффикс для индекса '{tz_index}' не найден. Копирование в эту папку будет пропущено.")
                return
            
            print(f"    - Найден суффикс: '{suffix}'")
            folder_name = f"{grouping_key}_{suffix}"

        # 3. Копируем файл
        dest_dir = TRA_SUB_APP_DIR / folder_name
        dest_dir.mkdir(exist_ok=True)
        print(f"    - Копирование файла в: {dest_dir}")
        shutil.copy(report_file, dest_dir)

    except Exception as e:
        print(f"  - [ОШИБКА] Не удалось выполнить специальную группировку: {e}")


def normalize_object_name(object_name: str) -> str:
    """
    Нормализует имя объекта, удаляя ведущий ноль для однозначных номеров.
    Пример: BVS05 -> BVS5. BVS10 -> BVS10.
    """
    # Ищем шаблон: BVS, затем 0, затем одна цифра от 1 до 9
    match = re.match(r"^(BVS)0([1-9])$", object_name, re.IGNORECASE)
    if match:
        # Собираем новое имя из первой группы (BVS) и второй (цифра)
        normalized_name = match.group(1) + match.group(2)
        print(f"  - [ИНФО] Имя объекта нормализовано: {object_name} -> {normalized_name}")
        return normalized_name
    return object_name

def copy_to_gst_folder(report_file: Path, date_str: str, tra_gst_dir: Path):
    """
    Выполняет копирование в папку 04_TRA_GST по расширенному правилу.
    """
    print(f"  - Применение расширенного правила для {tra_gst_dir.name}...")
    
    try:
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        week_number = date_obj.isocalendar()[1]
        year = date_str[:4]
    except ValueError:
        print(f"  - [ОШИБКА] Неверный формат даты в строке '{date_str}'. Невозможно определить неделю.")
        return

    while True:
        folder_name = f"{year}_T{week_number}_GST"
        target_dir = tra_gst_dir / folder_name
        
        print(f"    - Проверка папки: {target_dir.name}")

        is_locked = False
        if target_dir.exists():
            for ext in ["*.zip", "*.7z", "*.rar"]:
                if any("CT-GST-TRA-PRM-" in archive.name for archive in target_dir.glob(ext)):
                    print(f"    - Папка 'закрыта' архивом. Поиск следующей недели...")
                    is_locked = True
                    break
        
        if is_locked:
            week_number += 1
            continue
        
        print(f"    - Найдена 'свободная' папка: {target_dir.name}")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(report_file, target_dir)
            print(f"    - Файл успешно скопирован в: {target_dir}")
            break
        except Exception as e:
            print(f"  - [ОШИБКА] Не удалось скопировать файл в папку GST: {e}")
            break

def process_project_folder(project_path: Path):
    """Обрабатывает одну папку из INBOX_DIR."""
    print(f"\n--- Сканирование папки: {project_path.name} ---")

    # 1. Ищем уникальный PDF файл, содержащий _All и соответствующий шаблону
    all_matching_files = []
    # Ищем только PDF файлы, содержащие "_All"
    for file_path in project_path.glob("*_All*.[pP][dD][fF]"):
        if RE_FILENAME.match(file_path.name):
            all_matching_files.append(file_path)

    if not all_matching_files:
        print("  - [ИНФО] Файл отчета, соответствующий шаблону, не найден. Пропуск папки.")
        return
    if len(all_matching_files) > 1:
        print(f"  - [ПРЕДУПРЕЖДЕНИЕ] Найдено несколько ({len(all_matching_files)}) файлов отчетов. Пропуск папки.")
        return
    
    report_file = all_matching_files[0]
    print(f"  - Найден файл для обработки: {report_file.name}")

    # 2. Разбираем имя файла
    match = RE_FILENAME.match(report_file.name)
    if not match:
        print(f"  - [КРИТИЧЕСКАЯ ОШИБКА] Файл {report_file.name} не соответствует шаблону. Пропуск.")
        return

    data = match.groupdict()
    print(f"  - Разобраны данные из имени файла:\n{json.dumps(data, indent=4, ensure_ascii=False)}")

    date_str = data["date"]
    year = date_str[:4]
    month_num = date_str[4:6]
    month_name = MONTH_MAP.get(month_num, "UnknownMonth")
    part = data["part"].upper()
    month_folder_name = f"{month_num}.{month_name}"
    period = data['period'].upper()

    # 3. Определяем путь назначения
    pdf_dest_dir = None
    archive_dest_dir = None

    if period == 'C':
        print("  - [ИНФО] Логика для Корректирующего обслуживания.")
        target_folder_name = "Корректирующее ослуживание"
        
        pdf_dest_dir = DEST_ROOT_DIR / year / month_folder_name / part / "pdf" / target_folder_name
        archive_dest_dir = DEST_ROOT_DIR / year / month_folder_name / part / "Native" / target_folder_name
    
    else:
        print("  - [ИНФО] Логика для периодического обслуживания.")
        if part == 'LP':
            print("  - [ИНФО] Логика для LP.")
            object_name_raw = data["object_name"].upper()
            object_name = normalize_object_name(object_name_raw)
            
            pdf_dest_dir = DEST_ROOT_DIR / year / month_folder_name / part / "pdf" / object_name
            archive_dest_dir = DEST_ROOT_DIR / year / month_folder_name / part / "Native" / object_name

        elif part == 'CS':
            print("  - [ИНФО] Логика для CS.")
            tz_index = data["tz_index"]
            
            base_search_dir = DEST_ROOT_DIR / year / month_folder_name / part / "pdf"
            base_search_dir.mkdir(parents=True, exist_ok=True)
            
            found_folders = list(base_search_dir.glob(f"{tz_index}*"))
            
            if not found_folders:
                print(f"  - [ОШИБКА] Для индекса '{tz_index}' не найдена папка в {base_search_dir}. Пропуск.")
                return
            if len(found_folders) > 1:
                print(f"  - [ПРЕДУПРЕЖДЕНИЕ] Для индекса '{tz_index}' найдено несколько папок. Используется первая: {found_folders[0].name}")
            
            target_folder_name = found_folders[0].name
            print(f"  - Найдена папка назначения для CS: {target_folder_name}")
            
            pdf_dest_dir = base_search_dir / target_folder_name
            archive_dest_dir = DEST_ROOT_DIR / year / month_folder_name / part / "Native" / target_folder_name

    if not pdf_dest_dir or not archive_dest_dir:
        print("  - [ОШИБКА] Не удалось определить пути назначения. Пропуск.")
        return

    # 4. Копируем отчет в простые и сложные директории
    try:
        print(f"  - Копирование в {NOTES_DIR.name}...")
        shutil.copy(report_file, NOTES_DIR)
        
        copy_to_gst_folder(report_file, date_str, TRA_GST_DIR)

        # Выполняем новую специальную группировку
        process_special_grouping_for_sub_app(report_file, data)

        pdf_dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"  - Копирование отчета в: {pdf_dest_dir}")
        shutil.copy(report_file, pdf_dest_dir)
    except Exception as e:
        print(f"  - [ОШИБКА] Не удалось скопировать отчет: {e}")
        return

    # 5. Архивируем исходную папку и перемещаем архив (с перезаписью)
    try:
        archive_dest_dir.mkdir(parents=True, exist_ok=True)
        archive_basename = TEMP_ARCHIVE_DIR / project_path.name
        print(f"  - Создание архива для папки: {project_path.name}...")
        archive_path_str = shutil.make_archive(str(archive_basename), 'zip', str(project_path))
        archive_path = Path(archive_path_str)
        
        print(f"  - Копирование архива в: {archive_dest_dir} (с перезаписью существующего)")
        shutil.copy(archive_path, archive_dest_dir)
        
        # Удаляем временный архив после успешного копирования
        archive_path.unlink()
    except Exception as e:
        print(f"  - [ОШИБКА] Не удалось создать или переместить архив: {e}")



def main():
    """Главная функция для распределения файлов."""
    print("Запуск скрипта по распределению файлов...")

    # Проверяем и создаем базовые папки, если они не существуют
    # Это важно для папок назначения, чтобы shutil.copy не выдавал ошибку
    for dir_path in [NOTES_DIR, TRA_GST_DIR]:
        if not dir_path.exists():
            print(f"Создание необходимой папки: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)

    if not INBOX_DIR.exists():
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] Папка с исходными файлами не найдена: {INBOX_DIR}")
        return

    # Ищем папки в INBOX_DIR
    project_folders = [p for p in INBOX_DIR.iterdir() if p.is_dir()]

    if not project_folders:
        print(f"В папке {INBOX_DIR} не найдено подпапок для обработки.")
        return

    print(f"Найдено {len(project_folders)} папок для проверки.")
    for folder in project_folders:
        process_project_folder(folder)

    print("\nОбработка завершена.")

if __name__ == "__main__":
    main()