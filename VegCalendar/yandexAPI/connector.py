# yandexAPI/connector.py
import requests
import config # Импортируем конфигурационный файл
from datetime import datetime, timedelta
import logging # Импортируем модуль логирования для отладки

class YandexTrackerAPI:
    def __init__(self, token, org_id):
        self.token = token
        self.org_id = org_id
        # Заголовки общие для всех методов
        self.headers = {
            "Authorization": f"OAuth {self.token}",
            "X-Org-ID": self.org_id,
            "Content-Type": "application/json"
        }

    def add_worklog(self, issue_id, start_time, duration, comment):
        """Метод для отправки времени"""
        # Роутинг живет внутри метода
        url = f"{config.YANDEX_BASE_URL}/issues/{issue_id}/worklog"
        
        data = {
            "start": start_time,
            "duration": duration,
            "comment": comment
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            return True, response.json()
        return False, response.text
    
    def get_issue_info(self, issue_id):
        """Пример другого метода: получение данных о задаче"""
        url = f"{config.YANDEX_BASE_URL}/issues/{issue_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_user_worklogs(self):
        """
        Отобрать записи по параметрам (Глобальный поиск).
        URL: /v3/worklog/_search
        """
        url = f"{config.YANDEX_BASE_URL}/worklog/_search"
        
        # Вычисляем временное окно из конфига формат ISO
        date_from = (datetime.now() - timedelta(days=config.SYNC_WINDOW_DAYS)).strftime('%Y-%m-%dT00:00:00.000+0000')
        
        # Тело запроса для фильтрации
        query_data = {
            "createdBy": config.USER_LOGIN,
            "createdAt": {
                "from": date_from
            }
        }
        #логирование запроса
        logging.info(f"Запрос к API: POST {url}")
        logging.info(f"Параметры поиска: {query_data}")
        # Важно: этот метод требует POST запрос для поиска по параметрам
        response = requests.post(url, headers=self.headers, json=query_data)
        
        if response.status_code == 200:
            return True, response.json()
        return False, response.text

    def update_worklog(self, issue_id, worklog_id, duration=None, comment=None):
        """
        2. Редактировать запись о затраченном времени.
        Требует ID задачи и ID конкретной записи в ворклоге.
        """
        url = f"{config.YANDEX_BASE_URL}/issues/{issue_id}/worklog/{worklog_id}"
        data = {}
        if duration: data["duration"] = duration
        if comment: data["comment"] = comment
        
        response = requests.patch(url, headers=self.headers, json=data)
        if response.status_code == 200:
            return True, response.json()
        return False, response.text

    def delete_worklog(self, issue_id, worklog_id):
        """
        3. Удалить запись о затраченном времени.
        """
        url = f"{config.YANDEX_BASE_URL}/issues/{issue_id}/worklog/{worklog_id}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204: # 204 No Content означает успех для DELETE
            return True, "Deleted"
        return False, response.text