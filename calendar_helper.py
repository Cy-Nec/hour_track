import calendar
from PyQt6.QtWidgets import QTableWidgetItem, QTableWidget, QHeaderView
from PyQt6.QtCore import Qt
from datetime import date


class CalendarTableData:
    def __init__(self, year: int, month: int):
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


def setup_calendar_tables_for_half(ui, year: int, months_data: list):
    tab_widget = ui.tabW_SlidesFirstHalf

    # Сначала скрываем все вкладки
    for i in range(tab_widget.count()):
        tab_widget.setTabVisible(i, False)

    # Затем настраиваем только нужные вкладки
    for i, (month, label) in enumerate(months_data):
        if i >= tab_widget.count():
            continue

        # Создаем объект данных для календаря
        calendar_data = CalendarTableData(year, month)
        
        # Получаем соответствующий QTableWidget для вкладки
        # Сопоставляем вкладку с таблицей напрямую
        if i == 0:
            table_widget = ui.tableV_hours_1
        elif i == 1:
            table_widget = ui.tableV_hours_4
        elif i == 2:
            table_widget = ui.tableV_hours_2
        elif i == 3:
            table_widget = ui.tableV_hours_3
        elif i == 4:
            table_widget = ui.tableV_hours_5
        elif i == 5:
            table_widget = ui.tableV_hours_6
        else:
            continue  # Пропускаем если индекс больше доступных таблиц

        if table_widget:
            # Устанавливаем количество строк и колонок
            table_widget.setRowCount(1)
            col_count = len(calendar_data.dates) + 2
            table_widget.setColumnCount(col_count)

            # Заполняем шапку таблицы (заголовки столбцов)
            headers = ["Группа", "Предмет"] + [dt.strftime("%d") for dt in calendar_data.dates]
            for col in range(col_count):
                header_item = QTableWidgetItem(headers[col])
                table_widget.setHorizontalHeaderItem(col, header_item)

            # Заполняем ячейки данными
            for col in range(col_count):
                item = QTableWidgetItem(calendar_data.data_values[col])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Делаем редактируемыми
                table_widget.setItem(0, col, item)

            # Устанавливаем фиксированную ширину для первых двух колонок
            for col in range(min(2, col_count)):
                table_widget.setColumnWidth(col, 100)

            # Для остальных колонок можно установить растяжение
            header = table_widget.horizontalHeader()
            for col in range(2, col_count):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        # Устанавливаем текст вкладки и делаем её видимой
        tab_widget.setTabText(i, label)
        tab_widget.setTabVisible(i, True)

    # Показываем первую видимую вкладку
    for i in range(tab_widget.count()):
        if tab_widget.isTabVisible(i):
            tab_widget.setCurrentIndex(i)
            break