import calendar
import sys
import os
import configparser
from datetime import date, datetime, timedelta

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QDialog, QTreeWidgetItem, QMenu, QMessageBox, QListWidget, QListWidgetItem, QCompleter, QHeaderView, QTableWidget, QTableWidgetItem
from PyQt6.QtGui import QIcon, QPalette, QFontDatabase
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QTimer

from services.work_day_services import WorkDayDAO
from ui.mainWindow import Ui_MainWindow
from ui.newYearDialog import Ui_Dialog_NewYear
from ui.filterDialog import Ui_Dialog_Filter
from ui.sortDialog import Ui_Dialog_Sort
from ui.about import Ui_about
from ui.reportDialog import Ui_Dialog_Report
from ui.groupDialog import Ui_Dialog_Group
from ui.YearEditDialog import Ui_Dialog_YearEdit
from ui.subjectDialog import Ui_Dialog_Subject
from calendar_helper import CalendarTableData, setup_calendar_tables_for_half

from services.group_services import GroupDAO
from services.curriculum_services import CurriculumDAO
from services.subject_services import SubjectDAO


# === ThemeManager ===
class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # theme switch signal

    def __init__(self):
        super().__init__()

        self.custom_font_path = r"resources\fonts\CascadiaCode\CascadiaCode-VariableFont_wght.ttf"
        self.font_family = None

        # Загрузка шрифта
        if self.custom_font_path and os.path.exists(self.custom_font_path):
            font_id = QFontDatabase.addApplicationFont(self.custom_font_path)
            if font_id == -1:
                print("Не удалось загрузить шрифт через QFontDatabase")
            else:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    self.font_family = font_families[0]
                    print(f"Шрифт успешно загружен: {self.font_family}")
                else:
                    print("Не удалось получить имя шрифта из загруженного файла.")
        else:
            print("Путь к шрифту некорректен или файл не существует")

        # Создание объекта чтения конфига
        config = configparser.ConfigParser()
        read_config = config.read(rf'settings/config.ini')

        if not read_config:
            self.create_config()

        # get and set start theme
        self.current_theme = config['theme']['current_theme']

    def set_theme(self, theme: str):
        if theme not in ("light", "dark", "blue"):
            return
        self.current_theme = theme
        self.theme_changed.emit(theme)
        config = configparser.ConfigParser()
        config.read(rf'settings/config.ini')
        config['theme']['current_theme'] = theme
        with open(rf'settings/config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)

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
                stylesheet = f.read()

            # Добавляем шрифт в начало, если он загружен
            if self.font_family:
                font_style = f"* {{ font-family: \"{self.font_family}\"; }}\n\n"
                stylesheet = font_style + stylesheet

            return stylesheet
        except FileNotFoundError:
            print(f"Theme file not found: {path}")
            return ""

    def create_config(self):
        """Create config file"""
        config = configparser.ConfigParser()

        # Определение структуры конфига
        config['theme'] = {
            'current_theme': 'blue'
        }

        # Создание конфига
        with open(rf'settings/config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)


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


class YearEditDialog(ThemedDialog):
    def __init__(self, theme_manager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_YearEdit()
        self.ui.setupUi(self)
        
        self.group_service = GroupDAO()
        self.subject_service = SubjectDAO()
        self.curriculum_service = CurriculumDAO()
        
        self.on_theme_changed(self.theme_manager.get_theme())
        self.update_icons()
        
        self.load_groups()
        self.load_subjects()
        
        # Настройка ширины колонок в таблице
        header = self.ui.tableWidget_Hours .horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Подключение сигналов от кнопок
        self.ui.btn_AddSelected.clicked.connect(self.move_selected_items_to_table)
        self.ui.btn_RemoveSelected.clicked.connect(self.move_selected_items_to_list)
        self.ui.btn_Accept.clicked.connect(self.apply_changes)
        self.ui.btn_Cancel.clicked.connect(self.close)
        
        self.ui.comboBox_Groups.currentTextChanged.connect(self.on_group_or_semester_changed)
        self.ui.radioButton_First.toggled.connect(self.on_group_or_semester_changed)
        self.ui.radioButton_Second.toggled.connect(self.on_group_or_semester_changed)

    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_RemoveSelected'):
            self.ui.btn_RemoveSelected.setIcon(QIcon(self.theme_manager.get_icon_path("left")))
        if hasattr(self.ui, 'btn_AddSelected'):
            self.ui.btn_AddSelected.setIcon(QIcon(self.theme_manager.get_icon_path("right")))
            
    def load_groups(self):
        try:
            groups = self.group_service.get_all_groups()
            for group in groups:
                self.ui.comboBox_Groups.addItem(group[0])

            self.ui.comboBox_Groups.setCurrentIndex(-1)
        except Exception as e:
            print(f"Произошла ошибка при загрузке групп: {e}")  
    
    def load_subjects(self):
        try:
            subjects = self.subject_service.get_all_subjects()
            for subject in subjects:
                self.ui.listWidget_Subjects.addItem(subject[0])
        except Exception as e:
            print(f"Произошла ошибка при загрузке предметов: {e}")  
            
    def move_selected_items_to_table(self):
        selected_items = self.ui.listWidget_Subjects.selectedItems()

        if not selected_items:
            return  

        for item in selected_items:
            text = item.text()

            row_position = self.ui.tableWidget_Hours.rowCount()
            self.ui.tableWidget_Hours.insertRow(row_position)

            self.ui.tableWidget_Hours.setItem(row_position, 0, QTableWidgetItem(text))

        for item in reversed(selected_items):
            row = self.ui.listWidget_Subjects.row(item)
            self.ui.listWidget_Subjects.takeItem(row)
            
    def move_selected_items_to_list(self):
        selected_ranges = self.ui.tableWidget_Hours.selectedRanges()
        rows_to_remove = []

        for range_obj in selected_ranges:
            for row in range(range_obj.topRow(), range_obj.bottomRow() + 1):
                if row not in rows_to_remove:
                    rows_to_remove.append(row)

        rows_to_remove.sort(reverse=True)

        for row in rows_to_remove:
            item_text = self.ui.tableWidget_Hours.item(row, 0).text() if self.ui.tableWidget_Hours.item(row, 0) else ""

            self.ui.listWidget_Subjects.addItem(item_text)
            self.ui.tableWidget_Hours.removeRow(row)
    
    def on_group_or_semester_changed(self):
        """
        Загружает данные в tableWidget_Hours и listWidget_Subjects
        в зависимости от выбранной группы и активного radio button (семестр).
        """
        group_name = self.ui.comboBox_Groups.currentText()
        if not group_name: 
            self.ui.tableWidget_Hours.setRowCount(0)  
            self.ui.listWidget_Subjects.clear()     
            self.load_subjects()  
            return

        if self.ui.radioButton_First.isChecked():
            semester = 1
        elif self.ui.radioButton_Second.isChecked():
            semester = 2
        else:
            self.ui.tableWidget_Hours.setRowCount(0)
            self.ui.listWidget_Subjects.clear()
            return

        try:
            curriculums = self.curriculum_service.get_curriculums_by_group_and_semester(group_name, semester)

            self.ui.tableWidget_Hours.setRowCount(0)

            for row_data in curriculums:
                subject_name = row_data[4]  
                total_hour = row_data[2]    
                row_position = self.ui.tableWidget_Hours.rowCount()
                self.ui.tableWidget_Hours.insertRow(row_position)

                self.ui.tableWidget_Hours.setItem(row_position, 0, QTableWidgetItem(str(subject_name)))
                self.ui.tableWidget_Hours.setItem(row_position, 1, QTableWidgetItem(str(total_hour)))

            # Загрузка данных из бд
            all_subjects_from_db = [s[0] for s in self.subject_service.get_all_subjects()]
            subjects_in_table = []
            for row in range(self.ui.tableWidget_Hours.rowCount()):
                item = self.ui.tableWidget_Hours.item(row, 0)
                if item:
                    subjects_in_table.append(item.text())

            subjects_not_in_table = [s for s in all_subjects_from_db if s not in subjects_in_table]

            self.ui.listWidget_Subjects.clear()
            self.ui.listWidget_Subjects.addItems(subjects_not_in_table)

        except Exception as e:
            print(f"Произошла ошибка при загрузке данных для группы {group_name} и семестра {semester}: {e}")
            
    def apply_changes(self):
        """
        Синхронизирует данные из tableWidget_Hours с БД.
        Удаляет старые записи для группы и семестра, добавляет новые из таблицы.
        """
        group_name = self.ui.comboBox_Groups.currentText()
        if not group_name:
            QMessageBox.information(self, "Не выбрана группа. Невозможно сохранить данные.")
            return

        if self.ui.radioButton_First.isChecked():
            semester = 1
        elif self.ui.radioButton_Second.isChecked():
            semester = 2
        else:
            return

        try:
            old_curriculums = self.curriculum_service.get_curriculums_by_group_and_semester(group_name, semester)
            for curriculum in old_curriculums:
                curriculum_id = curriculum[0]  
                self.curriculum_service.delete_curriculum(curriculum_id)

            for row in range(self.ui.tableWidget_Hours.rowCount()):
                item_subject = self.ui.tableWidget_Hours.item(row, 0)
                item_hour = self.ui.tableWidget_Hours.item(row, 1)

                if not item_subject or not item_hour:
                    continue  

                subject_name = item_subject.text().strip()
                total_hour_str = item_hour.text().strip()

                if not subject_name or not total_hour_str:
                    continue  

                try:
                    total_hour = int(total_hour_str) 
                except ValueError:
                    QMessageBox.information(self, f"Некорректное значение часов для предмета '{subject_name}': {total_hour_str}")
                    continue

                # Создаём новую запись в БД
                self.curriculum_service.create_curriculum(
                    semester=semester,
                    total_hour=total_hour,
                    group_name=group_name,
                    subject_name=subject_name
                )
            QMessageBox.information(self, "Успех", f"Данные для группы '{group_name}' и семестра {semester} успешно сохранены.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при сохранении данных: {e}")


class SubjectDialog(ThemedDialog):
    def __init__(self, theme_manager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Subject()
        self.ui.setupUi(self)

        self.subject_service = SubjectDAO()

        self.on_theme_changed(self.theme_manager.get_theme())
        self.update_icons()

        self.load_subjects()

        # Подключение сигналов
        self.ui.listWidget_Subjects.itemSelectionChanged.connect(self.on_subject_selected)
        self.ui.comboBox_Subjects.currentTextChanged.connect(self.on_combo_text_changed)

        self.ui.btn_AddLine.clicked.connect(self.add_empty_row)
        self.ui.btn_RemoveLine.clicked.connect(self.remove_empty_row)

        self.ui.listWidget_Subjects.itemChanged.connect(self.on_list_item_changed)

        self.ui.btn_Update.clicked.connect(self.update_subject)
        self.ui.btn_Delete.clicked.connect(self.delete_subject)
        self.ui.btn_Accept.clicked.connect(self.accept_and_sync)
        self.ui.btn_Cancel.clicked.connect(self.close)
    
    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_RemoveLine'):
            self.ui.btn_RemoveLine.setIcon(QIcon(self.theme_manager.get_icon_path("remove")))
        if hasattr(self.ui, 'btn_AddLine'):
            self.ui.btn_AddLine.setIcon(QIcon(self.theme_manager.get_icon_path("add")))
        if hasattr(self.ui, 'btn_Delete'):
            self.ui.btn_Delete.setIcon(QIcon(self.theme_manager.get_icon_path('delete')))
        if hasattr(self.ui, 'btn_Update'):
            self.ui.btn_Update.setIcon(QIcon(self.theme_manager.get_icon_path('refresh')))
    
    def accept_and_sync(self):
        """
        Синхронизирует список групп в QListWidget с базой данных
        Удаляет из БД группы, отсутствующие в списке, и добавляет в БД группы, отсутствующие в БД
        """
        errors_occurred = False
        error_messages = []
        
        list_widget_names = set()
        for i in range(self.ui.listWidget_Subjects.count()):
            item = self.ui.listWidget_Subjects.item(i)
            name = item.text().strip()
            if name: 
                list_widget_names.add(name.lower()) 

        try:
            db_subjects_raw = self.subject_service.get_all_subjects()
            db_names = set()
            for subject_tuple in db_subjects_raw:
                db_name = subject_tuple[0]
                db_names.add(db_name.lower()) 
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить список дисциплин из базы данных: {e}")
            return

        print(f"[DEBUG] Список из UI (lower): {list_widget_names}")
        print(f"[DEBUG] Список из БД (lower): {db_names}")

        names_to_delete = db_names - list_widget_names
        names_to_add = list_widget_names - db_names

        for name_lower in names_to_delete:
            original_name_for_deletion = None
            for subject_tuple in db_subjects_raw:
                if subject_tuple[0].lower() == name_lower: 
                    original_name_for_deletion = subject_tuple[0] 
                    break

            if original_name_for_deletion:
                result = self.subject_service.delete_subject(original_name_for_deletion)
                if result is None:
                    error_msg = f"Не удалось удалить дисциплину '{original_name_for_deletion}' из базы данных."
                    print(f"Ошибка: {error_msg}")
                    error_messages.append(error_msg)
                    errors_occurred = True
                else:
                    print(f"Дисциплина '{original_name_for_deletion}' успешно удалена из БД.")

        for name_lower in names_to_add:
            original_name_for_addition = None
            for i in range(self.ui.listWidget_Subjects.count()):
                item = self.ui.listWidget_Subjects.item(i)
                if item.text().strip().lower() == name_lower:
                    original_name_for_addition = item.text().strip()
                    break

            if original_name_for_addition:
                result = self.subject_service.create_subject(original_name_for_addition)
                if result is None:
                    error_msg = f"Не удалось создать дисциплину '{original_name_for_addition}' в базе данных."
                    print(f"Ошибка: {error_msg}")
                    error_messages.append(error_msg)
                    errors_occurred = True
                else:
                    print(f"Дисциплина '{original_name_for_addition}' успешно добавлена в БД.")

        if errors_occurred:
            error_details = "\n".join(error_messages)
            QMessageBox.warning(self, "Часть данных не синхронизирована", f"Произошли ошибки при синхронизации:\n{error_details}\n\n.")
        else:
            QMessageBox.information(self, "Успешно", f"Список дисциплин синхронизирован с базой данных.\nУдалено: {len(names_to_delete)}, добавлено: {len(names_to_add)}.")

        self.load_subjects() 

    def count_empty_items(self):
        """
        Вспомогательный метод для подсчёта пустых элементов в QListWidget
        """
        count = 0
        for i in range(self.ui.listWidget_Subjects.count()):
            if not self.ui.listWidget_Subjects.item(i).text().strip():
                count += 1
        return count

    def delete_subject(self):
        """
        Удаляет выбранную дисциплину из QListWidget и QComboBox
        Использует текущий текст QComboBox как имя удаляемой группы
        """
        name_to_delete = self.ui.comboBox_Subjects.currentText().strip()

        if not name_to_delete:
            QMessageBox.warning(self, "Ошибка", "Не выбрана дисциплина для удаления.")
            return

        list_count = self.ui.listWidget_Subjects.count()
        item_found_in_list = False
        for i in range(list_count - 1, -1, -1): 
            list_item = self.ui.listWidget_Subjects.item(i)
            if list_item.text().strip().lower() == name_to_delete.lower():
                self.ui.listWidget_Subjects.takeItem(i) 
                item_found_in_list = True
                break 

        combo_index_to_delete = self.ui.comboBox_Subjects.findText(name_to_delete, Qt.MatchFlag.MatchExactly)
        if combo_index_to_delete >= 0:
            self.ui.comboBox_Subjects.removeItem(combo_index_to_delete)

        self.update_completer()

    def update_subject(self):
        """
        Обновляет имя дисциплины в QListWidget и QComboBox.
        Использует текущий текст QComboBox как старое имя и текст QLineEdit как новое имя.
        """
        old_name = self.ui.comboBox_Subjects.currentText().strip()

        if not old_name:
            QMessageBox.warning(self, "Ошибка", "Не выбрана дисциплина для обновления.")
            return

        new_name = self.ui.lineEdit_Subjects.text().strip()

        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Новое имя дисциплины не может быть пустым.")
            return

        if new_name.lower() == old_name.lower():
            QMessageBox.information(self, "Информация", "Новое имя совпадает со старым.")
            return

        list_count = self.ui.listWidget_Subjects.count()
        for i in range(list_count):
            list_item = self.ui.listWidget_Subjects.item(i)
            list_text = list_item.text().strip()
            if list_text.lower() == new_name.lower() and list_text.lower() != old_name.lower():
                QMessageBox.warning(self, "Ошибка", f"Дисциплина '{new_name}' уже существует в списке (регистр не учитывается).")
                return

        combo_count = self.ui.comboBox_Subjects.count()
        for i in range(combo_count):
            combo_text = self.ui.comboBox_Subjects.itemText(i).strip()
            if combo_text.lower() == new_name.lower() and combo_text.lower() != old_name.lower():
                QMessageBox.warning(self, "Ошибка", f"Дисциплина '{new_name}' уже существует в списке выбора (регистр не учитывается).")
                return

        for i in range(list_count):
            list_item = self.ui.listWidget_Subjects.item(i)
            if list_item.text().strip().lower() == old_name.lower():
                list_item.setText(new_name)
                break 

        combo_index_to_update = self.ui.comboBox_Subjects.findText(old_name, Qt.MatchFlag.MatchExactly)
        if combo_index_to_update >= 0:
            self.ui.comboBox_Subjects.removeItem(combo_index_to_update)
            self.ui.comboBox_Subjects.insertItem(combo_index_to_update, new_name)
            
            self.ui.comboBox_Subjects.setCurrentIndex(combo_index_to_update)

        self.update_completer()
    
    def on_combo_text_changed(self, current_text):
        index_in_combo = self.ui.comboBox_Subjects.findText(current_text, Qt.MatchFlag.MatchExactly)

        if index_in_combo >= 0: 
            self.ui.lineEdit_Subjects.setText(current_text)
        else:
            self.ui.lineEdit_Subjects.clear()

    def on_list_item_changed(self, item):
        """
        Обработчик сигнала itemChanged, срабатывающего при изменении текста элемента списка.
        Проверяет уникальность текста (без учёта регистра) и добавляет в QComboBox при успехе.
        """
        if not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            return

        original_text = item.text()
        new_text = original_text.strip()
        if not new_text:  
            count = self.ui.listWidget_Subjects.count()
            index = self.ui.listWidget_Subjects.indexFromItem(item).row()
            if index == count - 1:
                self.ui.listWidget_Subjects.takeItem(index)
            return

        new_text_lower = new_text.lower()

        list_widget_items_lower = []
        for i in range(self.ui.listWidget_Subjects.count()):
            list_item = self.ui.listWidget_Subjects.item(i)
            if list_item != item:  
                list_text = list_item.text().strip().lower()  
                list_widget_items_lower.append(list_text)

        if new_text_lower in list_widget_items_lower:
            QMessageBox.warning(self, "Ошибка", f"Дисциплина '{new_text}' уже существует в списке (регистр не учитывается).")
            item.setText("")  
            return

        # --- Проверка в QComboBox ---
        combo_count = self.ui.comboBox_Subjects.count()
        for i in range(combo_count):
            combo_text = self.ui.comboBox_Subjects.itemText(i).strip().lower()
            if combo_text == new_text_lower:
                QMessageBox.warning(self, "Ошибка", f"Дисциплина '{new_text}' уже существует в списке выбора (регистр не учитывается).")
                item.setText("") 
                return

        # --- Успешное добавление ---
        self.ui.comboBox_Subjects.addItem(new_text)
        self.update_completer()
        
        current_flags = item.flags()
        item.setFlags(current_flags & ~Qt.ItemFlag.ItemIsEditable)

    def update_completer(self):
        """
        Обновляет QCompleter QComboBox, чтобы он знал о текущем списке элементов.
        """
        combo_items = [self.ui.comboBox_Subjects.itemText(i) for i in range(self.ui.comboBox_Subjects.count())]

        completer = QCompleter(combo_items, self.ui.comboBox_Subjects)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)

        self.ui.comboBox_Subjects.setCompleter(completer)

    def add_empty_row(self):
        count = self.ui.listWidget_Subjects.count()
        if count == 0:
            return
        
        new_item = QListWidgetItem("") 
        new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
        new_item.setData(Qt.ItemDataRole.BackgroundRole, QPalette.ColorRole.AlternateBase)
        self.ui.listWidget_Subjects.addItem(new_item)

    def remove_empty_row(self):
        count = self.ui.listWidget_Subjects.count()
        if count == 0:
            return

        last_item = self.ui.listWidget_Subjects.item(count - 1)
        if last_item.text().strip() == "":
            self.ui.listWidget_Subjects.takeItem(count - 1)

    def load_subjects(self):
        try:
            self.ui.listWidget_Subjects.clear()

            subjects = self.subject_service.get_all_subjects()
            for subject in subjects:
                # Добавление элемента в QListWidget
                self.ui.listWidget_Subjects.addItem(subject[0])
                # Добавление элемента в QComboBox
                self.ui.comboBox_Subjects.addItem(subject[0])

            self.ui.comboBox_Subjects.setCurrentIndex(-1)
        except Exception as e:
            print(f"Произошла ошибка при загрузке дисциплин: {e}")  

    
    def on_subject_selected(self):
        selected_subjects = self.ui.listWidget_Subjects.selectedItems()
        if selected_subjects:
            selected_subject_name = selected_subjects[0].text()

            index_in_combo = self.ui.comboBox_Subjects.findText(selected_subject_name)
            if index_in_combo >= 0:
                self.ui.comboBox_Subjects.setCurrentIndex(index_in_combo)

            self.ui.lineEdit_Subjects.setText(selected_subject_name)
        else:
            self.ui.lineEdit_Subjects.clear()
        
        
class GroupDialog(ThemedDialog):
    def __init__(self, theme_manager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Group()
        self.ui.setupUi(self)

        self.group_service = GroupDAO()

        self.on_theme_changed(self.theme_manager.get_theme())
        self.update_icons()

        self.load_groups()

        # Подключение сигналов
        self.ui.listWidget_Groups.itemSelectionChanged.connect(self.on_group_selected)
        self.ui.comboBox_Groups.currentTextChanged.connect(self.on_combo_text_changed)

        self.ui.btn_AddLine.clicked.connect(self.add_empty_row)
        self.ui.btn_RemoveLine.clicked.connect(self.remove_empty_row)

        self.ui.listWidget_Groups.itemChanged.connect(self.on_list_item_changed)

        self.ui.btn_Update.clicked.connect(self.update_group)
        self.ui.btn_Delete.clicked.connect(self.delete_group)
        self.ui.btn_Accept.clicked.connect(self.accept_and_sync)
        self.ui.btn_Cancel.clicked.connect(self.close)
    
    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_RemoveLine'):
            self.ui.btn_RemoveLine.setIcon(QIcon(self.theme_manager.get_icon_path("remove")))
        if hasattr(self.ui, 'btn_AddLine'):
            self.ui.btn_AddLine.setIcon(QIcon(self.theme_manager.get_icon_path("add")))
        if hasattr(self.ui, 'btn_Delete'):
            self.ui.btn_Delete.setIcon(QIcon(self.theme_manager.get_icon_path('delete')))
        if hasattr(self.ui, 'btn_Update'):
            self.ui.btn_Update.setIcon(QIcon(self.theme_manager.get_icon_path('refresh')))
    
    def accept_and_sync(self):
        """
        Синхронизирует список групп в QListWidget с базой данных
        Удаляет из БД группы, отсутствующие в списке, и добавляет в БД группы, отсутствующие в БД
        """
        errors_occurred = False
        error_messages = []
        
        list_widget_names = set()
        for i in range(self.ui.listWidget_Groups.count()):
            item = self.ui.listWidget_Groups.item(i)
            name = item.text().strip()
            if name: 
                list_widget_names.add(name.lower()) 

        try:
            db_groups_raw = self.group_service.get_all_groups()
            db_names = set()
            for group_tuple in db_groups_raw:
                db_name = group_tuple[0]
                db_names.add(db_name.lower()) 
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить список групп из базы данных: {e}")
            return

        print(f"[DEBUG] Список из UI (lower): {list_widget_names}")
        print(f"[DEBUG] Список из БД (lower): {db_names}")

        names_to_delete = db_names - list_widget_names
        names_to_add = list_widget_names - db_names

        for name_lower in names_to_delete:
            original_name_for_deletion = None
            for group_tuple in db_groups_raw:
                if group_tuple[0].lower() == name_lower: 
                    original_name_for_deletion = group_tuple[0] 
                    break

            if original_name_for_deletion:
                result = self.group_service.delete_group(original_name_for_deletion)
                if result is None:
                    error_msg = f"Не удалось удалить группу '{original_name_for_deletion}' из базы данных."
                    print(f"Ошибка: {error_msg}")
                    error_messages.append(error_msg)
                    errors_occurred = True
                else:
                    print(f"Группа '{original_name_for_deletion}' успешно удалена из БД.")

        for name_lower in names_to_add:
            original_name_for_addition = None
            for i in range(self.ui.listWidget_Groups.count()):
                item = self.ui.listWidget_Groups.item(i)
                if item.text().strip().lower() == name_lower:
                    original_name_for_addition = item.text().strip()
                    break

            if original_name_for_addition:
                result = self.group_service.create_group(original_name_for_addition)
                if result is None:
                    error_msg = f"Не удалось создать группу '{original_name_for_addition}' в базе данных."
                    print(f"Ошибка: {error_msg}")
                    error_messages.append(error_msg)
                    errors_occurred = True
                else:
                    print(f"Группа '{original_name_for_addition}' успешно добавлена в БД.")

        if errors_occurred:
            error_details = "\n".join(error_messages)
            QMessageBox.warning(self, "Часть данных не синхронизирована", f"Произошли ошибки при синхронизации:\n{error_details}\n\nСм. лог для подробностей.")
        else:
            QMessageBox.information(self, "Успешно", f"Список групп синхронизирован с базой данных.\nУдалено: {len(names_to_delete)}, добавлено: {len(names_to_add)}.")

        self.load_groups() 

    def count_empty_items(self):
        """
        Вспомогательный метод для подсчёта пустых элементов в QListWidget
        """
        count = 0
        for i in range(self.ui.listWidget_Groups.count()):
            if not self.ui.listWidget_Groups.item(i).text().strip():
                count += 1
        return count

    def delete_group(self):
        """
        Удаляет выбранную группу из QListWidget и QComboBox
        Использует текущий текст QComboBox как имя удаляемой группы
        """
        name_to_delete = self.ui.comboBox_Groups.currentText().strip()

        if not name_to_delete:
            QMessageBox.warning(self, "Ошибка", "Не выбрана группа для удаления.")
            return

        list_count = self.ui.listWidget_Groups.count()
        item_found_in_list = False
        for i in range(list_count - 1, -1, -1): 
            list_item = self.ui.listWidget_Groups.item(i)
            if list_item.text().strip().lower() == name_to_delete.lower():
                self.ui.listWidget_Groups.takeItem(i) 
                item_found_in_list = True
                break 

        combo_index_to_delete = self.ui.comboBox_Groups.findText(name_to_delete, Qt.MatchFlag.MatchExactly)
        if combo_index_to_delete >= 0:
            self.ui.comboBox_Groups.removeItem(combo_index_to_delete)

        self.update_completer()

    def update_group(self):
        """
        Обновляет имя группы в QListWidget и QComboBox.
        Использует текущий текст QComboBox как старое имя и текст QLineEdit как новое имя.
        """
        old_name = self.ui.comboBox_Groups.currentText().strip()

        if not old_name:
            QMessageBox.warning(self, "Ошибка", "Не выбрана группа для обновления.")
            return

        new_name = self.ui.lineEdit_group.text().strip()

        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Новое имя группы не может быть пустым.")
            return

        if new_name.lower() == old_name.lower():
            QMessageBox.information(self, "Информация", "Новое имя совпадает со старым.")
            return

        list_count = self.ui.listWidget_Groups.count()
        for i in range(list_count):
            list_item = self.ui.listWidget_Groups.item(i)
            list_text = list_item.text().strip()
            if list_text.lower() == new_name.lower() and list_text.lower() != old_name.lower():
                QMessageBox.warning(self, "Ошибка", f"Группа '{new_name}' уже существует в списке (регистр не учитывается).")
                return

        combo_count = self.ui.comboBox_Groups.count()
        for i in range(combo_count):
            combo_text = self.ui.comboBox_Groups.itemText(i).strip()
            if combo_text.lower() == new_name.lower() and combo_text.lower() != old_name.lower():
                QMessageBox.warning(self, "Ошибка", f"Группа '{new_name}' уже существует в списке выбора (регистр не учитывается).")
                return

        for i in range(list_count):
            list_item = self.ui.listWidget_Groups.item(i)
            if list_item.text().strip().lower() == old_name.lower():
                list_item.setText(new_name)
                break 

        combo_index_to_update = self.ui.comboBox_Groups.findText(old_name, Qt.MatchFlag.MatchExactly)
        if combo_index_to_update >= 0:
            self.ui.comboBox_Groups.removeItem(combo_index_to_update)
            self.ui.comboBox_Groups.insertItem(combo_index_to_update, new_name)
            
            self.ui.comboBox_Groups.setCurrentIndex(combo_index_to_update)

        self.update_completer()
    
    def on_combo_text_changed(self, current_text):
        index_in_combo = self.ui.comboBox_Groups.findText(current_text, Qt.MatchFlag.MatchExactly)

        if index_in_combo >= 0: 
            self.ui.lineEdit_group.setText(current_text)
        else:
            self.ui.lineEdit_group.clear()

    def on_list_item_changed(self, item):
        """
        Обработчик сигнала itemChanged, срабатывающего при изменении текста элемента списка.
        Проверяет уникальность текста (без учёта регистра) и добавляет в QComboBox при успехе.
        """
        if not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            return

        original_text = item.text()
        new_text = original_text.strip()
        if not new_text:  
            count = self.ui.listWidget_Groups.count()
            index = self.ui.listWidget_Groups.indexFromItem(item).row()
            if index == count - 1:
                self.ui.listWidget_Groups.takeItem(index)
            return

        new_text_lower = new_text.lower()

        list_widget_items_lower = []
        for i in range(self.ui.listWidget_Groups.count()):
            list_item = self.ui.listWidget_Groups.item(i)
            if list_item != item:  
                list_text = list_item.text().strip().lower()  
                list_widget_items_lower.append(list_text)

        if new_text_lower in list_widget_items_lower:
            QMessageBox.warning(self, "Ошибка", f"Группа '{new_text}' уже существует в списке (регистр не учитывается).")
            item.setText("")  
            return

        # --- Проверка в QComboBox ---
        combo_count = self.ui.comboBox_Groups.count()
        for i in range(combo_count):
            combo_text = self.ui.comboBox_Groups.itemText(i).strip().lower()
            if combo_text == new_text_lower:
                QMessageBox.warning(self, "Ошибка", f"Группа '{new_text}' уже существует в списке выбора (регистр не учитывается).")
                item.setText("") 
                return

        # --- Успешное добавление ---
        self.ui.comboBox_Groups.addItem(new_text)
        self.update_completer()
        
        current_flags = item.flags()
        item.setFlags(current_flags & ~Qt.ItemFlag.ItemIsEditable)

    def update_completer(self):
        """
        Обновляет QCompleter QComboBox, чтобы он знал о текущем списке элементов.
        """
        combo_items = [self.ui.comboBox_Groups.itemText(i) for i in range(self.ui.comboBox_Groups.count())]

        completer = QCompleter(combo_items, self.ui.comboBox_Groups)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)

        self.ui.comboBox_Groups.setCompleter(completer)

    def add_empty_row(self):
        count = self.ui.listWidget_Groups.count()
        if count == 0:
            return
        
        new_item = QListWidgetItem("") 
        new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
        new_item.setData(Qt.ItemDataRole.BackgroundRole, QPalette.ColorRole.AlternateBase)
        self.ui.listWidget_Groups.addItem(new_item)

    def remove_empty_row(self):
        count = self.ui.listWidget_Groups.count()
        if count == 0:
            return

        last_item = self.ui.listWidget_Groups.item(count - 1)
        if last_item.text().strip() == "":
            self.ui.listWidget_Groups.takeItem(count - 1)

    def load_groups(self):
        try:
            self.ui.listWidget_Groups.clear()

            groups = self.group_service.get_all_groups()
            for group in groups:
                # Добавление элемента в QListWidget
                self.ui.listWidget_Groups.addItem(group[0])
                # Добавление элемента в QComboBox
                self.ui.comboBox_Groups.addItem(group[0])

            self.ui.comboBox_Groups.setCurrentIndex(-1)
        except Exception as e:
            print(f"Произошла ошибка при загрузке групп: {e}")  

    
    def on_group_selected(self):
        selected_group = self.ui.listWidget_Groups.selectedItems()
        if selected_group:
            selected_group_name = selected_group[0].text()

            index_in_combo = self.ui.comboBox_Groups.findText(selected_group_name)
            if index_in_combo >= 0:
                self.ui.comboBox_Groups.setCurrentIndex(index_in_combo)

            self.ui.lineEdit_group.setText(selected_group_name)
        else:
            self.ui.lineEdit_group.clear()

    
# === NewYearDialog ===
class NewYearDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_NewYear()
        self.ui.setupUi(self)

        self.setup_tree_widgets()

        # Создаём объекты классов сервисов для БД
        self.group_service = GroupDAO()
        self.subject_service = SubjectDAO()
        self.curriculum_service = CurriculumDAO()

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())

        self.load_info()

        # Добавляем обработчики кнопок
        self.ui.btn_Accept.clicked.connect(self.accept_info)

    def accept_info(self):
        """Функция принятия данных, введённых в treeWidget"""
        current_semester = self.ui.tabWidget.currentIndex()
        # Получаем текущий treeWidget в зависимости от выбранного полугодия
        current_tree_widget = self.ui.treeW_firstHalf if current_semester == 0 else self.ui.treeW_SecondHalf

        all_data = self.get_all_items_with_parent(current_tree_widget)
        print(all_data)

        # Инициализируем флаги для отслеживания результата работы добавления
        add_group_status = False
        add_subject_status = False

        # Получаем
        items_with_parent = self.get_all_items_with_parent(current_tree_widget)
        for entry in items_with_parent:
            current_item = entry['item']  # ('текст1', 'текст2', ...)
            parent_item = entry['parent']  # QTreeWidgetItem или None

            # Если нет родителя - то это группа
            if parent_item is None:
                new_group_name = current_item[0] # Получаем имя группы
                # Добавляем новую группу в бд
                new_group = self.group_service.create_group(new_group_name)

                # Проверяем, добавилась ли группа
                if not new_group is None:
                    # Меняем статус группы
                    add_group_status = True
                    msg = QMessageBox(QMessageBox.Icon.Information, "Группа успешно добавлена", "", QMessageBox.StandardButton.Ok, self)
                    msg.exec()

            elif parent_item:
                new_subject_name = current_item[0] # Получение имени группы
                new_subject = self.subject_service.create_subject(new_subject_name)  # Создание новой группы

                if not new_subject is None:
                    # Меняем статус группы
                    add_subject_status = True
                    msg = QMessageBox(QMessageBox.Icon.Information, "Предмет успешно добавлен", "", QMessageBox.StandardButton.Ok, self)
                    msg.exec()
                
                new_curriculum = self.curriculum_service.create_curriculum(semester=current_semester, total_hour=current_item[1], group_name=parent_item.text(0), subject_name=current_item[0])

    def get_all_items_with_parent(self, tree_widget):
        """Возвращает список всех элементов с указанием родителя"""
        data = []
        root = tree_widget.invisibleRootItem()

        def traverse_item(item, parent_item=None):
            # Добавляем текущий элемент и его родителя
            row_data = []
            for j in range(tree_widget.columnCount()):
                text = item.text(j)
                row_data.append(text)

            # Сохраняем: (данные, родительский элемент)
            data.append({
                'item': tuple(row_data),
                'parent': parent_item
            })

            # Рекурсивно обходим дочерние элементы
            for i in range(item.childCount()):
                child = item.child(i)
                traverse_item(child, item)  # передаём текущий item как родителя

        # Начинаем с корневых элементов (у них родителя нет)
        for i in range(root.childCount()):
            item = root.child(i)
            traverse_item(item)

        return data

    def load_info(self):
        ''' Функция загрузки плана из бд '''
        # Загружаем данные для первого семестра (0) в treeW_firstHalf
        semester_0_info = self.get_curriculum_hierarchy_by_semester(semester=0)
        self._load_and_expand_tree(self.ui.treeW_firstHalf, semester_0_info)

        # Загружаем данные для второго семестра (1) в treeW_SecondHalf
        semester_1_info = self.get_curriculum_hierarchy_by_semester(semester=1)
        self._load_and_expand_tree(self.ui.treeW_SecondHalf, semester_1_info)

    def _load_and_expand_tree(self, tree_widget, semester_data):
        """
        Вспомогательная функция для загрузки данных в tree_widget и разворачивания корневых элементов.
        """
        tree_widget.clear()
        for group_info in semester_data:
            group_item = QTreeWidgetItem(tree_widget)
            group_item.setText(0, group_info["name"])
            for subject_info in group_info["subjects"]:
                subject_item = QTreeWidgetItem(group_item)
                subject_item.setText(0, subject_info["name"])
                subject_item.setText(1, subject_info["hours"])

        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            tree_widget.expandItem(item)

    def get_curriculum_hierarchy_by_semester(self, semester):
        """
        Возвращает иерархический список групп и предметов для указанного семестра.

        Returns:
            list: Список словарей, каждый содержит:
                - 'name': имя группы
                - 'subjects': список словарей с 'name' и 'hours'
        """
        # Получаем все записи для семестра
        curriculums = self.curriculum_service.get_curriculums_by_semester(semester)

        # Группируем по group_name
        groups_dict = {}

        for row in curriculums:
            # row[0] = id, row[1] = semester, row[2] = total_hour, row[3] = group_name, row[4] = subject_name
            group_name = row[3]
            subject_name = row[4]
            total_hour = str(row[2])  # Приводим к строке для отображения

            if group_name not in groups_dict:
                groups_dict[group_name] = {
                    "name": group_name,
                    "subjects": []
                }

            groups_dict[group_name]["subjects"].append({
                "name": subject_name,
                "hours": total_hour
            })

        # Преобразуем в список
        return list(groups_dict.values())

    def setup_tree_widgets(self):
        """ Setup QTreeWidget."""
        tree_widgets = [self.ui.treeW_firstHalf, self.ui.treeW_SecondHalf]
        for tree_widget in tree_widgets:
            tree_widget.setEditTriggers(
                QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
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
        new_item.setText(0, "")  # empty row for title
        new_item.setText(1, "")  # empty row for hours
        return new_item

    def on_item_changed(self, item, column):
        """
        Обработчик сигнала itemChanged.
        Вызывается, когда пользователь изменяет текст в элементе.
        """
        tree_widget = item.treeWidget()
        # if column == 0 and item.text(0).strip():
        #     parent = item.parent()
        #     if parent:
        #         if parent.indexOfChild(item) == parent.childCount() - 1:
        #             self.add_empty_subject(tree_widget, parent)
        #     else:
        #         if tree_widget.indexOfTopLevelItem(item) == tree_widget.topLevelItemCount() - 1:
        #             self.add_empty_group(tree_widget)

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
    def __init__(self, theme_manager: ThemeManager, curriculum_dao, initial_selected_groups=None, initial_selected_subjects=None):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Filter()
        self.ui.setupUi(self)

        # Сохраняем DAO для получения данных
        self.curriculum_dao = curriculum_dao

        # Сохраняем изначально выбранные значения для восстановления
        self.initial_selected_groups = initial_selected_groups or set()
        self.initial_selected_subjects = initial_selected_subjects or set()

        # Атрибуты для хранения выбранных значений при закрытии
        self.selected_groups = set()
        self.selected_subjects = set()

        # Подключаем кнопки
        self.ui.btn_Cancel.clicked.connect(self.reject)
        self.ui.btn_Accept.clicked.connect(self.on_accept_clicked)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())

        # Загружаем данные и восстанавливаем выбор
        self.load_filter_data()
        self.restore_selection()

    def load_filter_data(self):
        """Загружает все уникальные группы и предметы в списки."""
        try:
            all_curriculums = self.curriculum_dao.get_all_curriculums()

            groups = set()
            subjects = set()
            for curriculum in all_curriculums:
                groups.add(curriculum[3]) # group_name
                subjects.add(curriculum[4]) # subject_name

            sorted_groups = sorted(list(groups))
            sorted_subjects = sorted(list(subjects))

            # Заполняем списки
            self.ui.listW_groups.clear()
            for group_name in sorted_groups:
                item = QListWidgetItem(group_name)
                # item.setCheckState(QtCore.Qt.CheckState.Unchecked) # Больше не нужно
                self.ui.listW_groups.addItem(item)

            self.ui.listW_groups_2.clear()
            for subject_name in sorted_subjects:
                item = QListWidgetItem(subject_name)
                # item.setCheckState(QtCore.Qt.CheckState.Unchecked) # Больше не нужно
                self.ui.listW_groups_2.addItem(item)

        except Exception as e:
            print(f"Ошибка при загрузке данных для фильтра: {e}")

    def restore_selection(self):
        """Восстанавливает выбранные элементы в списках."""
        # Выбираем элементы в списке групп
        for i in range(self.ui.listW_groups.count()):
            item = self.ui.listW_groups.item(i)
            if item.text() in self.initial_selected_groups:
                item.setSelected(True)

        # Выбираем элементы в списке предметов
        for i in range(self.ui.listW_groups_2.count()):
            item = self.ui.listW_groups_2.item(i)
            if item.text() in self.initial_selected_subjects:
                item.setSelected(True)

    def on_accept_clicked(self):
        """Обработчик нажатия кнопки 'Фильтровать'."""
        # Собираем выбранные элементы
        self.selected_groups = {item.text() for item in self.ui.listW_groups.selectedItems()}
        self.selected_subjects = {item.text() for item in self.ui.listW_groups_2.selectedItems()}

        print(f"Выбраны группы: {self.selected_groups}")
        print(f"Выбраны предметы: {self.selected_subjects}")

        self.accept()


# === about ===
class AboutWindow(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_about()
        self.ui.setupUi(self)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())


class ReportDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager, report_data: list):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Report()
        self.ui.setupUi(self)

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())

        # Подключаем кнопку закрытия
        self.ui.btn_close.clicked.connect(self.close)

        # Заполняем таблицу данными
        self.populate_report_table(report_data)

    def populate_report_table(self, report_data):
        """Заполняет таблицу отчёта данными."""
        self.ui.treeW_report.setRowCount(len(report_data))
        self.ui.treeW_report.setColumnCount(4)

        for row_index, (group_name, subject_name, total_hour, sum_of_hours) in enumerate(report_data):
            # Группа
            item_group = QTableWidgetItem(group_name)
            item_group.setFlags(item_group.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.ui.treeW_report.setItem(row_index, 0, item_group)

            # Дисциплина
            item_subject = QTableWidgetItem(subject_name)
            item_subject.setFlags(item_subject.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.ui.treeW_report.setItem(row_index, 1, item_subject)

            # Проведено ч. (сумма)
            item_hours_done = QTableWidgetItem(str(sum_of_hours))
            item_hours_done.setFlags(item_hours_done.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.ui.treeW_report.setItem(row_index, 2, item_hours_done)

            # Остаток ч. (план - проведено)
            remaining_hours = total_hour - sum_of_hours
            item_hours_remaining = QTableWidgetItem(str(remaining_hours))
            item_hours_remaining.setFlags(item_hours_remaining.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.ui.treeW_report.setItem(row_index, 3, item_hours_remaining)

        table_widget = self.ui.treeW_report
        header = table_widget.horizontalHeader()

        # Устанавливаем стратегию изменения размера для каждого столбца
        for i in range(4):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        table_widget.updateGeometry()

        fm = header.fontMetrics() # Используем fontMetrics заголовка

        for i in range(4):
            header_item = table_widget.horizontalHeaderItem(i)
            if header_item:
                # Текст заголовка
                header_text = header_item.text()
                # Измеряем ширину текста заголовка
                header_text_width = fm.horizontalAdvance(header_text)

                min_width = header_text_width + 10 # Добавляем небольшой отступ

                header.setMinimumSectionSize(min_width)
                current_size = header.sectionSize(i)
                if current_size < min_width:
                    header.resizeSection(i, min_width) # Устанавливаем размер, если он меньше минимума

        # Обновляем геометрию ещё раз после установки минимальных размеров
        table_widget.updateGeometry()


# === MainWindow ===
class MainWindow(ThemedWindow):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.work_day_dao = WorkDayDAO()
        self.curriculum_dao = CurriculumDAO()
        
        self.current_group_filter = set() # Изначально пустой фильтр
        self.current_subject_filter = set() # Изначально пустой фильтр
        
        self.table_date_mapping = {} # Добавьте эту строку

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
        
        # Переменная текущего года
        self.first_half_year = date.today().year

        # Подключаем радиокнопки
        self.ui.rBtn_First.toggled.connect(self.on_half_changed)
        self.ui.rBtn_Second.toggled.connect(self.on_half_changed)

        # Инициализируем начальное состояние — "Первое" полугодие активно
        self.on_half_changed()
        QTimer.singleShot(0, self.update_table_sizes)

        self.ui.tabW_SlidesFirstHalf.currentChanged.connect(self.on_tab_changed)

        # Connection menu
        self.ui.light.triggered.connect(lambda: self.theme_manager.set_theme("light"))
        self.ui.dark.triggered.connect(lambda: self.theme_manager.set_theme("dark"))
        self.ui.blue.triggered.connect(lambda: self.theme_manager.set_theme("blue"))
        self.ui.about.triggered.connect(lambda: self.open_aboutWindow())

        # Apply start theme
        self.on_theme_changed(self.theme_manager.get_theme())

        # Connect buttons
        if hasattr(self.ui, 'btn_NewYear'):
            self.ui.btn_NewYear.clicked.connect(self.open_new_year_dialog)
        if hasattr(self.ui, 'btn_Filt'):
            self.ui.btn_Filt.clicked.connect(self.open_filter_dialog)
        if hasattr(self.ui, 'btn_Sort'):
            self.ui.btn_Sort.clicked.connect(self.open_sort_dialog)
        if hasattr(self.ui, 'btn_Report'):
            self.ui.btn_Report.clicked.connect(self.open_report_dialog)
        if hasattr(self.ui, 'btn_Group'):
            self.ui.btn_Group.clicked.connect(self.open_group_dialog)
        if hasattr(self.ui, 'btn_Subject'):
            self.ui.btn_Subject.clicked.connect(self.open_subject_dialog)
        if hasattr(self.ui, 'btn_Default'):
            self.ui.btn_Default.clicked.connect(self.on_reset_clicked)
        if hasattr(self.ui, 'btn_Search'):
            self.ui.btn_Search.clicked.connect(self.on_search_clicked)

        # Initialize table widgets - hide headers if needed
        self.initialize_table_widgets()
        
        # Подключаем обработчики сигналов для таблиц
        self.setup_table_connections()
        
        QTimer.singleShot(0, self.load_and_display_work_days)

    def initialize_table_widgets(self):
        """Initialize properties for all QTableWidget instances."""
        # Список всех виджетов вкладок и соответствующих table widgets
        tables_data = [
            (self.ui.tab_September, self.ui.tableV_hours_1),
            (self.ui.tab_October, self.ui.tableV_hours_4),
            (self.ui.tab_November, self.ui.tableV_hours_2),
            (self.ui.tab_December, self.ui.tableV_hours_3),
            (self.ui.tab_5, self.ui.tableV_hours_5),
            (self.ui.tab_6, self.ui.tableV_hours_6),
        ]

        for tab_widget, table_widget in tables_data:
            # Example: Hide headers if needed
            table_widget.verticalHeader().setVisible(False)
            # table_widget.horizontalHeader().setVisible(False) # Uncomment if you want to hide horizontal headers too

    @pyqtSlot(str)
    def on_theme_changed(self, theme: str):
        """Call when theme switched"""
        self.setStyleSheet(self.theme_manager.get_stylesheet())
        self.update_icons()

        QTimer.singleShot(0, self.update_table_sizes)
        
    def load_and_display_work_days(self):
        """Загружает данные из БД и строит таблицы для текущего полугодия/семестра."""
        # print("Загрузка данных рабочих дней и учебных планов...")
        try:
            # Получить все записи из БД (для работы с ними)
            all_work_days = self.work_day_dao.get_all_work_days()
            # print(f"Найдено {len(all_work_days)} записей рабочих дней.")

            # Определить текущий семестр на основе выбранного полугодия
            current_semester = 1 if self.ui.rBtn_First.isChecked() else 2
            # print(f"Текущий семестр: {current_semester}")

            # Получить все учебные планы для текущего семестра
            curriculums_for_semester = self.curriculum_dao.get_curriculums_by_semester(current_semester)
            # print(f"Найдено {len(curriculums_for_semester)} учебных планов для семестра {current_semester}.")
            
            if self.current_group_filter or self.current_subject_filter:
                filtered_curriculums = []
                for curriculum in curriculums_for_semester:
                    group_name = curriculum[3]
                    subject_name = curriculum[4]
                    # Проверяем, проходит ли запись фильтр
                    group_ok = not self.current_group_filter or group_name in self.current_group_filter
                    subject_ok = not self.current_subject_filter or subject_name in self.current_subject_filter
                    if group_ok and subject_ok:
                        filtered_curriculums.append(curriculum)
                curriculums_for_semester = filtered_curriculums
                print(f"После фильтрации осталось {len(curriculums_for_semester)} учебных планов.")

            # Создать маппинг между метками месяцев и виджетами таблиц
            is_first_half = self.ui.rBtn_First.isChecked()
            current_months_data = self.first_half if is_first_half else self.second_half
            current_year = self.first_half_year if is_first_half else self.first_half_year + 1

            month_label_to_table = self.get_month_label_to_table_map() # Используем метод, определенный ниже
            
            table_widgets_to_load = []
            for month_label in [label for num, label in current_months_data]:
                table_widget = month_label_to_table.get(month_label)
                if table_widget:
                    table_widget.blockSignals(True) # Блокируем сигналы
                    table_widgets_to_load.append(table_widget)

            # Для каждого месяца в текущем полугодии
            for month_num, month_label in current_months_data:
                table_widget = month_label_to_table.get(month_label)
                if not table_widget:
                    continue # Пропускаем, если таблица не найдена

                # Очистить таблицу перед заполнением
                table_widget.setRowCount(0)
                table_widget.setColumnCount(0)

                # Создаем объект данных для календаря
                calendar_data = CalendarTableData(current_year, month_num)
                # Сохраняем mapping дат для этой таблицы
                self.table_date_mapping[table_widget] = calendar_data.dates

                # Создать список дней месяца (для шапки) - только не-воскресенья
                day_list = [dt.strftime("%d") for dt in calendar_data.dates] # Берем из отфильтрованного списка

                # Установить заголовки столбцов: Группа, Предмет, Дни месяца (без воскресений)
                headers = ["Группа", "Предмет"] + day_list
                table_widget.setColumnCount(len(headers))
                table_widget.setHorizontalHeaderLabels(headers)

                # Заполнить строки данными из учебных планов
                for curriculum in curriculums_for_semester:
                    group_name = curriculum[3]  # group_name
                    subject_name = curriculum[4] # subject_name

                    # Добавить новую строку
                    row_position = table_widget.rowCount()
                    table_widget.insertRow(row_position)

                    item_group = QTableWidgetItem(group_name)
                    table_widget.setItem(row_position, 0, item_group)

                    item_subject = QTableWidgetItem(subject_name)
                    table_widget.setItem(row_position, 1, item_subject)
                    # print(f"  Добавляем строку для Группа='{group_name}', Предмет='{subject_name}' на позицию {row_position}")

                    for col_index, target_date in enumerate(calendar_data.dates, start=2): # Перебираем даты, а не строки
                        # Найти запись workDay для этой группы, предмета и даты
                        found_hours = None
                        for wd in all_work_days:
                            wd_date = datetime.strptime(wd[1], "%Y-%m-%d").date()
                            wd_subject = wd[2]
                            wd_group = wd[3]
                            wd_semester = wd[4]

                            if (wd_group == group_name and
                                wd_subject == subject_name and
                                wd_date == target_date and # Сравниваем с target_date из calendar_data.dates
                                wd_semester == current_semester):
                                found_hours = wd[5]
                                break

                        item_hours = QTableWidgetItem(str(found_hours) if found_hours is not None else "")
                        table_widget.setItem(row_position, col_index, item_hours)

                # После заполнения всех строк обновить размеры
                table_widget.resizeColumnsToContents()
                table_widget.resizeRowsToContents()
            
            for table_widget in table_widgets_to_load:
                table_widget.blockSignals(False) # Разблокируем сигналы

        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            return

        # После загрузки всех данных обновите размеры таблиц
        self.update_table_sizes()
        # print("Данные успешно загружены и отображены.")
        
    def add_record_to_table(self, table_widget, record):
        """Добавляет одну запись в указанную таблицу."""
        # record - это кортеж (id, date, subject_name, group_name, semester, hours)
        row_position = table_widget.rowCount()
        table_widget.insertRow(row_position)
        
        # Заполняем ячейки данными из кортежа
        for col_index, data in enumerate(record):
            item = QTableWidgetItem(str(data)) # Преобразуем всё к строке для простоты
            table_widget.setItem(row_position, col_index, item)

    def clear_all_tables(self):
        """Очищает все таблицы."""
        table_widgets = [
            self.ui.tableV_hours_1,
            self.ui.tableV_hours_4,
            self.ui.tableV_hours_2,
            self.ui.tableV_hours_3,
            self.ui.tableV_hours_5,
            self.ui.tableV_hours_6,
        ]
        for table_widget in table_widgets:
            table_widget.setRowCount(0)
        # print("Все таблицы очищены.")
        
    def get_half_year_date_range(self, is_first_half: bool = True):
        """
        Определяет диапазон дат для первого или второго полугодия текущего учебного года.
        
        Args:
            is_first_half: Если True, возвращает диапазон для первого полугодия (Сент-Дек),
                          иначе для второго полугодия (Янв-Июнь)
        
        Returns:
            tuple: (start_date, end_date) - кортеж с начальной и конечной датами полугодия
        """
        current_year = self.first_half_year
        
        if is_first_half:
            # Первое полугодие: сентябрь-декабрь текущего года
            start_month, start_label = self.first_half[0]
            end_month, end_label = self.first_half[-1]
            
            start_date = date(current_year, start_month, 1)
            # Последний день месяца
            _, last_day = calendar.monthrange(current_year, end_month)
            end_date = date(current_year, end_month, last_day)
        else:
            next_year = current_year + 1
            start_month, start_label = self.second_half[0]
            end_month, end_label = self.second_half[-1]
            
            start_date = date(next_year, start_month, 1)
            # Последний день месяца
            _, last_day = calendar.monthrange(next_year, end_month)
            end_date = date(next_year, end_month, last_day)
        
        return start_date, end_date

    def count_weekends_in_half_year(self, is_first_half: bool = True):
        """
        Подсчитывает количество выходных дней (воскресений) в указанном полугодии.
        
        Args:
            is_first_half: Если True, подсчитывает для первого полугодия,
                          иначе для второго полугодия
        
        Returns:
            int: Количество воскресений в указанном полугодии
        """
        start_date, end_date = self.get_half_year_date_range(is_first_half)
        
        weekend_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # weekday() возвращает 6 для воскресенья
            if current_date.weekday() == 6:
                weekend_count += 1
            current_date += timedelta(days=1)
        
        return weekend_count

    @pyqtSlot()
    def on_half_changed(self):
        """Общий обработчик изменения полугодия"""
        if self.ui.rBtn_First.isChecked():
            setup_calendar_tables_for_half(self.ui, year=self.first_half_year, months_data=self.first_half)
        elif self.ui.rBtn_Second.isChecked():
            # Для второго полугодия используем следующий год
            next_year = self.first_half_year + 1
            setup_calendar_tables_for_half(self.ui, year=next_year, months_data=self.second_half)

        self.update_table_sizes()
        self.ui.line_Search.clear()
        
        QTimer.singleShot(0, self.load_and_display_work_days)

    def on_tab_changed(self, index):
        """Вызывается при переключении вкладки"""
        # Обновляем размеры только для текущей вкладки
        current_tab = self.ui.tabW_SlidesFirstHalf.currentWidget()
        # Find the specific table widget for the current tab
        table_widget = self.get_table_widget_for_tab(current_tab)
        if table_widget:
            table_widget.resizeColumnsToContents()
            table_widget.resizeRowsToContents()
            table_widget.updateGeometry()
        
        QTimer.singleShot(0, self.load_and_display_work_days)

    def get_table_widget_for_tab(self, tab):
        """Helper function to get the table widget for a given tab."""
        # Map tabs to their corresponding table widgets based on the UI setup
        tab_to_table = {
            self.ui.tab_September: self.ui.tableV_hours_1,
            self.ui.tab_October: self.ui.tableV_hours_4,
            self.ui.tab_November: self.ui.tableV_hours_2,
            self.ui.tab_December: self.ui.tableV_hours_3,
            self.ui.tab_5: self.ui.tableV_hours_5,
            self.ui.tab_6: self.ui.tableV_hours_6,
        }
        return tab_to_table.get(tab)
    
    def on_search_clicked(self):
        """Обработчик нажатия кнопки поиска."""
        search_text = self.ui.line_Search.text().strip().lower() 
        print(f"Поиск по запросу: '{search_text}'")
        self.apply_search_filter(search_text)
    
    def get_month_label_to_table_map(self):
        """Возвращает словарь соответствия меток месяцев виджетам таблиц."""
        is_first_half = self.ui.rBtn_First.isChecked()
        if is_first_half:
            return {
                "Сент": self.ui.tableV_hours_1,
                "Окт": self.ui.tableV_hours_4,
                "Нояб": self.ui.tableV_hours_2,
                "Декаб": self.ui.tableV_hours_3,
            }
        else: # Второе полугодие
            return {
                "Янв": self.ui.tableV_hours_1,
                "Фев": self.ui.tableV_hours_4,
                "Март": self.ui.tableV_hours_2,
                "Апр": self.ui.tableV_hours_3,
                "Май": self.ui.tableV_hours_5,
                "Июнь": self.ui.tableV_hours_6,
            }

    def update_table_sizes(self):
        """Обновляет размеры всех QTableWidget в виджетах вкладок"""
        # Список всех table widgets
        table_widgets = [
            self.ui.tableV_hours_1,
            self.ui.tableV_hours_4,
            self.ui.tableV_hours_2,
            self.ui.tableV_hours_3,
            self.ui.tableV_hours_5,
            self.ui.tableV_hours_6,
        ]

        for table_widget in table_widgets:
            table_widget.resizeColumnsToContents()
            table_widget.resizeRowsToContents()
            table_widget.updateGeometry()
            
    def apply_search_filter(self, search_text: str):
        """
        Применяет фильтр поиска к строкам таблиц.
        Скрывает строки, не содержащие search_text.
        """
        # Получаем список таблиц для текущего полугодия (аналогично load_and_display_work_days)
        is_first_half = self.ui.rBtn_First.isChecked()
        current_months_data = self.first_half if is_first_half else self.second_half
        # current_year = self.first_half_year if is_first_half else self.first_half_year + 1 # Не нужен тут

        month_label_to_table = self.get_month_label_to_table_map()

        # Проходим по всем таблицам, соответствующим текущему полугодию
        for month_label in [label for num, label in current_months_data]:
            table_widget = month_label_to_table.get(month_label)
            if not table_widget:
                continue

            # Проходим по всем строкам в таблице
            for row in range(table_widget.rowCount()):
                # Получаем данные из первых двух столбцов (Группа, Предмет)
                item_group = table_widget.item(row, 0)
                item_subject = table_widget.item(row, 1)

                group_text = item_group.text().lower() if item_group else ""
                subject_text = item_subject.text().lower() if item_subject else ""

                # Поиск по группе или предмету
                if search_text in group_text or search_text in subject_text:
                    table_widget.showRow(row) # Показываем строку, если совпадение найдено
                    continue # Переходим к следующей строке

                # Поиск по часам (данные в столбцах с 2 и далее)
                found_in_hours = False
                for col in range(2, table_widget.columnCount()):
                    item_hours = table_widget.item(row, col)
                    if item_hours:
                        hours_text = item_hours.text().lower()
                        if search_text in hours_text:
                             found_in_hours = True
                             break # Нашли совпадение в одном из столбцов часов, выходим из цикла по столбцам

                if found_in_hours:
                    table_widget.showRow(row) # Показываем строку, если совпадение найдено в часах
                else:
                    table_widget.hideRow(row) # Скрываем строку, если совпадений не найдено

        self.update_table_sizes()
            
    def setup_table_connections(self):
        """Подключает сигнал cellChanged ко всем таблицам."""
        table_widgets = [
            self.ui.tableV_hours_1,
            self.ui.tableV_hours_4,
            self.ui.tableV_hours_2,
            self.ui.tableV_hours_3,
            self.ui.tableV_hours_5,
            self.ui.tableV_hours_6,
        ]

        for table_widget in table_widgets:
            # Подключаем сигнал к общему обработчику
            table_widget.cellChanged.connect(self.on_cell_changed)
    
    def on_cell_changed(self, row, col):
        """Обработчик изменения ячейки в любой таблице."""
        sender = self.sender() # Получаем QTableWidget, который вызвал сигнал

        if not isinstance(sender, QTableWidget):
            # print(f"on_cell_changed вызван не для QTableWidget, а для {type(sender)}. Игнорируем.")
            return

        if col < 2:
            return

        # Получаем текст из ячейки
        item = sender.item(row, col)
        if item is None:
            new_text = ""
        else:
            new_text = item.text().strip()

        # Получаем список дат для текущей таблицы
        if sender not in self.table_date_mapping:
            # print("Ошибка: Не найдены даты для таблицы.")
            self.show_error_message("Произошла ошибка при обработке данных.")
            return

        filtered_dates = self.table_date_mapping[sender]
        date_index = col - 2
        if date_index < 0 or date_index >= len(filtered_dates):
            #  print(f"Ошибка: Индекс столбца {col} вне диапазона отфильтрованных дат.")
             self.show_error_message("Произошла ошибка при обработке данных.")
             return

        target_date = filtered_dates[date_index]

        # Определяем семестр
        is_first_half = self.ui.rBtn_First.isChecked()
        current_semester = 1 if is_first_half else 2

        # Получаем группу и предмет из строки
        item_group = sender.item(row, 0)
        item_subject = sender.item(row, 1)

        # Проверяем, существуют ли ячейки и содержат ли они непустой текст
        if item_group is None or item_subject is None:
            return

        group_name = item_group.text().strip()
        subject_name = item_subject.text().strip()

        if not group_name or not subject_name:
            return

        # Валидация числового значения
        if new_text == "":
            try:
                existing_records = self.work_day_dao.get_work_days_by_date(target_date)
                for record in existing_records:
                    if record[3] == group_name and record[2] == subject_name and record[4] == current_semester:
                        self.work_day_dao.delete_work_day(record[0])
                        break
            except Exception as e:
                self.show_error_message(f"Ошибка при удалении данных: {e}")
            return # Завершаем обработку, если значение пустое

        try:
            hours_float = float(new_text) # Позволим вводить дробные числа
            if hours_float < 0:
                raise ValueError("Часы не могут быть отрицательными.")
        except ValueError:
            # Значение не является числом или отрицательное
            item.setText("") 
            self.show_error_message("Значение должно быть числом (часы).")
            return
        
        try:
            # Проверим, существует ли уже запись для этой даты, группы, предмета и семестра
            existing_records = self.work_day_dao.get_work_days_by_date(target_date)
            found_existing = False
            for record in existing_records:
                if record[3] == group_name and record[2] == subject_name and record[4] == current_semester:
                    # Обновляем существующую запись
                    updated_record = self.work_day_dao.update_work_day(
                        record[0], # id
                        date=target_date.isoformat(),
                        subject_name=subject_name,
                        group_name=group_name,
                        semester=current_semester,
                        hours=hours_float
                    )
                    if updated_record:
                        print(f"Обновлена запись: {updated_record}")
                    else:
                        print(f"Не удалось обновить запись с id {record[0]}")
                    found_existing = True
                    break

            if not found_existing:
                # Вставляем новую запись
                new_record = self.work_day_dao.create_work_day(
                    date=target_date.isoformat(),
                    subject_name=subject_name,
                    group_name=group_name,
                    semester=current_semester,
                    hours=hours_float
                )
                if new_record:
                    print(f"Создана новая запись: {new_record}")
                else:
                    print("Не удалось создать новую запись.")
        except Exception as e:
            print(f"Ошибка при обновлении/вставке записи в БД: {e}")
            self.show_error_message(f"Ошибка при сохранении данных: {e}")

    def show_error_message(self, message):
        """Показывает окно с сообщением об ошибке."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical) # Иконка ошибки
        msg_box.setWindowTitle("Ошибка")
        msg_box.setText(message)
        msg_box.exec() # Показать модально

    def on_reset_clicked(self):
        """Handler for the 'Сброс' button."""
        # Сброс фильтров по группам и предметам
        self.current_group_filter = set()
        self.current_subject_filter = set()

        # Сброс строки поиска
        self.ui.line_Search.clear()

        # Сброс фильтра поиска (скрытые строки)
        self.ui.line_Search.clear()

        self.on_half_changed()

    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_Search'):
            self.ui.btn_Search.setIcon(QIcon(self.theme_manager.get_icon_path("search")))
        if hasattr(self.ui, 'btn_Filt'):
            self.ui.btn_Filt.setIcon(QIcon(self.theme_manager.get_icon_path("filter")))
        if hasattr(self.ui, 'btn_Report'):
            self.ui.btn_Report.setIcon(QIcon(self.theme_manager.get_icon_path("report")))
        if hasattr(self.ui, 'btn_NewYear'):
            self.ui.btn_NewYear.setIcon(QIcon(self.theme_manager.get_icon_path("new_year")))
        if hasattr(self.ui, 'btn_Default'):
            self.ui.btn_Default.setIcon(QIcon(self.theme_manager.get_icon_path("refresh")))
        if hasattr(self.ui, 'btn_Group'):
            self.ui.btn_Group.setIcon(QIcon(self.theme_manager.get_icon_path("group")))
        if hasattr(self.ui, 'btn_Subject'):
            self.ui.btn_Subject.setIcon(QIcon(self.theme_manager.get_icon_path("subject")))

    def open_new_year_dialog(self):
        dialog = YearEditDialog(self.theme_manager)
        dialog.exec()

    def open_filter_dialog(self):
        dialog = FilterDialog(
            self.theme_manager,
            self.curriculum_dao,
            initial_selected_groups=self.current_group_filter, # Передаем текущие фильтры
            initial_selected_subjects=self.current_subject_filter
        )
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Сохраняем новые фильтры
            self.current_group_filter = dialog.selected_groups.copy()
            self.current_subject_filter = dialog.selected_subjects.copy()
            print(f"Фильтры обновлены в MainWindow: Группы={self.current_group_filter}, Предметы={self.current_subject_filter}")
            # Перезагружаем данные с учетом фильтров
            QTimer.singleShot(0, self.load_and_display_work_days)
        # Если пользователь нажал "Отменить", фильтры остаются неизменными
        
    def get_report_data(self):
        """
        Подготавливает данные для отчёта: (group_name, subject_name, total_hour_plan, sum_of_hours_done).
        Учитывает текущие фильтры по группам и предметам.
        """
        # Определить текущий семестр
        current_semester = 1 if self.ui.rBtn_First.isChecked() else 2

        # Получить все учебные планы для текущего семестра
        curriculums_for_semester = self.curriculum_dao.get_curriculums_by_semester(current_semester)

        # Фильтруем учебные планы по текущим фильтрам
        if self.current_group_filter or self.current_subject_filter:
            filtered_curriculums = []
            for curriculum in curriculums_for_semester:
                group_name = curriculum[3]
                subject_name = curriculum[4]
                group_ok = not self.current_group_filter or group_name in self.current_group_filter
                subject_ok = not self.current_subject_filter or subject_name in self.current_subject_filter
                if group_ok and subject_ok:
                    filtered_curriculums.append(curriculum)
            curriculums_for_semester = filtered_curriculums

        all_work_days = self.work_day_dao.get_all_work_days()

        # Подготовить итоговый список
        report_data = []

        for curriculum in curriculums_for_semester:
            # curriculum - это (id, semester, total_hour, group_name, subject_name)
            curriculum_id = curriculum[0]
            semester = curriculum[1]
            total_hour = curriculum[2]
            group_name = curriculum[3]
            subject_name = curriculum[4]

            # Суммируем часы для этой группы и предмета в этом семестре
            sum_of_hours = 0
            for work_day in all_work_days:
                # work_day - это (id, date_str, subject_name, group_name, semester, hours)
                wd_subject = work_day[2]
                wd_group = work_day[3]
                wd_semester = work_day[4]
                wd_hours = work_day[5]

                if (wd_group == group_name and wd_subject == subject_name and
                    wd_semester == current_semester):
                    sum_of_hours += wd_hours

            report_data.append((group_name, subject_name, total_hour, sum_of_hours))

        return report_data

    def open_report_dialog(self):
        report_data = self.get_report_data()

        dialog = ReportDialog(self.theme_manager, report_data)
        dialog.exec()

    def open_aboutWindow(self):
        dialog = AboutWindow(self.theme_manager)
        dialog.exec()

    def open_group_dialog(self):
        dialog = GroupDialog(self.theme_manager)
        dialog.exec()
        
    def open_subject_dialog(self):
        dialog = SubjectDialog(self.theme_manager)
        dialog.exec()



if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create themeManager
    theme_manager = ThemeManager()

    # Create MainWindow
    window = MainWindow(theme_manager)
    window.show()

    sys.exit(app.exec())

