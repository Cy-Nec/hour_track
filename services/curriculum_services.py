from .general import DBBase
from settings.settings import ROOT_PATH


class CurriculumDAO(DBBase):
    def __init__(self, db=None):
        super().__init__(rf"{ROOT_PATH}\db\hour_track.db")
        self.cursor = self.create_cursor()
        # Включаем проверку внешних ключей
        self._connection.execute("PRAGMA foreign_keys = ON")

    def create_curriculum(self, semester, total_hour, group_name, subject_name) -> tuple | None:
        """Заполнение одного учбеного плана"""

        query = """INSERT INTO curriculums (semester, total_hour, group_name, subject_name) VALUES (?, ?, ?, ?)"""
        try:
            self.cursor.execute(query, (semester, total_hour, group_name, subject_name))

            # Проверяем, получилось ли добавить новую запись
            new_row = self.cursor.lastrowid
            if new_row is None:
                return None
            self._connection.commit()

            # Возвращаем набор данных, записанный в бд, используя встроенную переменную ROWID в sqlite
            select_query = """SELECT * FROM curriculums WHERE id = ?"""
            self.cursor.execute(select_query, (new_row,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Произошла ошибка при заполнении учебного плана: {e}")
            if self._connection:
                self._connection.rollback()

    def get_curriculum_by_id(self, curriculum_id) -> tuple:
        """Строгий поиск учебного плана по его id"""

        query = """SELECT * FROM curriculums WHERE id = ?"""
        try:
            result = self.cursor.execute(query, (curriculum_id,)).fetchone()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении учебного плана по id {curriculum_id}: {e}")
            return ()

    def get_all_curriculums(self) -> list:
        """Получение всех учебных планов"""

        query = "SELECT * FROM curriculums"
        try:
            result = self.cursor.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении всех учебных планов: {e}")
            return []

    def get_curriculums_by_semester(self, semester) -> list:
        """Получение учебных планов по семестру"""

        query = "SELECT * FROM curriculums WHERE semester = ?"
        try:
            result = self.cursor.execute(query, (semester,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении учебных планов по семестру {semester}: {e}")
            return []

    def get_curriculums_by_group(self, group_name, use_like=False) -> list:
        """Получение учебных планов по группе"""

        if use_like:
            query = "SELECT * FROM curriculums WHERE group_name LIKE ?"
            group_name = f"%{group_name}%"
        else:
            query = "SELECT * FROM curriculums WHERE group_name = ?"
        try:
            result = self.cursor.execute(query, (group_name,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении учебных планов по группе: {e}")
            return []

    def get_curriculums_by_subject(self, subject_name, use_like=False) -> list:
        """Получение учебных планов по предмету"""

        if use_like:
            query = "SELECT * FROM curriculums WHERE subject_name LIKE ?"
            subject_name = f"%{subject_name}%"
        else:
            query = "SELECT * FROM curriculums WHERE subject_name = ?"
        try:
            result = self.cursor.execute(query, (subject_name,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении учебных планов по предмету: {e}")
            return []

    def update_curriculum(self, id, **kwargs) -> str | None:
        """Обновление учебного плана"""

        # Формируем строку запроса на основе переданных именованных аргументов
        query = """UPDATE curriculums SET """
        for k in kwargs:
            query += f"{k} = ?, """
        query = query[:-2] + """ WHERE id = ?"""

        # Формируем список значений
        values = list([v for v in kwargs.values()])
        values.append(id)

        try:
            result = self.cursor.execute(query, tuple(values))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            # Возвращаем набор данных, записанный в бд, используя встроенную переменную ROWID в sqlite
            select_query = """SELECT * FROM curriculums WHERE id = ?"""
            self.cursor.execute(select_query, (id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Произошла ошибка при учебного плана: {e}")
            if self._connection:
                self._connection.rollback()

    def delete_curriculum(self, curriculum_id) -> str | None:
        """Удаление записи учебного плана"""

        query = """DELETE FROM curriculums WHERE id = ?"""
        try:
            result = self.cursor.execute(query, (curriculum_id,))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return curriculum_id
        except Exception as e:
            print(f"Произошла ошибка при удалении учебного плана: {e}")
            if self._connection:
                self._connection.rollback()
