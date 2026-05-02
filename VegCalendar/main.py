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
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QAbstractItemView,
    QHeaderView,
    QFrame,
    QStackedWidget,
    QMenu,
    QInputDialog,
    QSplitter,
    QMessageBox,

)
from PyQt6.QtCore import  Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QCursor, QFont, QAction
from config import STYLE, SAVE_FILE
from utils import MultiLineDelegate, FlowLayout
from dialogs import TaskManagerDialog, RulesManagerDialog, WorkSettingsDialog
from engine import DataManager

class VegCalendar(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. ПОДКЛЮЧАЕМ ДВИГАТЕЛЬ (ОБЯЗАТЕЛЬНО ПЕРВЫМ)
        self.engine = DataManager(SAVE_FILE)

        # 2. СОЗДАЕМ ССЫЛКИ, ЧТОБЫ СТАРЫЙ КОД ИХ ВИДЕЛ
        # Это именно те строки, которые я предложил, но их нужно 
        # поставить ДО вызова self.init_ui()
        self.tasks_data = self.engine.tasks_data
        self.history = self.engine.history
        self.rules_data = self.engine.rules_data
        self.work_settings = self.engine.work_settings

        # 3. ТЕПЕРЬ МОЖНО РИСОВАТЬ (теперь self.tasks_data уже существует)
        self.setWindowTitle("Veg Tracker 4.4")
        self.resize(1400, 900)
        self.setStyleSheet(STYLE)

        self.start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
        self.current_task, self.eraser_mode = None, False

        self.init_ui() 
        # Теперь refresh_task_buttons внутри init_ui найдет self.tasks_data и не упадет!

        # ... остальной код (таймеры, колонки) ...

        self.init_ui()

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

        # Кнопка синхронизации с Яндексом
        self.btn_sync = QPushButton("☁") # Можно использовать иконку облака
        self.btn_sync.setObjectName("IconBtn")
        self.btn_sync.setFixedSize(40, 40)
        self.btn_sync.setToolTip("Синхронизировать с Яндекс Трекером")
        self.btn_sync.clicked.connect(self.run_yandex_sync)
        top_bar.addWidget(self.btn_sync)

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
        header.sectionResized.connect(lambda logicalIndex, oldSize, newSize: self.save_to_disk())

        saved = getattr(self.engine, 'mirror_widths', [140, 280, 100, 60, 500])
        
        for i, width in enumerate(saved):
            if i < self.mirror_table.columnCount():
                self.mirror_table.setColumnWidth(i, width)

        # НАСТРОЙКА ПОВЕДЕНИЯ КОЛОНОК
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Дата
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Задача
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Время
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)       # Статус (фиксированный)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)     # Комментарий (тянется)

        header.setCascadingSectionResizes(True)
        header.setMinimumSectionSize(40)
        header.sectionResized.connect(lambda logicalIndex, oldSize, newSize: self.save_to_disk())

        # СОХРАНЯЕМ РАЗМЕРЫ КОЛОНОК
        header.sectionResized.connect(self.save_to_disk)

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
        """
        Метод для отрисовки таблицы-отчета (зеркала).
        Группирует данные по задачам за каждый день и отображает статус синхронизации с Яндексом.
        """
        # 1. ПОДГОТОВКА: Очищаем таблицу и собираем базовые данные
        self.mirror_table.setRowCount(0)
        # Получаем идентификатор текущей недели (например, '2024_W18')
        wid = self.get_week_id()
        # Извлекаем историю записей для этой недели из памяти
        hist = self.history.get(wid, {})
        # Создаем быстрый поиск данных о задачах по их ID
        lk = {t["id"]: t for t in self.tasks_data}

        # 2. КЭШИРОВАНИЕ СТАТУСОВ: Один раз читаем CSV, чтобы не тормозить интерфейс
        # Ключ словаря: "ID_Задачи_ГГГГ-ММ-ДД", значение: "Да" или "Нет"
        csv_statuses = {}
        csv_path = "yandex_tracker_export.csv"
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        # Извлекаем дату (первые 10 символов из формата ISO: '2024-04-30T...')
                        date_part = row['start'][:10]
                        key = f"{row['issue_id']}_{date_part}"
                        csv_statuses[key] = row['sent']
            except Exception as e:
                print(f"Ошибка при чтении статусов из CSV: {e}")

        days_names = [
            "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
        ]

        # 3. ОСНОВНОЙ ЦИКЛ: Проходим по каждому из 7 дней недели
        for d_idx in range(1, 8):
            # Вычисляем дату конкретного дня
            current_date = self.start_of_week + timedelta(days=d_idx - 1)
            # d_str для отображения (30.04.2024), d_iso для поиска в CSV (2024-04-30)
            d_str = current_date.strftime("%d.%m.%Y")
            d_iso = current_date.strftime("%Y-%m-%d")
            day_name = days_names[d_idx - 1]

            # Группируем задачи за день: { task_id: {"count": количество_слотов, "notes": [список_заметок]} }
            day_summary = {}
            has_data_for_this_day = False

            # Проверяем все 48 слотов (по 30 минут) этого дня
            for r in range(48):
                val = hist.get(f"{r},{d_idx}")
                if val:
                    has_data_for_this_day = True
                    # Определяем ID задачи и текст заметки
                    tid = val["tid"] if isinstance(val, dict) else val
                    note = val.get("note", "").strip() if isinstance(val, dict) else ""

                    if tid not in day_summary:
                        day_summary[tid] = {"count": 0, "notes": []}
                    
                    day_summary[tid]["count"] += 1
                    if note and note not in day_summary[tid]["notes"]:
                        day_summary[tid]["notes"].append(note)

            # 4. ОТРИСОВКА: Если в этот день были записи, выводим их в таблицу
            if has_data_for_this_day:
                # А) Строка-заголовок дня (зеленая полоса)
                row_idx = self.mirror_table.rowCount()
                self.mirror_table.insertRow(row_idx)

                sep_item = QTableWidgetItem(f"{day_name} ({d_str})")
                sep_item.setBackground(QColor("#2d2d2d")) # Темный фон
                sep_item.setForeground(QColor("#399223")) # Зеленый текст
                sep_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                sep_item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Запрет на редактирование
                self.mirror_table.setItem(row_idx, 0, sep_item)

                # Закрашиваем остальные ячейки заголовка в темный цвет
                for col in range(1, 5):
                    empty = QTableWidgetItem("")
                    empty.setBackground(QColor("#2d2d2d"))
                    empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.mirror_table.setItem(row_idx, col, empty)

                # Б) Отрисовка задач этого дня
                for tid, summary in day_summary.items():
                    task_info = lk.get(tid)
                    if not task_info:
                        continue # Пропускаем, если задача удалена из настроек

                    row_idx = self.mirror_table.rowCount()
                    self.mirror_table.insertRow(row_idx)

                    # Кол 0: Дата
                    self.mirror_table.setItem(row_idx, 0, QTableWidgetItem(d_str))

                    # Кол 1: Код задачи (с поддержкой ссылки на Tracker)
                    code_item = QTableWidgetItem(task_info["code"])
                    code_item.setData(Qt.ItemDataRole.UserRole, task_info.get("url", ""))
                    if task_info.get("url"):
                        code_item.setForeground(QColor("#80cbc4")) # Подсвечиваем цветом ссылки
                    self.mirror_table.setItem(row_idx, 1, code_item)

                    # Кол 2: Время (из слотов в часы)
                    total_hours = summary["count"] * 0.5
                    self.mirror_table.setItem(row_idx, 2, QTableWidgetItem(f"{total_hours} ч"))

                    # Кол 3: СТАТУС (Умная проверка через кэш CSV)
                    tracker_id = task_info.get("tracker_id", "").strip()
                    lookup_key = f"{tracker_id}_{d_iso}"
                    
                    # Если в CSV нашли "Да", ставим галочку, иначе песочные часы
                    is_sent = csv_statuses.get(lookup_key) == "Да"
                    status_icon = "✅" if is_sent else "⏳"
                    
                    status_item = QTableWidgetItem(status_icon)
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_item.setFlags(status_item.flags() ^ Qt.ItemFlag.ItemIsEditable) # Только чтение
                    self.mirror_table.setItem(row_idx, 3, status_item)

                    # Кол 4: Комментарии
                    combined_notes = "\n".join(summary["notes"])
                    comment_item = QTableWidgetItem(combined_notes)
                    # Разрешаем редактирование комментариев прямо в отчете
                    comment_item.setFlags(comment_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.mirror_table.setItem(row_idx, 4, comment_item)     

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

    def save_to_disk(self):
        """
        Метод в главном окне: собирает UI-данные и дергает движок.
        """
        # 1. Сначала забираем ширины колонок из таблицы отчета
        if hasattr(self, "mirror_table"):
            m_widths = []
            for i in range(self.mirror_table.columnCount()):
                m_widths.append(self.mirror_table.columnWidth(i))
            
            # Сохраняем эти ширины в объект движка
            self.engine.mirror_widths = m_widths 

        # 2. Теперь просим движок сохранить всё в файл
        # Больше не будет ошибки, так как в engine.py мы убрали self.engine.save_to_disk()
        self.engine.save_to_disk()
        
        # 3. Обновляем вспомогательный CSV
        if hasattr(self.engine, 'prepare_csv_for_yandex'):
            self.engine.prepare_csv_for_yandex()

    #Метод вызова синхронизации с Yandex Tracker
    def run_yandex_sync(self):
        """
        Обработчик нажатия кнопки синхронизации.
        Отвечает только за UI: курсор, вызов логики и показ уведомлений.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication, QMessageBox
        
        # 1. Показываем пользователю, что программа занята (песочные часы)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # 2. Просто просим движок сделать свою работу[cite: 3]
            # Мы не знаем, какой там токен и какой сервис — нам просто нужен отчет.
            report = self.engine.sync_external_services()
            
            QApplication.restoreOverrideCursor()
            
            # 3. Выводим результат через стандартное окно[cite: 5]
            msg = f"Готово!\nУспешно отправлено: {report['success']}\nОшибок: {report['failed']}"
            QMessageBox.information(self, "Облако", msg)
            
            # 4. Обновляем таблицу, чтобы отобразить новые статусы синхронизации[cite: 5]
            self.setup_view()
            
        except Exception as e:
            # В случае любой беды возвращаем обычный курсор и ругаемся[cite: 5]
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Ошибка синхронизации", f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = VegCalendar()
    w.show()
    sys.exit(app.exec())