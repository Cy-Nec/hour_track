import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QDialog
from PyQt6.QtGui import QIcon
from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from ui.mainWindow import Ui_MainWindow
from ui.newYearDialog import Ui_Dialog_NewYear
from ui.filterDialog import Ui_Dialog_Filter
from ui.sortDialog import Ui_Dialog_Sort
from ui.about import Ui_about
from calendar_helper import setup_calendar_tables_for_half


# === ThemeManager ===
class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # theme switch signal

    def __init__(self):
        super().__init__()
        # Set start theme
        self.current_theme = "light"

    def set_theme(self, theme: str):
        if theme not in ("light", "dark", "blue"):
            return
        self.current_theme = theme
        self.theme_changed.emit(theme)

    def get_theme(self) -> str:
        return self.current_theme

    def get_icon_path(self, name: str) -> str:
        """Return path to icon"""
        return os.path.join("resources", "icons", self.current_theme, f"{name}.svg")

    def get_stylesheet(self) -> str:
        """Load QSS theme file"""
        path = os.path.join("themes", f"{self.current_theme}.qss")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Theme file not found: {path}")
            return ""


# === ThemedWindow (base class for Window) ===
class ThemedWindow(QMainWindow):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__()
        self.theme_manager = theme_manager
        # Connect to signal about theme switch
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    @pyqtSlot(str)
    def on_theme_changed(self, theme: str):
        """Call when theme switched"""
        self.setStyleSheet(self.theme_manager.get_stylesheet())
        self.update_icons()

    def update_icons(self):
        """For children classes"""
        pass


# === ThemedDialog (base class for modal window) ===
class ThemedDialog(QDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__()
        self.theme_manager = theme_manager
        # Connect to signal about theme switch
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    @pyqtSlot(str)
    def on_theme_changed(self, theme: str):
        """Call when theme switched"""
        self.setStyleSheet(self.theme_manager.get_stylesheet())
        self.update_icons()

    def update_icons(self):
        """For children classes"""
        pass


# === NewYearDialog ===
class NewYearDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_NewYear()
        self.ui.setupUi(self)

        # Delete system border
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())


# === FilterDialog ===
class FilterDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Filter()
        self.ui.setupUi(self)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())
    

# === SortDialog ===
class SortDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Sort()
        self.ui.setupUi(self)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())


# === about ===
class AboutWindow(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_about()
        self.ui.setupUi(self)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())


# === MainWindow ===
class MainWindow(ThemedWindow):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)   

        # "Первое" полугодие = Сент–Дек (4 месяца)
        self.first_half = [
            (9, "Сент"),
            (10, "Окт"),
            (11, "Нояб"),
            (12, "Декаб")
        ]
        # "Второе" полугодие = Янв–Июнь (6 месяцев)
        self.second_half = [
            (1, "Янв"),
            (2, "Фев"),
            (3, "Март"),
            (4, "Апр"),
            (5, "Май"),
            (6, "Июнь")
        ]

        # Подключаем радиокнопки
        self.ui.rBtn_First.toggled.connect(self.on_half_changed)
        self.ui.rBtn_Second.toggled.connect(self.on_half_changed)

        # Инициализируем начальное состояние — "Первое" полугодие активно
        self.on_half_changed()

        # Connection menu
        self.ui.light.triggered.connect(lambda: self.theme_manager.set_theme("light"))
        self.ui.dark.triggered.connect(lambda: self.theme_manager.set_theme("dark"))
        self.ui.blue.triggered.connect(lambda: self.theme_manager.set_theme("blue"))
        self.ui.about.triggered.connect(lambda: self.open_aboutWindow())

        # Apply start theme 
        self.on_theme_changed(self.theme_manager.get_theme())

        # Connect button "New_Year"
        if hasattr(self.ui, 'btn_NewYear'):
            self.ui.btn_NewYear.clicked.connect(self.open_new_year_dialog)
        # Connect button "Filter"
        if hasattr(self.ui, 'btn_Filt'):
            self.ui.btn_Filt.clicked.connect(self.open_filter_dialog)
        # Connect button "Sort"
        if hasattr(self.ui, 'btn_Sort'):
            self.ui.btn_Sort.clicked.connect(self.open_sort_dialog)

        for i in range(self.ui.tabW_SlidesFirstHalf.count()):
            table_view = self.ui.tabW_SlidesFirstHalf.widget(i).findChild(QtWidgets.QTableView)
            if table_view:
                # Скрываем вертикальный заголовок (номера строк)
                table_view.verticalHeader().setVisible(False)

    @pyqtSlot()
    def on_half_changed(self):
        """Общий обработчик изменения полугодия"""
        if self.ui.rBtn_First.isChecked():
            setup_calendar_tables_for_half(self.ui, year=2025, months_data=self.first_half)
        elif self.ui.rBtn_Second.isChecked():
            setup_calendar_tables_for_half(self.ui, year=2025, months_data=self.second_half)
     
    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_Search'):
            self.ui.btn_Search.setIcon(QIcon(self.theme_manager.get_icon_path("search")))
        if hasattr(self.ui, 'btn_Filt'):
            self.ui.btn_Filt.setIcon(QIcon(self.theme_manager.get_icon_path("filter")))
        if hasattr(self.ui, 'btn_Sort'):
            self.ui.btn_Sort.setIcon(QIcon(self.theme_manager.get_icon_path("sort")))
        if hasattr(self.ui, 'btn_Report'):
            self.ui.btn_Report.setIcon(QIcon(self.theme_manager.get_icon_path("report")))
        if hasattr(self.ui, 'btn_NewYear'):
            self.ui.btn_NewYear.setIcon(QIcon(self.theme_manager.get_icon_path("new_year")))
        if hasattr(self.ui, 'btn_Default'):
            self.ui.btn_Default.setIcon(QIcon(self.theme_manager.get_icon_path("refresh")))
    
    def open_new_year_dialog(self):
        dialog = NewYearDialog(self.theme_manager)
        dialog.exec()
    
    def open_filter_dialog(self):
        dialog = FilterDialog(self.theme_manager)
        dialog.exec()

    def open_sort_dialog(self):
        dialog = SortDialog(self.theme_manager)
        dialog.exec()
            
    def open_aboutWindow(self):
        dialog = AboutWindow(self.theme_manager)
        dialog.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create themeManager
    theme_manager = ThemeManager()

    # Create MainWindow
    window = MainWindow(theme_manager)
    window.show()

    sys.exit(app.exec())