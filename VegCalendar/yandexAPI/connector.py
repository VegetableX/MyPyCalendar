# yandexAPI/connector.py
import requests
from config import YANDEX_BASE_URL # Импортируем базу

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
        url = f"{YANDEX_BASE_URL}/issues/{issue_id}/worklog"
        
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
        url = f"{YANDEX_BASE_URL}/issues/{issue_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()