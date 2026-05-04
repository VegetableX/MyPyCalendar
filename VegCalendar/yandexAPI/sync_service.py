import csv
import logging
import config
from datetime import datetime
from .connector import YandexTrackerAPI
from .time_parser import iso_duration_to_minutes, normalize_to_date_str

# Настройка логирования
logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class TrackerSyncService:
    def __init__(self, api_token, org_id, csv_path, sync_start_date):
        self.api = YandexTrackerAPI(token=api_token, org_id=org_id)
        self.csv_path = csv_path
        self.sync_start_date = sync_start_date
        logging.info("Сервис инициализирован. Токены переданы в коннектор.")

    def sync_from_csv(self):
        results = {"success": 0, "failed": 0, "updated": 0, "deleted": 0}
        logging.info("--- Запуск синхронизации ---")

        # 1. Получаем все записи из облака за период
        success_fetch, cloud_data = self.api.get_user_worklogs()
        if not success_fetch:
            logging.error(f"Не удалось получить записи из облака: {cloud_data}")
            return results

        # Группируем облачные записи по дате и issue_id для быстрого поиска
        # Ключ: (date_str, issue_key), Значение: список записей (т.к. могут быть дубли)
        cloud_map = {}
        for entry in cloud_data:
            date_key = normalize_to_date_str(entry.get('start'))
            issue_key = entry.get('issue', {}).get('key', '').upper()
            dict_key = (date_key, issue_key)
            
            if dict_key not in cloud_map:
                cloud_map[dict_key] = []
            cloud_map[dict_key].append(entry)

        try:
            with open(self.csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                rows = list(reader)

            for row in rows:
                # ПРОВЕРКА ГРАНИЦЫ БЕЗОПАСНОСТИ
                csv_date = normalize_to_date_str(row['start'])# Получаем "YYYY-MM-DD"
                if csv_date < self.sync_start_date:
                    if row.get('sent') == 'Нет':
                        logging.info(f"Пропуск {row['issue_id']} на {csv_date}: дата до точки отсечки.")
                    continue # Переходим к следующей строке, не заходя в логику отправки
                # Нас интересуют только те, что помечены "Нет" (или те, что нужно проверить)
                if row.get('sent') == 'Нет':
                    csv_issue = row['issue_id'].upper()
                    csv_duration = iso_duration_to_minutes(row['duration'])
                    dict_key = (csv_date, csv_issue)

                    # Ищем совпадения в облаке
                    matches = cloud_map.get(dict_key, [])

                    if not matches:
                        # СЦЕНАРИЙ А: Записи нет -> Создаем
                        ok, res = self.api.add_worklog(row['issue_id'], row['start'], row['duration'], row['comment'])
                        if ok:
                            row['sent'] = 'Да'
                            results["success"] += 1
                            logging.info(f"Создано: {csv_issue} на {csv_date}")
                        else:
                            logging.error(f"Ошибка создания {csv_issue}: {res}")
                            results["failed"] += 1
                    
                    else:
                        # СЦЕНАРИЙ Б и В: Записи есть. Сортируем по updatedAt (свежие в начало)
                        matches.sort(key=lambda x: x.get('updatedAt', ''), reverse=True)
                        main_entry = matches[0]
                        other_entries = matches[1:]

                        # Проверяем длительность основной записи
                        api_duration = iso_duration_to_minutes(main_entry.get('duration'))
                        
                        if api_duration == csv_duration:
                            # Все совпало, просто помечаем как отправлено
                            row['sent'] = 'Да'
                            logging.info(f"Совпало: {csv_issue} на {csv_date}. Пропуск.")
                        else:
                            # Длительность разная -> Обновляем
                            ok, res = self.api.update_worklog(csv_issue, main_entry['id'], row['duration'], row['comment'])
                            if ok:
                                row['sent'] = 'Да'
                                results["updated"] += 1
                                logging.info(f"Обновлено: {csv_issue} на {csv_date} ({api_duration}м -> {csv_duration}м)")
                            else:
                                logging.error(f"Ошибка обновления {csv_issue}: {res}")

                        # Удаляем лишние дубликаты, если они есть
                        for duplicate in other_entries:
                            if self.api.delete_worklog(csv_issue, duplicate['id']):
                                results["deleted"] += 1
                                logging.warning(f"Удален дубликат: {csv_issue}, ID: {duplicate['id']}")

            self._save_updates(rows)
            
        except Exception as e:
            logging.critical(f"Критическая ошибка сервиса: {e}")
            
        return results

    def _save_updates(self, rows):
        if not rows: return
        fieldnames = rows[0].keys()
        with open(self.csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)