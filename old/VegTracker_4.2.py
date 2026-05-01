import csv
import sys
import uuid
import json
import os
import webbrowser
from datetime import datetime, timedelta, date
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QAbstractItemView,
    QHeaderView,
    QFrame,
    QDialog,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QMessageBox,
    QLineEdit,
    QDateEdit,
    QStackedWidget,
    QMenu,
    QInputDialog,
    QSplitter,
    QLayout,
    QStyledItemDelegate,
    QTextEdit,
)
from PyQt6.QtCore import QRect, Qt, QTimer, QDate, QPoint, QSize
from PyQt6.QtGui import QColor, QCursor, QFont, QAction


SAVE_FILE = "calendar_data.json"


STYLE = """
QMainWindow, QWidget { background-color: #1a1a1a; color: #e0e0e0; }
QTableWidget { background-color: #202020; gridline-color: #333333; border: 1px solid #333333; outline: none; }
QHeaderView::section { background-color: #252525; color: #aaaaaa; padding: 6px; border: 1px solid #1a1a1a; }
QFrame#StatsPanel { background-color: #1a1a1a; border-left: 1px solid #333333; min-width: 110px; }
QPushButton { background-color: #303030; color: white; border: 1px solid #404040; padding: 8px; border-radius: 4px; }
QPushButton#ToggleBtn { background-color: #252525; border: 1px solid #333333; color: #888; font-weight: bold; border-radius: 0px; }
QPushButton#IconBtn { background-color: #2a2a2a; border: 1px solid #444; font-size: 14px; }
QPushButton#EraserBtn:checked { background-color: #d32f2f; border: 2px solid #ffcdd2; }
QPushButton#ViewToggle { background-color: #2e7d32; font-weight: bold; }
QLineEdit, QComboBox, QDateEdit { background-color: #252525; border: 1px solid #444; color: white; padding: 5px; }
QSplitter::handle { background-color: #333333; width: 2px; }
"""

# Вспомогательный класс. Позволяет вводить многострочный текст в ячейках таблицы
class MultiLineDelegate(QStyledItemDelegate):
    # Создает текстовое поле редактора
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        return editor

    # Загружает текст из таблицы в редактор
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setPlainText(str(value or ""))

    # Сохраняет введенный текст обратно в таблицу
    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

# Автоматически переносит кнопки на новую строку (умная сетка)
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.items = []

    def __del__(self):
        del self.items

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size

    # Расставляет элементы слева направо с переносом строк
    def _do_layout(self, rect, test_only):
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self.items:
            next_x = x + item.sizeHint().width() + self.spacing()
            if next_x - self.spacing() > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self.spacing()
                next_x = x + item.sizeHint().width() + self.spacing()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()

# Окно создания или редактирования типа задачи
class TaskEditDialog(QDialog):
    # Формирует интерфейс настройки (код, имя, ссылка, цвет) + настройка UI
    def __init__(self, parent, task_data=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка задачи")
        self.setFixedWidth(350)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Код задачи (отображается в сетке):"))
        self.edit_code = QLineEdit()
        if task_data:
            self.edit_code.setText(task_data["code"])
        layout.addWidget(self.edit_code)

        layout.addWidget(QLabel("Полное название:"))
        self.edit_name = QLineEdit()
        if task_data:
            self.edit_name.setText(task_data["name"])
        layout.addWidget(self.edit_name)

        layout.addWidget(QLabel("Ссылка (URL):"))
        self.edit_url = QLineEdit()
        if task_data:
            self.edit_url.setText(task_data.get("url", ""))
        layout.addWidget(self.edit_url)

        layout.addWidget(QLabel("Статус задачи:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["В работе", "Завершена"])
        if task_data:
            self.combo_status.setCurrentText(task_data.get("status", "В работе"))
        layout.addWidget(self.combo_status)

        layout.addWidget(QLabel("ID в Яндекс Трекере (напр. TASK-123):"))
        self.edit_tracker_id = QLineEdit()
        if task_data:
            self.edit_tracker_id.setText(task_data.get("tracker_id", ""))
        layout.addWidget(self.edit_tracker_id)

        layout.addWidget(QLabel("Тип задачи:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Tracker", "Fix", "Support", "ETC"])
        if task_data:
            self.combo_type.setCurrentText(task_data.get("task_type", "ETC"))
        layout.addWidget(self.combo_type)

        self.selected_color = QColor(task_data["color"] if task_data else "#7E57C2")
        self.btn_color = QPushButton("Выбрать цвет")
        self.update_btn_color()
        self.btn_color.clicked.connect(self.pick_color)
        layout.addWidget(self.btn_color)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Сохранить")
        self.btn_ok.clicked.connect(self.validate)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.result_task = (
            task_data.copy() if task_data else {"id": str(uuid.uuid4())[:8]}
        )

    # Обновляет цвет на кнопке выбора
    def update_btn_color(self):
        self.btn_color.setStyleSheet(
            f"background-color: {self.selected_color.name()}; color: white;"
        )

    # Открывает палитру для выбора цвета задачи
    def pick_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Цвет задачи")
        if color.isValid():
            self.selected_color = color
            self.update_btn_color()

    # Проверяет ошибки и сохраняет данные задачи
    def validate(self):
        code, name = self.edit_code.text().strip(), self.edit_name.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Ошибка", "Заполните Код и Название!")
            return
        self.result_task.update(
            {
                "name": name,
                "code": code,
                "url": self.edit_url.text().strip(),
                "tracker_id": self.edit_tracker_id.text().strip(),
                "color": self.selected_color.name(),
                "status": self.combo_status.currentText() if hasattr(self, 'combo_status') else "В работе",
                "task_type": self.combo_type.currentText()
            }
        )
        self.accept()


class RecurringTaskDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Создать правило повтора")
        self.setFixedWidth(450)
        self.setStyleSheet(STYLE)
        self.parent = parent
        layout = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(10, 10, 10, 10)

        grid.addWidget(QLabel("Задача:"), 0, 0)
        self.task_combo = QComboBox()
        for t in parent.tasks_data:
            if t.get("status") != "Завершена":
                self.task_combo.addItem(f"[{t['code']}] {t['name']}", t["id"])
        grid.addWidget(self.task_combo, 0, 1, 1, 3)

        grid.addWidget(QLabel("Повтор:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Еженедельно", "Ежемесячно"])
        self.type_combo.currentIndexChanged.connect(self.toggle_ui)
        grid.addWidget(self.type_combo, 1, 1, 1, 3)

        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit(QDate.currentDate().addMonths(1))
        self.end_date.setCalendarPopup(True)

        grid.addWidget(QLabel("Дата начала:"), 2, 0)
        grid.addWidget(self.start_date, 2, 1)
        grid.addWidget(QLabel("Дата окончания:"), 2, 2, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.end_date, 2, 3)

        times = [f"{h:02}:{m:02}" for h in range(24) for m in (0, 30)]
        self.start_time, self.end_time = QComboBox(), QComboBox()
        self.start_time.setEditable(True)
        self.start_time.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_time.lineEdit().setReadOnly(True)
        self.end_time.setEditable(True)
        self.end_time.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.end_time.lineEdit().setReadOnly(True)
        self.start_time.addItems(times)
        self.end_time.addItems(times)

        grid.addWidget(QLabel("Время начала:"), 3, 0)
        grid.addWidget(self.start_time, 3, 1)
        grid.addWidget(QLabel("Время окончания:"), 3, 2, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.end_time, 3, 3)

        layout.addLayout(grid)

        self.days_widget = QWidget()
        days_lay = QHBoxLayout(self.days_widget)
        days_lay.setContentsMargins(0, 0, 0, 0)
        self.day_cbs = []
        for name in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
            cb = QCheckBox(name)
            days_lay.addWidget(cb)
            self.day_cbs.append(cb)
        layout.addWidget(self.days_widget)

        self.btn_apply = QPushButton("Запланировать")
        self.btn_apply.setMinimumHeight(40)
        self.btn_apply.clicked.connect(self.apply_rule)
        layout.addWidget(self.btn_apply)

        self.toggle_ui()

    def toggle_ui(self):
        is_weekly = self.type_combo.currentIndex() == 0
        self.days_widget.setVisible(is_weekly)

    def get_nth_weekday_of_month(self, year, month, target_weekday, n):
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()
        days_to_add = (target_weekday - first_weekday) % 7
        target_date = first_day + timedelta(days=days_to_add) + timedelta(weeks=n - 1)
        if target_date.month == month:
            return target_date
        return None

    def apply_rule(self):
        s_date, e_date = (
            self.start_date.date().toPyDate(),
            self.end_date.date().toPyDate(),
        )
        tid = self.task_combo.currentData()
        sh, sm = map(int, self.start_time.currentText().split(":"))
        eh, em = map(int, self.end_time.currentText().split(":"))
        s_slot, e_slot = (
            sh * 2 + (1 if sm == 30 else 0),
            eh * 2 + (1 if em == 30 else 0),
        )

        rule_id = f"rule_{str(uuid.uuid4())[:8]}"
        self.parent.rules_data[rule_id] = {
            "desc": f"{self.task_combo.currentText()} ({self.start_time.currentText()}-{self.end_time.currentText()}) - {self.type_combo.currentText()}"
        }

        if self.type_combo.currentIndex() == 0:
            current = s_date
            while current <= e_date:
                if self.day_cbs[current.weekday()].isChecked():
                    self.parent.bulk_add_to_history(
                        current, s_slot, e_slot, tid, rule_id
                    )
                current += timedelta(days=1)

        else:
            target_weekday = s_date.weekday()

            first_day_start_month = date(s_date.year, s_date.month, 1)
            first_target = first_day_start_month + timedelta(
                days=(target_weekday - first_day_start_month.weekday()) % 7
            )
            week_number = (s_date.day - first_target.day) // 7 + 1

            current_month = s_date.replace(day=1)
            while current_month <= e_date:
                target_date = self.get_nth_weekday_of_month(
                    current_month.year, current_month.month, target_weekday, week_number
                )
                if target_date and s_date <= target_date <= e_date:
                    self.parent.bulk_add_to_history(
                        target_date, s_slot, e_slot, tid, rule_id
                    )

                next_month = current_month.month % 12 + 1
                next_year = current_month.year + (current_month.month // 12)
                current_month = date(next_year, next_month, 1)

        self.parent.save_to_disk()
        self.parent.setup_view()
        self.accept()


class VegCalendar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Veg Tracker 4.3")
        self.resize(1400, 900)
        self.setStyleSheet(STYLE)

        self.start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
        self.history, self.tasks_data, self.rules_data = {}, [], {}
        self.work_settings = {
            "active_days": [1, 1, 1, 1, 1, 0, 0],
            "start": "09:00",
            "end": "18:00",
            "color": "#3c1e3a5f",
            "show_weekends": True
        }
        self.current_task, self.eraser_mode = None, False

        self.load_from_disk()

        self.init_ui()

        if hasattr(self, "saved_widths") and self.saved_widths:
            for i, w in enumerate(self.saved_widths):
                self.mirror_table.setColumnWidth(i, w)
        else:
            self.mirror_table.setColumnWidth(0, 140)
            self.mirror_table.setColumnWidth(1, 280)
            self.mirror_table.setColumnWidth(2, 100)
            self.mirror_table.setColumnWidth(3, 60)  # Статус
            self.mirror_table.setColumnWidth(4, 500) # Комментарий

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        QTimer.singleShot(200, self.scroll_to_work)

    def adjust_mirror_rows(self):

        self.mirror_table.resizeRowsToContents()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        top_bar = QHBoxLayout()

        self.tasks_container = QWidget()

        self.btns_lay = FlowLayout(self.tasks_container, spacing=5)

        top_bar.addWidget(self.tasks_container, 1)

        self.btn_view_toggle = QPushButton("📋 Таблица-Отчет")
        self.btn_view_toggle.setCheckable(True)
        self.btn_view_toggle.setObjectName("ViewToggle")
        self.btn_view_toggle.clicked.connect(self.switch_view)
        top_bar.addWidget(self.btn_view_toggle)

        self.btn_eraser = QPushButton("🧹")
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.setObjectName("EraserBtn")
        self.btn_eraser.setFixedSize(40, 40)
        self.btn_eraser.clicked.connect(self.toggle_eraser)
        top_bar.addWidget(self.btn_eraser)

        for icon, cmd in [
            ("🔄", self.open_rules),
            ("🕒", self.open_work_settings),
            ("⚙", self.open_task_manager),
        ]:
            btn = QPushButton(icon)
            btn.setObjectName("IconBtn")
            btn.setFixedSize(40, 40)
            btn.clicked.connect(cmd)
            top_bar.addWidget(btn)

        self.btn_collapse = QPushButton("▶")
        self.btn_collapse.setObjectName("IconBtn")
        self.btn_collapse.setFixedSize(40, 40)
        self.btn_collapse.clicked.connect(self.toggle_stats_panel)
        top_bar.addWidget(self.btn_collapse)

        self.lbl_clock = QLabel()
        top_bar.addWidget(self.lbl_clock)
        self.main_layout.addLayout(top_bar)

        nav = QHBoxLayout()
        pb, nb = QPushButton("<"), QPushButton(">")
        self.lbl_range = QLabel()
        self.lbl_range.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        pb.clicked.connect(self.prev_w)
        nb.clicked.connect(self.next_w)
        nav.addStretch()
        nav.addWidget(pb)
        nav.addWidget(self.lbl_range)
        nav.addWidget(nb)
        nav.addStretch()
        self.main_layout.addLayout(nav)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.stack = QStackedWidget()

        self.table = QTableWidget(48, 8)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setMouseTracking(True)
        self.table.cellPressed.connect(self.on_cell_event)
        self.table.cellEntered.connect(self.on_cell_event)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.stack.addWidget(self.table)

        # Создаем таблицу-отчет: 0 строк, 5 колонок
        self.mirror_table = QTableWidget(0, 5) 
        
        # УСТАНАВЛИВАЕМ ПРАВИЛЬНЫЕ ЗАГОЛОВКИ (Статус перед Комментарием)
        self.mirror_table.setHorizontalHeaderLabels(
            ["Дата", "Задача", "Время", "Статус", "Комментарий"]
        )

        self.mirror_table.setWordWrap(True)
        self.mirror_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        header = self.mirror_table.horizontalHeader()
        header.sectionResized.connect(lambda: self.mirror_table.resizeRowsToContents())

        # НАСТРОЙКА ПОВЕДЕНИЯ КОЛОНОК
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Дата
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Задача
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Время
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)       # Статус (фиксированный)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)     # Комментарий (тянется)

        self.mirror_table.setMinimumWidth(0)
        self.stack.setMinimumWidth(0)

        # Делегат теперь для КОЛОНКИ 4 (Комментарий), чтобы текст переносился
        self.mirror_table.setItemDelegateForColumn(
            4, MultiLineDelegate(self.mirror_table)
        )
        
        self.mirror_table.itemChanged.connect(
            lambda: self.mirror_table.resizeRowsToContents()
        )
        self.mirror_table.cellDoubleClicked.connect(self.on_mirror_click)
        self.stack.addWidget(self.mirror_table)
        self.splitter.addWidget(self.stack)

        self.stats_panel = QFrame()
        self.stats_panel.setObjectName("StatsPanel")
        stats_main_layout = QVBoxLayout(self.stats_panel)
        stats_main_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")       
        self.stats_v = QVBoxLayout(scroll_content)
        self.stats_v.addWidget(QLabel("<b>📊 ДЕТАЛИЗАЦИЯ:</b>"))
        self.lbl_stats = QLabel()
        self.lbl_stats.setWordWrap(True)
        self.lbl_stats.setOpenExternalLinks(True)
        self.stats_v.addWidget(self.lbl_stats)
        self.stats_v.addStretch()
        scroll.setWidget(scroll_content)
        stats_main_layout.addWidget(scroll)

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(0, 45)

        self.splitter.addWidget(self.stats_panel)
        self.splitter.setSizes([1000, 110])

        self.main_layout.addWidget(self.splitter, 1)

        self.refresh_task_buttons()
        self.setup_view()

    def toggle_stats_panel(self):
        is_visible = self.stats_panel.isVisible()
        self.stats_panel.setVisible(not is_visible)
        self.btn_collapse.setText("◀" if not is_visible else "▶")

    def scroll_to_work(self):

        sh, sm = map(int, self.work_settings["start"].split(":"))

        idx = (sh * 2 + (1 if sm == 30 else 0)) + 1

        target_row = max(0, idx - 3)

        item = self.table.item(target_row, 1)
        if item:
            self.table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtTop)

    def switch_view(self):
        self.stack.setCurrentIndex(1 if self.btn_view_toggle.isChecked() else 0)
        self.setup_view()

    def setup_view(self):
        self.lbl_range.setText(
            f"{self.start_of_week.strftime('%d.%m')} — {(self.start_of_week + timedelta(days=6)).strftime('%d.%m.%Y')}"
        )
        if self.stack.currentIndex() == 0:
            self.setup_calendar()
        else:
            self.setup_mirror()

    def setup_calendar(self):
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.clearSpans()
        # 1. Определяем, какие дни нужно отображать
        show_weekends = self.work_settings.get("show_weekends", True)
        active_days = self.work_settings["active_days"]
        # Индексы реальных дней (1-7), которые попадут в таблицу
        visible_days = []
        headers = ["Time"]
        for i in range(7):
            if active_days[i] or show_weekends:
                visible_days.append(i + 1)
                headers.append((self.start_of_week + timedelta(days=i)).strftime("%a\n%d.%m"))
        # Устанавливаем динамическое кол-во колонок
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        sh, sm = map(int, self.work_settings["start"].split(":"))
        eh, em = map(int, self.work_settings["end"].split(":"))
        s_idx, e_idx = (sh * 2 + (1 if sm == 30 else 0)), (eh * 2 + (1 if em == 30 else 0))
        overlay = QColor(self.work_settings["color"])
        for r in range(48):
            time_item = QTableWidgetItem()
            if r % 2 == 0:
                time_item.setText(f"{r // 2:02}:00")
            time_item.setBackground(QColor("#252525"))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, time_item)
            # Заполняем только те колонки, которые мы решили отображать
            for visual_col, day_idx in enumerate(visible_days, 1):
                it = QTableWidgetItem()
                if not (active_days[day_idx - 1] and s_idx <= r < e_idx):
                    it.setBackground(overlay)
                self.table.setItem(r, visual_col, it)
        wid = self.get_week_id()
        hist = self.history.get(wid, {})
        lk = {t["id"]: t for t in self.tasks_data}
        for pos, data in hist.items():
            tid = data["tid"] if isinstance(data, dict) else data
            if tid in lk:
                r, c = map(int, pos.split(","))
                # Проверяем, отображается ли сейчас этот день в таблице
                if c in visible_days:
                    visual_col = visible_days.index(c) + 1
                    t = lk[tid]
                    item = QTableWidgetItem(f"[{t['code']}]")
                    item.setBackground(QColor(t["color"]))
                    item.setForeground(QColor("white"))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    tip = f"{t['name']}"
                    if isinstance(data, dict) and data.get("note"):
                        item.setFont(QFont("Arial", 8, QFont.Weight.Bold, italic=True))
                        tip += f"\n---\n{data['note']}"
                    item.setToolTip(tip)
                    self.table.setItem(r, visual_col, item)
        self.table.blockSignals(False)
        self.update_stats()

    def setup_mirror(self):
        self.mirror_table.setRowCount(0)
        wid = self.get_week_id()
        hist = self.history.get(wid, {})
        lk = {t["id"]: t for t in self.tasks_data}

        days_names = [
            "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
        ]

        for d_idx in range(1, 8):
            current_date = self.start_of_week + timedelta(days=d_idx - 1)
            d_str = current_date.strftime("%d.%m.%Y")
            day_name = days_names[d_idx - 1]

            # Словарь для группировки задач за текущий день
            # Формат: { task_id: {"count": 0, "notes": []} }
            day_summary = {}
            has_data = False

            # Проходим по всем 48 слотам дня и собираем статистику
            for r in range(48):
                val = hist.get(f"{r},{d_idx}")
                if val:
                    has_data = True
                    tid = val["tid"] if isinstance(val, dict) else val
                    note = val.get("note", "").strip() if isinstance(val, dict) else ""

                    if tid not in day_summary:
                        day_summary[tid] = {"count": 0, "notes": []}
                    
                    day_summary[tid]["count"] += 1
                    
                    # Если есть текст и мы его еще не добавляли в список заметок
                    if note and note not in day_summary[tid]["notes"]:
                        day_summary[tid]["notes"].append(note)

            # Если в этот день была хоть какая-то активность
            if has_data:
                # 1. Отрисовка строки-разделителя с названием дня
                row = self.mirror_table.rowCount()
                self.mirror_table.insertRow(row)

                sep_text = f"{day_name} ({d_str})"
                sep_item = QTableWidgetItem(sep_text)
                sep_item.setBackground(QColor("#2d2d2d"))
                sep_item.setForeground(QColor("#399223"))
                sep_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                sep_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.mirror_table.setItem(row, 0, sep_item)

                for col in range(1, 5):
                    empty = QTableWidgetItem("")
                    empty.setBackground(QColor("#2d2d2d"))
                    empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.mirror_table.setItem(row, col, empty)

                # 2. Отрисовка сгруппированных задач
                for tid, summary in day_summary.items():
                    t = lk.get(tid)
                    if not t:
                        continue # Если задачу удалили из настроек, пропускаем

                    row = self.mirror_table.rowCount()
                    self.mirror_table.insertRow(row)

                    # Колонка 0: Дата
                    self.mirror_table.setItem(row, 0, QTableWidgetItem(d_str))

                    # Колонка 1: Код задачи
                    c_it = QTableWidgetItem(t["code"])
                    c_it.setData(Qt.ItemDataRole.UserRole, t.get("url", ""))
                    if t.get("url"):
                        c_it.setForeground(QColor("#80cbc4"))
                    self.mirror_table.setItem(row, 1, c_it)

                    # Колонка 2: Общее время
                    total_hours = summary["count"] * 0.5
                    self.mirror_table.setItem(row, 2, QTableWidgetItem(f"{total_hours} ч"))

                    # Колонка 4: Статус отправки в трекер
                    sent_status = "✅" if summary.get("sent", False) else "⏳"
                    status_item = QTableWidgetItem(sent_status)
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.mirror_table.setItem(row, 3, status_item)

                    # Колонка 4: Комментарии (склеиваем через абзац)
                    combined_notes = "\n".join(summary["notes"])
                    comment_item = QTableWidgetItem(combined_notes)
                    comment_item.setFlags(comment_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.mirror_table.setItem(row, 4, comment_item)

    def update_stats(self):
        lk = {t["id"]: t for t in self.tasks_data}
        hist = self.history.get(self.get_week_id(), {})
        daily, total = {i: {} for i in range(1, 8)}, {}
        for pos, data in hist.items():
            tid = data["tid"] if isinstance(data, dict) else data
            if tid in lk:
                c = int(pos.split(",")[1])
                daily[c][tid] = daily[c].get(tid, 0) + 0.5
                total[tid] = total.get(tid, 0) + 0.5

        res = ""
        dn = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, name in enumerate(dn, 1):
            if daily[i]:
                res += f"<div style='margin-bottom:10px;'><b>{name}:</b>"
                for tid, h in daily[i].items():
                    t = lk[tid]

                    if t.get("url"):
                        res += f"<br><a href='{t['url']}' style='color:#80cbc4; text-decoration:none;'>{t['code']}</a>: {h}ч"
                    else:
                        res += (
                            f"<br><span style='color:#aaaaaa;'>{t['code']}</span>: {h}ч"
                        )
                res += "</div>"
        if total:
            res += "<hr><b>ИТОГО ЗА НЕДЕЛЮ:</b>"
            for tid, h in total.items():
                res += f"<br>● {lk[tid]['code']}: {h}ч"
        self.lbl_stats.setText(res or "Нет записей")

    def on_cell_event(self, r, c):
        if QApplication.mouseButtons() == Qt.MouseButton.LeftButton and c > 0:
            wid = self.get_week_id()
            key = f"{r},{c}"
            if wid not in self.history:
                self.history[wid] = {}

            if self.eraser_mode:
                if key in self.history[wid]:
                    del self.history[wid][key]
            elif self.current_task:
                old_note = ""
                if key in self.history[wid] and isinstance(
                    self.history[wid][key], dict
                ):
                    old_note = self.history[wid][key].get("note", "")
                self.history[wid][key] = {
                    "tid": self.current_task["id"],
                    "note": old_note,
                }

            self.setup_calendar()
            self.save_to_disk()

    def show_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if idx.column() > 0:
            m = QMenu(self)
            a = QAction("📝 Комментарий", self)
            a.triggered.connect(lambda: self.add_note(idx.row(), idx.column()))
            m.addAction(a)
            m.exec(self.table.viewport().mapToGlobal(pos))

    def add_note(self, r, c):
        wid = self.get_week_id()
        key = f"{r},{c}"
        if key not in self.history.get(wid, {}):
            return

        curr = self.history[wid][key]
        old_txt = curr.get("note", "") if isinstance(curr, dict) else ""
        txt, ok = QInputDialog.getMultiLineText(
            self, "Заметка", "Введите комментарий:", old_txt
        )
        if ok:
            tid = curr["tid"] if isinstance(curr, dict) else curr
            self.history[wid][key] = {"tid": tid, "note": txt}
            self.setup_calendar()
            self.save_to_disk()

    def on_mirror_click(self, r, c):
        url = self.mirror_table.item(r, c).data(Qt.ItemDataRole.UserRole)
        if url:
            webbrowser.open(url)

    def refresh_task_buttons(self):
        while self.btns_lay.count():
            w = self.btns_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        for t in self.tasks_data:
            if t.get("status") == "Завершена":
                continue
            btn = QPushButton(t["code"])
            btn.setCheckable(True)

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t["color"]};
                    color: white;
                    font-weight: bold;
                    min-width: 60px;
                    border: 2px solid transparent; /* Чтобы кнопка не "прыгала" при появлении рамки */
                    border-radius: 4px;
                }}
                QPushButton:checked {{
                    color:  Black !important; /* Цвет текста при нажатии */
                    border: 2px solid green; /* Та самая черная рамка */
                }}
            """)
            btn.clicked.connect(lambda ch, x=t, b=btn: self.set_tool(x, b))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, task=t: self.show_task_context_menu(task))
            self.btns_lay.addWidget(btn)

    def show_task_context_menu(self, task):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE)
        finish_action = menu.addAction("✅ Завершить задачу")
        # Вызываем меню в позиции курсора
        action = menu.exec(QCursor.pos())
        if action == finish_action:
            # Меняем статус в данных
            task["status"] = "Завершена"
            # Если эта задача была выбрана как текущий инструмент — сбрасываем его
            if hasattr(self, 'current_tool') and self.current_tool == task:
                self.set_tool(None, None)
            # Сохраняем изменения в файл и обновляем панель
            self.save_to_disk()
            self.refresh_task_buttons()

    def set_tool(self, task, btn):
        self.eraser_mode = False
        self.btn_eraser.setChecked(False)
        if self.current_task == task:
            self.current_task = None
            btn.setChecked(False)
        else:
            for i in range(self.btns_lay.count()):
                self.btns_lay.itemAt(i).widget().setChecked(False)
            self.current_task = task
            btn.setChecked(True)

    def toggle_eraser(self):
        self.eraser_mode = self.btn_eraser.isChecked()
        if self.eraser_mode:
            self.current_task = None
            for i in range(self.btns_lay.count()):
                self.btns_lay.itemAt(i).widget().setChecked(False)

    def bulk_add_to_history(self, dt, s, e, tid, rid):
        ws = dt - timedelta(days=dt.weekday())
        wid, col = ws.strftime("%Y_W%U"), dt.weekday() + 1
        if wid not in self.history:
            self.history[wid] = {}
        for r in range(s, e):
            self.history[wid][f"{r},{col}"] = {"tid": tid, "rid": rid, "note": ""}

    def remove_rule_from_history(self, rid):

        for wid, entries in list(self.history.items()):
            keys_to_del = [
                pos
                for pos, data in entries.items()
                if isinstance(data, dict) and data.get("rid") == rid
            ]

            for k in keys_to_del:
                del entries[k]

            if not entries:
                del self.history[wid]

        self.save_to_disk()
        self.setup_view()

    def delete_task_globally(self, task_code):

        task_id = None
        for t in self.tasks_data:
            if t["code"] == task_code:
                task_id = t["id"]
                break
        if not task_id:
            return

        self.tasks_data = [t for t in self.tasks_data if t["id"] != task_id]

        rules_to_delete = set()
        for wid, entries in list(self.history.items()):
            keys_to_del = []
            for pos, data in entries.items():
                tid = data["tid"] if isinstance(data, dict) else data
                if tid == task_id:
                    keys_to_del.append(pos)

                    if isinstance(data, dict) and "rid" in data:
                        rules_to_delete.add(data["rid"])

            for k in keys_to_del:
                del entries[k]

            if not entries:
                del self.history[wid]

        for rid in rules_to_delete:
            if rid in self.rules_data:
                del self.rules_data[rid]

        self.save_to_disk()
        self.refresh_task_buttons()
        self.setup_view()

    def open_task_manager(self):
        dlg = TaskManagerDialog(self)
        dlg.exec()
        self.refresh_task_buttons()
        self.setup_view()

    def open_rules(self):
        RulesManagerDialog(self).exec()
        self.setup_view()

    def open_work_settings(self):
        WorkSettingsDialog(self).exec()
        self.setup_view()
        self.scroll_to_work()

    def save_to_disk(self):

        m_widths = []
        if hasattr(self, "mirror_table"):
            m_widths = [self.mirror_table.columnWidth(i) for i in range(5)]

        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "tasks": self.tasks_data,
                    "history": self.history,
                    "work": self.work_settings,
                    "rules": self.rules_data,
                    "mirror_widths": m_widths,
                },
                f,
                indent=4,
            )
        self.sync_to_csv()

    def load_from_disk(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.tasks_data = d.get("tasks", [])
                    self.history = d.get("history", {})
                    self.work_settings = d.get("work", self.work_settings)
                    self.rules_data = d.get("rules", {})
                    self.saved_widths = d.get("mirror_widths", [173, 157, 60, 654])
            except Exception as e:
                print(f"Ошибка загрузки: {e}")

    def closeEvent(self, event):

        self.save_to_disk()
        event.accept()

    def get_week_id(self):
        return self.start_of_week.strftime("%Y_W%U")

    def tick(self):
        self.lbl_clock.setText(datetime.now().strftime("%d.%m.%Y | %H:%M:%S"))

    def prev_w(self):
        self.start_of_week -= timedelta(days=7)
        self.setup_view()

    def next_w(self):
        self.start_of_week += timedelta(days=7)
        self.setup_view()

    #Метод экспорта данных в CSV-файлик
    def sync_to_csv(self):
        file_path = "yandex_tracker_export.csv"
        # Сопоставляем данные задач
        tracker_map = {t["code"]: t.get("tracker_id", "") for t in self.tasks_data}
        task_types = {t["id"]: t.get("task_type", "ETC") for t in self.tasks_data}
        task_codes = {t["id"]: t["code"] for t in self.tasks_data}
        
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                # Добавляем колонку 'sent' для твоего контроля
                writer.writerow(['issue_id', 'start', 'duration', 'comment', 'sent'])
                
                for week_id in sorted(self.history.keys()):
                    parts = week_id.split('_')
                    year, week_num = int(parts[0]), int(parts[1].replace('W', ''))
                    first_day = date(year, 1, 1)
                    monday = first_day + timedelta(weeks=week_num, days=-first_day.weekday())
                    hist = self.history[week_id]
                    
                    for d_idx in range(1, 8):
                        current_date = monday + timedelta(days=d_idx - 1)
                        day_summary = {} 
                        
                        for r in range(48):
                            val = hist.get(f"{r},{d_idx}")
                            if val:
                                tid = val["tid"] if isinstance(val, dict) else val
                                # Проверяем тип задачи — берем только "Tracker"
                                if task_types.get(tid) != "Tracker":
                                    continue
                                    
                                note = val.get("note", "").strip() if isinstance(val, dict) else ""
                                # Получаем статус отправки (по умолчанию False)
                                is_sent = val.get("sent", False) if isinstance(val, dict) else False
                                
                                if tid not in day_summary:
                                    day_summary[tid] = {"count": 0, "notes": [], "first_slot": r, "sent": is_sent}
                                
                                day_summary[tid]["count"] += 1
                                if note and note not in day_summary[tid]["notes"]:
                                    day_summary[tid]["notes"].append(note)

                        for tid, summary in day_summary.items():
                            issue_id = tracker_map.get(task_codes.get(tid), "")
                            if not issue_id: continue

                            fs = summary["first_slot"]
                            start_iso = f"{current_date.strftime('%Y-%m-%d')}T{fs//2:02}:{30 if fs%2!=0 else 0:02}:00.000+0300"
                            duration_iso = f"PT{int(summary['count'] * 30)}M"
                            clean_comment = " / ".join(summary["notes"]).replace('\n', ' ').strip()
                            
                            # Записываем в CSV: статус отправки преобразуем в текстовый вид для таблицы
                            sent_status = "Да" if summary["sent"] else "Нет"
                            
                            writer.writerow([issue_id, start_iso, duration_iso, clean_comment, sent_status])
        except Exception as e:
            print(f"Ошибка экспорта: {e}")

class TaskManagerDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Менеджер задач")
        self.resize(1000, 500)
        self.setStyleSheet(STYLE)
        self.p = parent
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Код", "Название", "Трекер ID", "Статус", "Ссылка", "Цвет", "Управление"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)
        btn_add = QPushButton("+ Добавить новую")
        btn_add.clicked.connect(self.add_new)
        layout.addWidget(btn_add)
        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        for i, t in enumerate(self.p.tasks_data):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(t["code"]))
            self.table.setItem(r, 1, QTableWidgetItem(t["name"]))
            self.table.setItem(r, 2, QTableWidgetItem(t.get("tracker_id", "")))
            self.table.setItem(r, 3, QTableWidgetItem(t.get("status", "В работе")))
            
            url_item = QTableWidgetItem(t.get("url", ""))
            if t.get("url"): url_item.setForeground(QColor("#80cbc4"))
            self.table.setItem(r, 4, url_item)
            
            color_widget = QWidget()
            color_box = QFrame(color_widget)
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(f"background-color: {t.get('color', '#7E57C2')}; border-radius: 2px;")
            color_lay = QHBoxLayout(color_widget)
            color_lay.setContentsMargins(0, 0, 0, 0)
            color_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color_lay.addWidget(color_box)
            self.table.setCellWidget(r, 5, color_widget)

            action_w = QWidget()
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(2, 2, 2, 2)
            btn_edit = QPushButton("⚙")
            btn_edit.clicked.connect(lambda ch, idx=i: self.edit(idx))

            btn_del = QPushButton("🗑")
            btn_del.clicked.connect(
                lambda ch, code=t["code"]: self.confirm_delete(code)
            )

            action_lay.addWidget(btn_edit)
            action_lay.addWidget(btn_del)
            self.table.setCellWidget(r, 6, action_w)

    def add_new(self):
        d = TaskEditDialog(self.p)
        if d.exec():
            self.p.tasks_data.append(d.result_task)
            self.p.save_to_disk()
            self.refresh()

    def edit(self, idx):
        d = TaskEditDialog(self.p, self.p.tasks_data[idx])
        if d.exec():
            self.p.tasks_data[idx] = d.result_task
            self.p.save_to_disk()
            self.refresh()

    def confirm_delete(self, task_code):
        reply = QMessageBox.question(
            self,
            "ВНИМАНИЕ: Опасное удаление",
            f"Вы уверены, что хотите удалить тип задачи '{task_code}'?\n\n"
            "Это удалит ВСЕ записи на доске (историю) и ВСЕ связанные периодические задачи!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.p.delete_task_globally(task_code)
            self.refresh()


class RulesManagerDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Активные правила")
        self.resize(500, 300)
        self.setStyleSheet(STYLE)
        self.p = parent
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Описание правила", "Удалить"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)
        btn_add = QPushButton("+ Добавить повтор")
        btn_add.clicked.connect(self.add_rule)
        layout.addWidget(btn_add)
        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        for rid, info in self.p.rules_data.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(info["desc"]))
            btn = QPushButton("🗑")
            btn.clicked.connect(lambda ch, x=rid: self.del_rule(x))
            self.table.setCellWidget(r, 1, btn)

    def add_rule(self):
        if RecurringTaskDialog(self.p).exec():
            self.refresh()

    def del_rule(self, rid):

        self.p.remove_rule_from_history(rid)

        if rid in self.p.rules_data:
            del self.p.rules_data[rid]

        self.p.save_to_disk()
        self.refresh()


class WorkSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Настройка рабочего дня")
        self.setStyleSheet(STYLE)
        self.p = parent
        layout = QVBoxLayout(self)
        times = [f"{h:02}:{m:02}" for h in range(24) for m in (0, 30)]
        self.s = QComboBox()
        self.e = QComboBox()
        self.s.addItems(times)
        self.e.addItems(times)
        self.s.setCurrentText(parent.work_settings["start"])
        self.e.setCurrentText(parent.work_settings["end"])
        layout.addWidget(QLabel("Начало рабочего дня:"))
        layout.addWidget(self.s)
        layout.addWidget(QLabel("Конец рабочего дня:"))
        layout.addWidget(self.e)

        self.cbs = []
        days_l = QHBoxLayout()
        for i, n in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]):
            cb = QCheckBox(n)
            cb.setChecked(bool(parent.work_settings["active_days"][i]))
            self.cbs.append(cb)
            days_l.addWidget(cb)
        layout.addLayout(days_l)
        # Чекбокс для отображения выходных дней
        self.cb_show_weekends = QCheckBox("Отображать выходные дни")
        self.cb_show_weekends.setChecked(parent.work_settings.get("show_weekends", True))
        layout.addWidget(self.cb_show_weekends)

        btn_color = QPushButton("Цвет нерабочих зон")
        btn_color.clicked.connect(self.pick_c)
        layout.addWidget(btn_color)
        self.clr = QColor(parent.work_settings["color"])

        btn_save = QPushButton("Применить")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    def pick_c(self):
        c = QColorDialog.getColor(self.clr, self)
        if c.isValid():
            self.clr = c

    def save(self):
        self.p.work_settings.update(
            {
                "start": self.s.currentText(),
                "end": self.e.currentText(),
                "color": self.clr.name(QColor.NameFormat.HexArgb),
                "active_days": [int(cb.isChecked()) for cb in self.cbs],
                "show_weekends": self.cb_show_weekends.isChecked()
            }
        )
        self.p.save_to_disk()
        self.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = VegCalendar()
    w.show()
    sys.exit(app.exec())