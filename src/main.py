import sys
import os

from src.yandex_service_collect.collect_domains import run_collect_domains
from src.yandex_service_collect.collect_keywords import run_collect_keywords
from src.yandex_service_collect.run import run_collect_links

# Добавляем директорию src в Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import threading
from typing import List, Tuple
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from src.yandex_service_collect.get_link import get_yandex_links
from create_result import run_create_result
from core.paths import paths
from core.logger import get_logger, log_exception, app_logger, webdriver_logger
from core.config import DEFAULT_THREADS_COUNT, MAX_LINKS, MAX_TIMEOUT_PER_REQUEST, MAX_ATTEMPTS_PER_QUERY

class Application:
    """Основной класс приложения."""
    
    def __init__(self):
        self.logger = get_logger('application')
        self.num_threads = DEFAULT_THREADS_COUNT
        self.max_links_per_query = MAX_LINKS

    def run(self) -> None:
        """Запускает приложение."""
        while True:
            self._show_menu()
            choice = input("Введите номер выбора: ")
            
            if choice == "1":
                self._run_single_mode()
            elif choice == "2":
                self.logger.info("Выход из программы")
                break
            else:
                print("Некорректный выбор. Попробуйте снова.")

    def _show_menu(self) -> None:
        """Показывает меню."""
        print("Выберите режим работы:")
        print("1. Режим одного файла (Single Mode)")
        print("2. Выйти")

    def _run_single_mode(self) -> None:
        """Запускает режим одного файла."""
        try:
            self.num_threads = int(input(f"Введите количество потоков (по умолчанию {DEFAULT_THREADS_COUNT}): ") or DEFAULT_THREADS_COUNT)
            self.max_links_per_query = int(input(f"Введите количество ссылок для каждого запроса (макс. {MAX_LINKS}, по умолчанию {MAX_LINKS}): ") or MAX_LINKS)
            
            if self.max_links_per_query <= 0 or self.max_links_per_query > MAX_LINKS:
                self.max_links_per_query = MAX_LINKS
                print(f"Установлено значение по умолчанию: {self.max_links_per_query}")
            
            #paths.cleanup()  # Очищаем директории
            #run_collect_domains()  # Собираем домены
            #run_collect_keywords()  # Собираем ключевые слова
            run_collect_links(self.num_threads, self.max_links_per_query)  # Собираем ссылки
            run_create_result()  # Создаем финальный результат
        except Exception as e:
            log_exception(self.logger, "Ошибка в режиме одного файла", e)
            print(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    # Используем нашу систему логирования
    app_logger.info("Запуск приложения")
    
    app = Application()
    app.run()
