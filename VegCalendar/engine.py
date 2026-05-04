# engine.py
import json
import os
from yandexAPI.sync_service import TrackerSyncService
import config
import csv
from datetime import date, timedelta

class DataManager:
    def __init__(self, save_file):
        self.save_file = save_file
        # Это были строки 39-46 в твоем файле
        self.history = {}
        self.tasks_data = []
        self.rules_data = {}
        self.work_settings = {
            "active_days": [1, 1, 1, 1, 1, 0, 0],
            "start": "09:00",
            "end": "18:00",
            "color": "#3c1e3a5f",
            "show_weekends": True
        }
        self.load_from_disk()

    def load_from_disk(self):
        # Это строки 712-721
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks_data = data.get("tasks", [])
                    self.history = data.get("history", {})
                    self.rules_data = data.get("rules", {})
                    self.work_settings.update(data.get("work_settings", {}))
                    
                    # --- НОВОЕ: Загружаем ширину колонок из JSON ---
                    self.mirror_widths = data.get("mirror_widths", [140, 280, 100, 60, 500])
            except: pass

    def save_to_disk(self):
        """
        Метод внутри DataManager, который физически записывает данные на диск.
        """
        try:
            # Собираем все данные в один словарь для записи
            data_to_save = {
                "tasks": self.tasks_data,
                "history": self.history,
                "work_settings": self.work_settings,
                "rules": self.rules_data,
                "mirror_widths": getattr(self, 'mirror_widths', [140, 280, 100, 60, 500])
            }
            
            # Записываем в файл (SAVE_FILE берется из конфига или инициализации)
            with open(self.save_file, "w", encoding="utf-8") as f:
                # indent=4 делает файл читаемым для человека
                # ensure_ascii=False сохраняет кириллицу как буквы, а не коды
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Критическая ошибка при записи на диск: {e}")

    def bulk_add_to_history(self, target_date, s_slot, e_slot, tid, rule_id):
        # Это строки 664-675
        d_str = target_date.strftime("%Y-%m-%d")
        for slot in range(s_slot, e_slot):
            key = f"{d_str}_{slot}"
            self.history[key] = {"tid": tid, "note": "", "rule_id": rule_id}

    def remove_rule_from_history(self, rule_id):
        # Это строки 677-680
        to_del = [k for k, v in self.history.items() if v.get("rule_id") == rule_id]
        for k in to_del: self.history.pop(k, None)

    def delete_task_globally(self, task_code):
        # Это строки 690-710
        target_id = next((t["id"] for t in self.tasks_data if t["code"] == task_code), None)
        if not target_id: return
        self.tasks_data = [t for t in self.tasks_data if t["id"] != target_id]
        self.history = {k: v for k, v in self.history.items() if v.get("tid") != target_id}
        self.rules_data = {k: v for k, v in self.rules_data.items() if f"[{task_code}]" not in v['desc']}
        self.save_to_disk()

    #Метод экспорта данных в CSV-файлик
    def prepare_csv_for_yandex(self):
        """
        Формирует CSV с учетом правил: 
        1. Не сбрасывать 'Да', если параметры не менялись.
        2. Сбрасывать на 'Нет', если изменилось время (duration).
        """
        import os
        import csv
        from datetime import date, timedelta

        # --- НОВАЯ ЛОГИКА: Читаем старые статусы ---
        old_data = {}
        if os.path.exists(config.YANDEX_CSV_PATH):
            try:
                with open(config.YANDEX_CSV_PATH, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        # Ключ: ID задачи + Дата (первые 10 символов из ISO старта)
                        d_key = row['start'][:10]
                        key = f"{row['issue_id']}_{d_key}"
                        old_data[key] = {"sent": row['sent'], "duration": row['duration']}
            except Exception as e:
                print(f"Предупреждение: Не удалось прочитать старый CSV: {e}")

        tracker_map = {t["code"]: t.get("tracker_id", "").strip() for t in self.tasks_data}
        task_types = {t["id"]: t.get("task_type", "ETC") for t in self.tasks_data}
        task_codes = {t["id"]: t["code"] for t in self.tasks_data}

        try:
            with open(config.YANDEX_CSV_PATH, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['issue_id', 'start', 'duration', 'comment', 'sent'])

                for week_id in sorted(self.history.keys()):
                    parts = week_id.split('_')
                    year, week_num = int(parts[0]), int(parts[1].replace('W', ''))
                    first_day = date(year, 1, 1)
                    monday = first_day + timedelta(weeks=week_num, days=-first_day.weekday())
                    hist = self.history[week_id]

                    for d_idx in range(1, 8):
                        current_date = monday + timedelta(days=d_idx - 1)
                        d_iso = current_date.strftime('%Y-%m-%d')
                        day_summary = {}

                        for r in range(48):
                            val = hist.get(f"{r},{d_idx}")
                            if val:
                                tid = val["tid"] if isinstance(val, dict) else val
                                if task_types.get(tid) != "Tracker": continue
                                
                                note = val.get("note", "").strip() if isinstance(val, dict) else ""
                                if tid not in day_summary:
                                    day_summary[tid] = {"count": 0, "notes": [], "first_slot": r}
                                day_summary[tid]["count"] += 1
                                if note and note not in day_summary[tid]["notes"]:
                                    day_summary[tid]["notes"].append(note)

                        for tid, summary in day_summary.items():
                            issue_id = tracker_map.get(task_codes.get(tid), "")
                            if not issue_id: continue

                            fs = summary["first_slot"]
                            start_iso = f"{d_iso}T{fs//2:02}:{30 if fs%2!=0 else 0:02}:00.000+0300"
                            duration_iso = f"PT{int(summary['count'] * 30)}M"
                            
                            # --- ПРИМЕНЕНИЕ ПРАВИЛ ---
                            lookup_key = f"{issue_id}_{d_iso}"
                            final_sent = "Нет"

                            if lookup_key in old_data:
                                # Если время совпадает - сохраняем статус (Да/Нет)
                                if old_data[lookup_key]["duration"] == duration_iso:
                                    final_sent = old_data[lookup_key]["sent"]
                                # Если время изменилось - оставляем "Нет" (сброс)

                            clean_comment = " / ".join(summary["notes"]).replace('\n', ' ').strip()
                            writer.writerow([issue_id, start_iso, duration_iso, clean_comment, final_sent])
            return True
        except Exception as e:
            print(f"Ошибка при подготовке CSV: {e}")
            return False
    
    def sync_external_services(self):
        """
        Главный метод для внешней синхронизации. 
        Скрывает внутри себя все детали работы с API[cite: 3, 8].
        """
        # 1. Сначала принудительно обновляем экспортный файл данными из памяти
        self.prepare_csv_for_yandex()
        
        # 2. Создаем сервис синхронизации, используя данные из config.py
        self.sync_service = TrackerSyncService(
        api_token=config.YANDEX_TOKEN, 
        org_id=config.YANDEX_ORG_ID, 
        csv_path=config.YANDEX_CSV_PATH,
        sync_start_date=getattr (config, 'SYNC_START_DATE', '2026-05-01')
    )
            
        # 3. Запускаем процесс и возвращаем результат (dict с отчетом)[cite: 8]
        return self.sync_service.sync_from_csv()