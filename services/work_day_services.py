from idlelib import query

from general import DBBase


class WorkDayDAO(DBBase):
    def __init__(self, db=None):
        super().__init__(r"D:\hour_track\db\hour_track.db")
        self.cursor = self.create_cursor()
        # Включаем проверку внешних ключей
        self._connection.execute("PRAGMA foreign_keys = ON")

    def create_work_day(self, date, subject_name, group_name, semester, hours) -> tuple | None:
        """Заполнение одного рабочего дня"""

        query = """INSERT INTO workDays (date, subject_name, group_name, semester, hours) VALUES (?, ?, ?, ?, ?)"""
        try:
            self.cursor.execute(query, (date, subject_name, group_name, semester, hours))

            # Проверяем, получилось ли добавить новую запись
            new_row = self.cursor.lastrowid
            if new_row is None:
                return None
            self._connection.commit()

            # Возвращаем набор данных, записанный в бд, используя встроенную переменную ROWID в sqlite
            select_query = """SELECT * FROM workDays WHERE id = ?"""
            self.cursor.execute(select_query, (new_row,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Произошла ошибка при заполнении рабочего дня: {e}")
            if self._connection:
                self._connection.rollback()

    def get_work_day_by_id(self, work_day_id) -> tuple:
        """Строгий поискс рабочего дня по его id"""

        query = """SELECT * FROM workDays WHERE id = ?"""

        try:
            result = self.cursor.execute(query, (work_day_id,)).fetchone()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении рабочего дня по его id - {work_day_id}: {e}")
            return ()

    def get_all_work_days(self) -> list:
        """Получение всех рабочих дней"""

        query = "SELECT * FROM workDays"
        try:
            result = self.cursor.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении всех рабочих дней: {e}")
            return []

    def get_work_days_by_group(self, group_name) -> list:
        """Получение рабочих дней по группе"""

        query = "SELECT * FROM workDays WHERE group_name = ?"
        try:
            result = self.cursor.execute(query, (group_name,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении рабочих дней по группе: {e}")
            return []

    def get_work_days_by_subject(self, subject_name) -> list:
        """Получение рабочих дней по предмету"""

        query = "SELECT * FROM workDays WHERE subject_name = ?"
        try:
            result = self.cursor.execute(query, (subject_name,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении рабочих дней по предмету: {e}")
            return []

    def get_work_days_by_date(self, date) -> list:
        """Получение рабочих дней по дате"""

        query = "SELECT * FROM workDays WHERE date = ?"
        try:
            result = self.cursor.execute(query, (date,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении рабочих дней по дате: {e}")
            return []

    def update_work_day(self, **kwargs) -> str | None:
        """Обновление рабочего дня"""
        pass
        # query = """UPDATE subjects SET name = ? WHERE name = ?"""
        # try:
        #     result = self.cursor.execute(query, (new_name, current_name))
        #     self._connection.commit()
        #
        #     # Проверяем, что запрос выполнился минимум над 1 записью
        #     if self.cursor.rowcount == 0:
        #         return None
        #
        #     return new_name
        # except Exception as e:
        #     print(f"Произошла ошибка при обновлении предмета: {e}")
        #     if self._connection:
        #         self._connection.rollback()

    def delete_work_day(self, work_day_id) -> str | None:
        """Удаление записи о рабочем дне"""

        query = """DELETE FROM workDays WHERE id = ?"""
        try:
            result = self.cursor.execute(query, (work_day_id,))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return work_day_id
        except Exception as e:
            print(f"Произошла ошибка при удалении предмета: {e}")
            if self._connection:
                self._connection.rollback()

workday = WorkDayDAO()
print(workday.create_work_day("16-05-2025", "СРЕДИЗЕМНОЕ МОРЕ", "23ИСП-1", 1, 2))