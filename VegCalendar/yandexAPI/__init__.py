# yandex_api.py
import requests

class YandexTrackerAPI:
    def __init__(self, token, org_id):
        self.token = token
        self.org_id = org_id
        self.base_url = "https://api.tracker.yandex.net/v2"
        self.headers = {
            "Authorization": f"OAuth {self.token}",
            "X-Org-ID": self.org_id,
            "Content-Type": "application/json"
        }

    def add_worklog(self, issue_id, start_time, duration, comment):
        """
        Добавляет запись о затраченном времени в конкретную задачу.
        Документация: https://cloud.yandex.ru/docs/tracker/concepts/issues/add-worklog
        """
        url = f"{self.base_url}/issues/{issue_id}/worklog"
        data = {
            "start": start_time,    # Формат: "2024-04-22T10:00:00.000+0300"
            "duration": duration,   # Формат: "PT30M"
            "comment": comment
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            return True, response.json()
        else:
            return False, response.text