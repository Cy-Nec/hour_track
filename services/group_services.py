from general import DBBase


class GroupDAO(DBBase):
    def __init__(self, db=None):
        super().__init__(r"D:\hour_track\db\hour_track.db")
        self.cursor = self.create_cursor()

    def create_group(self, group_name) -> str | None:
        """Создание группы"""

        query = """INSERT INTO groups (name) VALUES (?)"""
        try:
            self.cursor.execute(query, (group_name,))
            self._connection.commit()
            return group_name
        except Exception as e:
            print(f"Произошла ошибка при создании группы: {e}")
            if self._connection:
                self._connection.rollback()

    def get_group_by_name(self, group_name) -> tuple:
        """Строгий поискс групп по названию"""

        query = """SELECT * FROM groups WHERE name = ?"""

        try:
            result = self.cursor.execute(query, (group_name,)).fetchone()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении группы по названию - {group_name}: {e}")
            return ()

    def get_groups_like_name(self, group_name) -> list:
        """Не строгий поискс групп по названию"""

        pattern = f"%{group_name}%"
        query = """SELECT * FROM groups WHERE name LIKE ?"""

        try:
            result = self.cursor.execute(query, (pattern,)).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении групп по похожему названию - {group_name}: {e}")
            return []

    def get_all_groups(self) -> list:
        """Получение всех групп"""

        query = "SELECT * FROM groups"
        try:
            result = self.cursor.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Произошла ошибка при получении всех групп: {e}")
            return []

    def update_group(self, current_name, new_name) -> str | None:
        """Обновление группы"""

        query = """UPDATE groups SET name = ? WHERE name = ?"""
        try:
            result = self.cursor.execute(query, (new_name, current_name))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return new_name
        except Exception as e:
            print(f"Произошла ошибка при обновлении группы: {e}")
            if self._connection:
                self._connection.rollback()

    def delete_group(self, group_name) -> str | None:
        """Удаление группы"""

        query = """DELETE FROM groups WHERE name = ?"""
        try:
            result = self.cursor.execute(query, (group_name,))
            self._connection.commit()

            # Проверяем, что запрос выполнился минимум над 1 записью
            if self.cursor.rowcount == 0:
                return None

            return group_name
        except Exception as e:
            print(f"Произошла ошибка при удалении группы: {e}")
            if self._connection:
                self._connection.rollback()
