import sys
import os
import configparser
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QDialog, QTreeWidgetItem, QMenu, QMessageBox, QListWidget, QListWidgetItem, QCompleter
from PyQt6.QtGui import QIcon, QPalette
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt

from ui.mainWindow import Ui_MainWindow
from ui.newYearDialog import Ui_Dialog_NewYear
from ui.filterDialog import Ui_Dialog_Filter
from ui.sortDialog import Ui_Dialog_Sort
from ui.about import Ui_about
from ui.reportDialog import Ui_Dialog_Report
from ui.groupDialog import Ui_Dialog_Group
from calendar_helper import setup_calendar_tables_for_half

from services.group_services import GroupDAO
from services.curriculum_services import CurriculumDAO
from services.subject_services import SubjectDAO


# === ThemeManager ===
class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # theme switch signal

    def __init__(self):
        super().__init__()
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
                return f.read()
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
    
    def update_icons(self):
        """Update icons when theme switched"""
        if hasattr(self.ui, 'btn_RemoveLine'):
            self.ui.btn_RemoveLine.setIcon(QIcon(self.theme_manager.get_icon_path("remove")))
        if hasattr(self.ui, 'btn_AddLine'):
            self.ui.btn_AddLine.setIcon(QIcon(self.theme_manager.get_icon_path("add")))
    
    def accept_and_sync(self):
        """
        Синхронизирует список групп в QListWidget с базой данных.
        Удаляет из БД группы, отсутствующие в списке, и добавляет в БД группы, отсутствующие в БД.
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
        Вспомогательный метод для подсчёта пустых элементов в QListWidget.
        """
        count = 0
        for i in range(self.ui.listWidget_Groups.count()):
            if not self.ui.listWidget_Groups.item(i).text().strip():
                count += 1
        return count

    def delete_group(self):
        """
        Удаляет выбранную группу из QListWidget и QComboBox.
        Использует текущий текст QComboBox как имя удаляемой группы.
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


class ReportDialog(ThemedDialog):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__(theme_manager)
        self.ui = Ui_Dialog_Report()
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
        # Connect button "Report"
        if hasattr(self.ui, 'btn_Report'):
            self.ui.btn_Report.clicked.connect(self.open_report_dialog)
        # Connect button "Group"
        if hasattr(self.ui, 'btn_Group'):
            self.ui.btn_Group.clicked.connect(self.open_group_dialog)

        for i in range(self.ui.tabW_SlidesFirstHalf.count()):
            table_view = self.ui.tabW_SlidesFirstHalf.widget(i).findChild(QtWidgets.QTableView)
            if table_view:
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

    def open_report_dialog(self):
        dialog = ReportDialog(self.theme_manager)
        dialog.exec()

    def open_aboutWindow(self):
        dialog = AboutWindow(self.theme_manager)
        dialog.exec()

    def open_group_dialog(self):
        dialog = GroupDialog(self.theme_manager)
        dialog.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create themeManager
    theme_manager = ThemeManager()

    # Create MainWindow
    window = MainWindow(theme_manager)
    window.show()

    sys.exit(app.exec())
