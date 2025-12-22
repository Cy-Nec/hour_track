import os
import sqlite3
from settings.settings import get_full_db_path, get_current_db_filename


class DBBase:
    """Base class to work with db"""
    def __init__(self, db_filename=None):
        # Если имя файла не передано, используем текущее
        if db_filename is None:
             db_filename = get_current_db_filename()
        # Получаем полный путь к БД, используя функцию из settings
        self.db_path = get_full_db_path(db_filename)
        print(f"Подключение к БД: {self.db_path}") # Для отладки

        # Убедимся, что директория db существует
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

        # Создаем соединение
        self._connection = self.__create_connection(self.db_path)
        self.cursor = self.create_cursor()
        # Включаем проверку внешних ключей
        self._connection.execute("PRAGMA foreign_keys = ON")

    def get_db_path(self):
        return self.db_path

    def create_cursor(self):
        """Создаёт курсор и сохраняет соединение для последующего закрытия"""
        # Курсор создается из существующего соединения
        if self._connection is None:
            print("Предупреждение: Попытка создать курсор при закрытом соединении.")
            return None
        return self._connection.cursor()

    def __create_connection(self, path):
        """Создает соединение с БД по указанному пути."""
        print(f"[DEBUG DBBase] Подключение к БД по пути: {path}")
        try:
            conn = sqlite3.connect(path)
            return conn
        except Exception as e:
            print(f"Ошибка при подключении к БД по пути {path}: {e}")
            return None

    def close(self):
        """Закрывает соединение с БД, если оно открыто"""
        if self._connection:
            self._connection.close()
            self._connection = None