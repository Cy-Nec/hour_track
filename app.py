import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QDialog, QTreeWidgetItem, QMenu
from PyQt6.QtGui import QIcon
from PyQt6 import QtWidgets
from PyQt6 import QtCore
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

        self.setup_tree_widgets()

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())

        # Add empty row to initialization 
        self.add_empty_group(self.ui.treeW_firstHalf)
        self.add_empty_group(self.ui.treeW_SecondHalf)


    def setup_tree_widgets(self):
        """ Setup QTreeWidget."""
        tree_widgets = [self.ui.treeW_firstHalf, self.ui.treeW_SecondHalf]
        for tree_widget in tree_widgets:
            tree_widget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
            tree_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            # Connect signal to context menu
            tree_widget.customContextMenuRequested.connect(lambda pos, tw=tree_widget: self.open_context_menu(pos, tw))
            
            tree_widget.itemChanged.connect(self.on_item_changed)


    def add_empty_group(self, tree_widget, parent_item=None):
        """Добавляет одну пустую строку (группу или предмет) в дерево."""
        if parent_item:
            # add subject row
            new_item = QTreeWidgetItem(parent_item)
        else:
            # add group row
            new_item = QTreeWidgetItem(tree_widget)

        new_item.setFlags(new_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        new_item.setText(0, "") # empty row for title
        new_item.setText(1, "") # empty row for hours
        return new_item


    def on_item_changed(self, item, column):
        """
        Обработчик сигнала itemChanged.
        Вызывается, когда пользователь изменяет текст в элементе.
        """
        tree_widget = item.treeWidget()
        if column == 0 and item.text(0).strip(): 
            parent = item.parent()
            if parent:
                if parent.indexOfChild(item) == parent.childCount() - 1:
                    self.add_empty_subject(tree_widget, parent)
            else:
                if tree_widget.indexOfTopLevelItem(item) == tree_widget.topLevelItemCount() - 1:
                    self.add_empty_group(tree_widget)


    def add_empty_subject(self, tree_widget, parent_item):
        """Добавляет один пустой дочерний элемент (предмет) к родительскому элементу (группе)."""
        new_item = self.add_empty_group(tree_widget, parent_item)
        tree_widget.expandItem(parent_item)
        return new_item


    def open_context_menu(self, position, tree_widget):
        """Открывает контекстное меню для QTreeWidget."""
        menu = QMenu(tree_widget)
        add_group_action = menu.addAction("Добавить группу")
        add_subject_action = menu.addAction("Добавить предмет")
        delete_action = menu.addAction("Удалить")

        item = tree_widget.itemAt(position)
        if item:
            parent_item = item.parent()
            if parent_item:
                 add_group_action.setEnabled(False) 
                 add_subject_action.setEnabled(False)
            else:
                 add_group_action.setEnabled(False) 

            is_last_empty_top_level = (
                tree_widget.indexOfTopLevelItem(item) == tree_widget.topLevelItemCount() - 1
                and not item.text(0) and not item.text(1)
                and item.parent() is None 
            )
            if is_last_empty_top_level:
                 delete_action.setEnabled(False)
            else:
                delete_action.triggered.connect(lambda: self.delete_item(tree_widget, item))

            if parent_item is None:
                add_subject_action.triggered.connect(lambda: self.add_subject_context(tree_widget, item))
            else:
                add_subject_action.setEnabled(False)

        else:
            delete_action.setEnabled(False)
            add_subject_action.setEnabled(False)

        add_group_action.triggered.connect(lambda: self.add_group_context(tree_widget))

        def start_edit_on_action(action, add_func, *args):
            def handler():
                new_item = add_func(tree_widget, *args) if args else add_func(tree_widget)
                tree_widget.editItem(new_item, 0)
            action.triggered.connect(handler)

        menu.exec(tree_widget.mapToGlobal(position))

    def add_group_context(self, tree_widget):
        """Добавляет новую группу через контекстное меню."""
        new_item = self.add_empty_group(tree_widget)
        tree_widget.editItem(new_item, 0)

    def add_subject_context(self, tree_widget, parent_item):
        """Добавляет новый предмет через контекстное меню."""
        new_item = self.add_empty_subject(tree_widget, parent_item)
        tree_widget.editItem(new_item, 0)


    def delete_item(self, tree_widget, item):
        """Удаляет выбранный элемент."""
        is_last_empty_top_level = (
            tree_widget.indexOfTopLevelItem(item) == tree_widget.topLevelItemCount() - 1
            and not item.text(0) and not item.text(1)
            and item.parent() is None
        )
        if is_last_empty_top_level:
             return

        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = tree_widget.indexOfTopLevelItem(item)
            if index >= 0:
                tree_widget.takeTopLevelItem(index)
                if tree_widget.topLevelItemCount() == 0:
                     self.add_empty_group(tree_widget)


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