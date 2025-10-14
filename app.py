import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon
from ui.mainWindow import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # current theme
        self.current_theme = "light"

        # menuBar theme connect
        self.ui.light.triggered.connect(lambda: self.switch_theme("light"))
        self.ui.dark.triggered.connect(lambda: self.switch_theme("dark"))

        # apply start theme
        self.apply_theme(self.current_theme)

    def get_icon(self, name: str) -> QIcon:
        """return icon from current theme (as file path)"""
        path = os.path.join(os.path.dirname(__file__), "resources", "icons", self.current_theme, f"{name}.svg")
        return QIcon(path)

    def load_stylesheet(self, theme: str) -> str:
        """load QSS theme file"""
        path = os.path.join(os.path.dirname(__file__), "themes", f"{theme}.qss")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Theme file not found: {path}")
            return ""

    def apply_theme(self, theme: str):
        """Apply theme (icons + stylesheet)"""
        # save current theme
        self.current_theme = theme

        # apply QSS
        self.setStyleSheet(self.load_stylesheet(theme))

        # update icons
        if hasattr(self.ui, 'btn_Search'):
            self.ui.btn_Search.setIcon(self.get_icon("search"))
        if hasattr(self.ui, 'btn_Filt'):
            self.ui.btn_Filt.setIcon(self.get_icon("filter"))
        if hasattr(self.ui, 'btn_Sort'):
            self.ui.btn_Sort.setIcon(self.get_icon("sort"))
        if hasattr(self.ui, 'btn_Report'):
            self.ui.btn_Report.setIcon(self.get_icon("report"))
        if hasattr(self.ui, 'btn_NewYear'):
            self.ui.btn_NewYear.setIcon(self.get_icon("new_year"))
        if hasattr(self.ui, 'btn_Default'):
            self.ui.btn_Default.setIcon(self.get_icon("refresh"))

    def switch_theme(self, theme: str):
        """Switch current theme"""
        if theme not in ("light", "dark"):
            return
        self.apply_theme(theme)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())