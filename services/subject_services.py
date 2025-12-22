from .general import DBBase


class SubjectDAO(DBBase):
    def __init__(self, db_filename=None):
        super().__init__(db_filename)
        # self.cursor = self.create_cursor()
        # Включаем проверку внешних ключей
        # self._connection.execute("PRAGMA foreign_keys = ON")

    def create_subject(self, subject_name) -> str | None:
        """Создание предмета"""

        query = """INSERT INTO subjects (name) VALUES (?)"""
        try:
            self.cursor.execute(query, (subject_name,))
            self._connection.commit()
            return subject_name
        except Exception as e:
            print(f"Произошла ошибка при создании предмета: {e}")
            if self._connection:
                self._connection.rollback()

    def get_subject_by_name(self, subject_name) -> tuple:
        """Строгий поискс предмета по названию"""

        query = """SELECT * FROM subjects WHERE name = ?"""

        try:
            result = self.cursor.execute(query, (subject_name,)).fetchone()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении предмета по названию - {subject_name}: {e}")
            return ()

    def get_subjects_like_name(self, subject_name) -> list:
        """Не строгий поискс предметов по названию"""

        pattern = f"%{subject_name}%"
        query = """SELECT * FROM subjects WHERE name LIKE ?"""

        try:
            result = self.cursor.execute(query, (pattern,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении предмета по похожему названию - {subject_name}: {e}")
            return []

    def get_all_subjects(self) -> list:
        """Получение всех предметов"""

        query = "SELECT * FROM subjects"
        try:
            result = self.cursor.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении всех предметов: {e}")
            return []

    def update_subject(self, current_name, new_name) -> str | None:
        """Обновление предмета"""

        query = """UPDATE subjects SET name = ? WHERE name = ?"""
        try:
            result = self.cursor.execute(query, (new_name, current_name))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return new_name
        except Exception as e:
            print(f"Произошла ошибка при обновлении предмета: {e}")
            if self._connection:
                self._connection.rollback()

    def delete_subject(self, subject_name) -> str | None:
        """Удаление предмета"""

        query = """DELETE FROM subjects WHERE name = ?"""
        try:
            result = self.cursor.execute(query, (subject_name,))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return subject_name
        except Exception as e:
            print(f"Произошла ошибка при удалении предмета: {e}")
            if self._connection:
                self._connection.rollback()