import calendar
from PyQt6.QtCore import QAbstractTableModel, Qt
from datetime import date


class CalendarTableModel(QAbstractTableModel):
    def __init__(self, year: int, month: int, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month

        # Собираем даты месяца, исключая воскресенья
        self.dates = []
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            dt = date(year, month, day)
            weekday = dt.weekday()  # 0 — понедельник, 6 — воскресенье
            if weekday != 6:  # Исключаем воскресенье
                self.dates.append(dt)

        # Данные для редактирования (изначально пустые строки)
        self.data_values = [""] * (len(self.dates) + 2)

        # Ссылка на таблицу, чтобы вызвать resize при изменении
        self.table_view = None

    def set_table_view(self, table_view):
        """Привязывает таблицу к модели, чтобы можно было вызывать resize"""
        self.table_view = table_view

    def rowCount(self, parent=None):
        return 1  # Одна строка

    def columnCount(self, parent=None):
        return len(self.dates) + 2  # Даты + 2 пустые колонки в начале

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if row == 0:
                # Для дат (начиная с 3-й колонки)
                if col >= 2:
                    date_index = col - 2
                    if date_index < len(self.dates):
                        # Показываем дату только в шапке, а не в данных строки
                        return self.data_values[col]
                else:
                    # Для первых 2 колонок
                    return self.data_values[col]

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()

        if row == 0 and col >= 2:  # Только начиная с 3-й колонки
            self.data_values[col] = value
            self.dataChanged.emit(index, index)

            # После изменения данных — подстраиваем ширину колонки
            if self.table_view:
                self.table_view.resizeColumnToContents(col)

            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled

        col = index.column()

        # Только начиная с 3-й колонки (индекс 2) — редактируемо
        if col >= 2:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        else:
            return super().flags(index)  # Только для чтения

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return "Группа"
            elif section == 1:
                return "Предмет"
            else:
                # Над датами — день месяца (например, "01", "02", ...)
                date_index = section - 2
                if date_index < len(self.dates):
                    return self.dates[date_index].strftime("%d")  # Только день месяца
        return None


def setup_calendar_tables(ui, year: int = 2025):
    """
    Заполняет QTableView на вкладках датами месяцев, распределёнными по строке, начиная с 3-й колонки, исключая воскресенья
    """
    months = [
        (9, "Сент"),   # сентябрь
        (10, "Окт"),   # октябрь
        (11, "Нояб"),  # ноябрь
        (12, "Декаб")  # декабрь
    ]

    tables = [
        ui.tableV_hours_1,  # Сент
        ui.tableV_hours_4,  # Окт
        ui.tableV_hours_2,  # Нояб
        ui.tableV_hours_3   # Декаб
    ]

    for i, (month, label) in enumerate(months):
        model = CalendarTableModel(year, month)
        tables[i].setModel(model)

        # Привязываем таблицу к модели, чтобы вызывать resize
        model.set_table_view(tables[i])

        # Подстраиваем ширину колонок под содержимое
        tables[i].resizeColumnsToContents()

        # Обновляем название вкладки, если нужно
        ui.tabW_Slides.setTabText(i, label)