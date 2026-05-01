# yandexAPI/sync_service.py
import csv
from .connector import YandexTrackerAPI # Точка означает "в этой же папке"

class TrackerSyncService:
    """
    Сервис, который читает локальный CSV и решает, что пора отправить в Яндекс.
    """
    def __init__(self, api_token, org_id, csv_path):
        self.api = YandexTrackerAPI(api_token, org_id)
        self.csv_path = csv_path

    def sync_from_csv(self):
        results = {"success": 0, "failed": 0}
        
        try:
            # Читаем CSV с твоими данными
            with open(self.csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                rows = list(reader)

            for row in rows:
                # Отправляем только те записи, где стоит 'Нет' в колонке 'sent'
                if row.get('sent') == 'Нет':
                    success, msg = self.api.add_worklog(
                        issue_id=row['issue_id'],
                        start_time=row['start'],
                        duration=row['duration'],
                        comment=row['comment']
                    )
                    
                    if success:
                        results["success"] += 1
                        row['sent'] = 'Да' # Меняем статус на "отправлено"
                    else:
                        results["failed"] += 1
                        print(f"Ошибка API для {row['issue_id']}: {msg}")

            # Сохраняем обновленные статусы обратно в CSV
            self._save_updates(rows)
            
        except Exception as e:
            print(f"Ошибка при чтении файла для синхронизации: {e}")
            
        return results

    def _save_updates(self, rows):
        if not rows: return
        fieldnames = rows[0].keys()
        with open(self.csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)