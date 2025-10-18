import sqlite3
from settings.settings import ROOT_PATH


class DBBase:
    """Base class to work with db"""

    def __init__(self, db_file=f"{ROOT_PATH}/db/hour_track.db"):
        self.db_file = db_file
        self._connection = None  # будем хранить соединение, чтобы закрыть позже

    def create_cursor(self):
        """Создаёт курсор и сохраняет соединение для последующего закрытия"""
        if self._connection is None:
            self._connection = self.__create_connection()
        return self._connection.cursor()

    def __create_connection(self):
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except Exception as e:
            print(f"Ошибка при подключении к БД: {e}")
            return None

    def close(self):
        """Закрывает соединение с БД, если оно открыто"""
        if self._connection:
            self._connection.close()
            self._connection = None