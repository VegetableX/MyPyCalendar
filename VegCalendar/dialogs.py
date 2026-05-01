import uuid
from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QVBoxLayout, QGridLayout, QHBoxLayout, QWidget, QPushButton, 
    QLabel, QDialog, QCheckBox, QComboBox, QColorDialog, 
    QMessageBox, QLineEdit, QDateEdit, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

# Импортируем стили из нашего файла настроек
from config import STYLE

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
