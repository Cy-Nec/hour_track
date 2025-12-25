import os
from pathlib import Path

_BASE_ROOT_PATH = Path(__file__).resolve().parent.parent
# ROOT_PATH теперь изначально указывает на папку db
ROOT_PATH = str(_BASE_ROOT_PATH / "db")

db_dir_path = _BASE_ROOT_PATH / "db"
db_files = list(db_dir_path.glob("*.db"))

if db_files:
    # Берём самый последний по времени модификации .db файл как текущую БД
    latest_db_file = max(db_files, key=lambda f: f.stat().st_mtime)
    _CURRENT_DB_FILENAME = latest_db_file.name
    print(f"[DEBUG Settings Module Load] Найдена существующая БД: {_CURRENT_DB_FILENAME}")
else:
    # Если .db файлов нет, используем имя по умолчанию
    _CURRENT_DB_FILENAME = "hour_track.db"
    print(f"[DEBUG Settings Module Load] .db файлы не найдены, используется имя по умолчанию: {_CURRENT_DB_FILENAME}")

def get_base_root_path():
    """Возвращает базовую директорию проекта."""
    # Возвращаем _BASE_ROOT_PATH как Path объект
    return _BASE_ROOT_PATH # Важно вернуть Path объект, а не строку

def update_root_path_with_db_file(full_db_path):
    """Обновляет ROOT_PATH на директорию базы данных и сохраняет имя файла."""
    global ROOT_PATH, _CURRENT_DB_FILENAME
    full_path_obj = Path(full_db_path)
    # Устанавливаем ROOT_PATH на директорию 'db'
    ROOT_PATH = str(full_path_obj.parent)
    # Сохраняем имя файла БД
    _CURRENT_DB_FILENAME = full_path_obj.name
    print(f"[DEBUG Settings] update_root_path_with_db_file вызван. ROOT_PATH теперь: {ROOT_PATH}, _CURRENT_DB_FILENAME: {_CURRENT_DB_FILENAME}")

def get_current_db_filename():
    """Возвращает имя текущего файла базы данных."""
    print(f"[DEBUG Settings] get_current_db_filename возвращает: {_CURRENT_DB_FILENAME}") # Добавлено для отладки
    return _CURRENT_DB_FILENAME

def get_full_db_path(db_filename=None):
    """Возвращает полный путь к файлу базы данных."""
    filename_to_use = db_filename if db_filename else _CURRENT_DB_FILENAME
    full_path = os.path.join(ROOT_PATH, filename_to_use)
    print(f"[DEBUG Settings] get_full_db_path для '{filename_to_use}' возвращает: {full_path}") # Добавлено для отладки
    return full_path

def reset_to_default_db():
    """Сбрасывает ROOT_PATH и имя БД на значения по умолчанию."""
    global ROOT_PATH, _CURRENT_DB_FILENAME
    _CURRENT_DB_FILENAME = "hour_track.db"
    root_dir = str(_BASE_ROOT_PATH)
    db_dir = os.path.join(root_dir, "db")
    os.makedirs(db_dir, exist_ok=True)
    ROOT_PATH = db_dir
    print(f"[DEBUG Settings] reset_to_default_db вызван. ROOT_PATH: {ROOT_PATH}, _CURRENT_DB_FILENAME: {_CURRENT_DB_FILENAME}")