from .general import DBBase


class WorkDayDAO(DBBase):
    def __init__(self, db_filename=None):
        super().__init__(db_filename)
        # self.cursor = self.create_cursor()
        # Включаем проверку внешних ключей
        # self._connection.execute("PRAGMA foreign_keys = ON")

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

    def get_work_days_by_group(self, group_name, use_like=False) -> list:
        """
        Получение рабочих дней по группе
        :parameter use_like: Параметр, означающий, будет ли в запросе использоваться констуркция LIKE
        """

        # Формируем запрос
        if use_like:
            query = "SELECT * FROM workDays WHERE group_name LIKE ?"
            # Подготавливаем значение с % по краям
            group_name = f"%{group_name}%"
        else:
            query = "SELECT * FROM workDays WHERE group_name = ?"

        try:
            result = self.cursor.execute(query, (group_name,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении рабочих дней по группе: {e}")
            return []

    def get_work_days_by_subject(self, subject_name, use_like=False) -> list:
        """
        Получение рабочих дней по предмету
        :parameter use_like: Параметр, означающий, будет ли в запросе использоваться констуркция LIKE
        """

        # Формируем запрос
        if use_like:
            query = "SELECT * FROM workDays WHERE subject_name LIKE ?"
            # Подготавливаем значение с % по краям
            subject_name = f"%{subject_name}%"
        else:
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

    def update_work_day(self, id, **kwargs) -> str | None:
        """Обновление рабочего дня"""

        # Формируем строку запроса на основе переданных именованных аргументов
        query = """UPDATE workDays SET """
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
            select_query = """SELECT * FROM workDays WHERE id = ?"""
            self.cursor.execute(select_query, (id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Произошла ошибка при обновлении предмета: {e}")
            if self._connection:
                self._connection.rollback()

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
            print(f"Произошла ошибка при удалении рабочего дня: {e}")
            if self._connection:
                self._connection.rollback()
