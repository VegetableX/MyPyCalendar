
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
# Куда мы сохраняем основные изменения в календарике
SAVE_FILE = "calendar_data.json"
# --- URL подключения к API ---
YANDEX_BASE_URL = "https://api.tracker.yandex.net/v3"
# --- Путь к CSV-файлу для учёта времени ---
YANDEX_CSV_PATH = "yandex_tracker_export.csv"
# --- Идентификация пользователя ---
YANDEX_TOKEN = "y0__wgBEPfA2vICGNyNQSCkrb2jFzD24db9B5GxtV8I2zberGlkEoqurQ4CbMbj" # Твой OAuth-токен
YANDEX_ORG_ID = "8460363" # ID твоей организации
# Можно получить через GET /myself Твой логин или ID в системе Яндекса (используется для фильтрации ворклога)
USER_LOGIN = "8000000000000002"
# За сколько дней ДО текущей даты мы проверяем наличие записей?
SYNC_WINDOW_DAYS = 30
# Настройки конвертации времени (ISO 8601 -> Minutes)
WORK_DAY_MINUTES = 480  # 8 часов
WORK_WEEK_MINUTES = 2400 # 5 рабочих дней (если Tracker использует недели 'W')
# ЧАС всегда равен 60 минутам по стандарту ISO, его менять не нужно
# Ранее внесенные данные до этой даты не будут затронуты синхронизацией
SYNC_START_DATE = "2026-05-01"