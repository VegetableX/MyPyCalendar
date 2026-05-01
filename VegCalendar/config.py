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

# Данные для работы с Яндекс.Трекером. Подставь свои данные для работы с API
YANDEX_TOKEN = "y0__wgBEPfA2vICGNyNQSCkrb2jFzD24db9B5GxtV8I2zberGlkEoqurQ4CbMbj" # Твой OAuth-токен
YANDEX_ORG_ID = "8460363"    # ID организации
YANDEX_CSV_PATH = "yandex_tracker_export.csv"
YANDEX_BASE_URL = "https://api.tracker.yandex.net/v3"