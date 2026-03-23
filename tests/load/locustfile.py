import random
import string
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
import json


class URLShortenerUser(HttpUser):
    """
    Пользователь для нагрузочного тестирования
    Симулирует реальное поведение пользователя сервиса
    """
    
    wait_time = between(1, 3)  # Ожидание между запросами 1-3 секунды
    
    def on_start(self):
        """
        Действия при старте каждого пользователя:
        - Регистрация нового пользователя
        - Получение токена авторизации
        """
        # Генерация уникальных данных пользователя
        self.username = f"load_user_{random.randint(10000, 99999)}"
        self.email = f"{self.username}@example.com"
        self.password = "LoadTest123!"
        
        # Регистрация пользователя
        with self.client.post("/auth/register", 
                             json={
                                 "username": self.username,
                                 "email": self.email,
                                 "password": self.password
                             },
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")
        
        # Получение токена
        with self.client.post("/auth/token",
                             json={
                                 "username": self.username,
                                 "password": self.password
                             },
                             catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.client.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                response.success()
            else:
                response.failure(f"Token acquisition failed: {response.status_code}")
        
        self.links = []
    
    @task(3)
    def create_short_link(self):
        """
        Создание короткой ссылки
        Вес задачи: 3 (более частая)
        """
        original_url = f"https://example.com/{random.randint(1, 100000)}"
        
        with self.client.post("/links/shorten",
                             json={"original_url": original_url},
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.links.append(data["short_code"])
                response.success()
            else:
                response.failure(f"Failed to create link: {response.status_code}")
    
    @task(5)
    def redirect_to_link(self):
        """
        Переход по короткой ссылке (редирект)
        Самый частый запрос - вес 5
        """
        if self.links:
            short_code = random.choice(self.links)
            with self.client.get(f"/{short_code}",
                                catch_response=True,
                                allow_redirects=False) as response:
                if response.status_code == 307:
                    response.success()
                else:
                    response.failure(f"Redirect failed: {response.status_code}")
    
    @task(2)
    def get_link_stats(self):
        """
        Получение статистики ссылки
        Вес задачи: 2
        """
        if self.links:
            short_code = random.choice(self.links)
            with self.client.get(f"/links/{short_code}/stats",
                                catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get stats: {response.status_code}")
    
    @task(1)
    def search_links(self):
        """
        Поиск ссылок по оригинальному URL
        Вес задачи: 1
        """
        with self.client.get("/links/search?original_url=https://example.com",
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")
    
    @task(1)
    def update_link(self):
        """
        Обновление ссылки
        Вес задачи: 1
        """
        if self.links:
            short_code = random.choice(self.links)
            new_url = f"https://example.com/updated/{random.randint(1, 1000)}"
            with self.client.put(f"/links/{short_code}",
                                json={"original_url": new_url},
                                catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to update link: {response.status_code}")
    
    @task(1)
    def delete_link(self):
        """
        Удаление ссылки
        Вес задачи: 1
        """
        if self.links:
            short_code = random.choice(self.links)
            with self.client.delete(f"/links/{short_code}",
                                   catch_response=True) as response:
                if response.status_code == 204:
                    self.links.remove(short_code)
                    response.success()
                else:
                    response.failure(f"Failed to delete link: {response.status_code}")


class AnonymousUser(HttpUser):
    """
    Анонимный пользователь (без авторизации)
    Симулирует неавторизованных посетителей
    """
    
    wait_time = between(1, 2)
    
    @task(2)
    def create_anonymous_link(self):
        """
        Создание ссылки анонимным пользователем
        """
        original_url = f"https://example.com/anonymous/{random.randint(1, 1000)}"
        
        with self.client.post("/links/shorten",
                             json={"original_url": original_url},
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(3)
    def random_redirect(self):
        """
        Переход по случайной ссылке
        """
        # Генерация случайного кода
        random_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        with self.client.get(f"/{random_code}",
                            catch_response=True,
                            allow_redirects=False) as response:
            if response.status_code in [307, 200, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def search_links(self):
        """
        Поиск ссылок
        """
        with self.client.get("/links/search?original_url=https://example.com",
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Событие при инициализации Locust
    """
    print("Load testing started for URL Shortener Service")
    print(f"Target host: {environment.host}")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """
    Событие при завершении тестов
    """
    print("\nLoad testing completed")
    
    # Сохранение статистики
    stats = environment.runner.stats
    total_requests = stats.num_requests
    total_failures = stats.num_failures
    rps = stats.total_rps
    
    print(f"Total requests: {total_requests}")
    print(f"Total failures: {total_failures}")
    print(f"Requests per second: {rps:.2f}")