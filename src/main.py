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


class WebDriverManager:
    """Класс для управления WebDriver."""
    
    @staticmethod
    def init_driver() -> webdriver.Firefox:
        """Инициализирует WebDriver."""
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            # options.add_argument('--headless')
            
            # Сначала проверяем, есть ли локальный драйвер
            local_driver_path = os.path.join(paths.BASE_DIR, 'drivers', 'geckodriver.exe')
            if os.path.exists(local_driver_path):
                webdriver_logger.info(f"Используем локальный GeckoDriver: {local_driver_path}")
                service = Service(executable_path=local_driver_path)
            else:
                # Пытаемся загрузить через WebDriverManager
                try:
                    webdriver_logger.info("Локальный драйвер не найден, пытаемся загрузить автоматически")
                    service = Service(GeckoDriverManager().install())
                except Exception as e:
                    # Если не удалось загрузить, пробуем использовать драйвер из PATH
                    webdriver_logger.warning(f"Не удалось загрузить GeckoDriver: {str(e)}")
                    webdriver_logger.info("Пытаемся использовать GeckoDriver из системного PATH")
                    service = Service(executable_path="geckodriver")
            
            driver = webdriver.Firefox(service=service, options=options)
            webdriver_logger.info("WebDriver успешно инициализирован")
            return driver
        except Exception as e:
            log_exception(webdriver_logger, "Ошибка при инициализации WebDriver", e)
            raise

class LinkCollector:
    """Класс для сбора ссылок."""
    
    def __init__(self, num_threads: int = DEFAULT_THREADS_COUNT, max_links_per_query: int = MAX_LINKS):
        self.num_threads = num_threads
        self.max_links_per_query = max_links_per_query
        self.lock = threading.Lock()
        self.logger = get_logger('link_collector')

    def worker(self, domains: List[str], queries: List[str]) -> None:
        """Рабочий процесс для потока."""
        driver = None
        try:
            driver = WebDriverManager.init_driver()
            
            for i, query in enumerate(queries):
                if query:
                    domain = domains[i]
                    search_query = f"site:{domain} {query}"
                    self.logger.info(f"Обработка запроса: {search_query}")

                    for attempt in range(MAX_ATTEMPTS_PER_QUERY):
                        start_time = time.time()
                        links = get_yandex_links(driver, search_query, domain, self.max_links_per_query)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > MAX_TIMEOUT_PER_REQUEST:
                            self.logger.warning(f"Попытка {attempt + 1}: Поток завис ({elapsed_time:.1f}с), перезапускаем...")
                            if driver:
                                driver.quit()
                            driver = WebDriverManager.init_driver()
                            continue

                        if links:
                            with self.lock:
                                with open(paths.PARSED_LINKS_FILE, 'a', encoding='utf-8') as res_file:
                                    for link in links:
                                        res_file.write(link + '\n')
                            self.logger.info(f"Найдено и сохранено {len(links)} ссылок для {search_query}")
                            break
                        else:
                            self.logger.warning(f"Попытка {attempt + 1}: Ссылки не найдены для {search_query}")
        except Exception as e:
            log_exception(self.logger, "Критическая ошибка в рабочем потоке", e)
        finally:
            if driver:
                try:
                    driver.quit()
                    self.logger.info("Драйвер закрыт")
                except Exception as e:
                    self.logger.error(f"Ошибка при закрытии драйвера: {str(e)}")

    def run(self) -> None:
        """Запускает процесс сбора ссылок."""
        try:
            domains, queries = self._load_queries()
            threads = self._create_threads(domains, queries)
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
                
            self.logger.info("Обработка файла завершена")
        except Exception as e:
            log_exception(self.logger, "Ошибка при сборе ссылок", e)
            raise

    def _load_queries(self) -> Tuple[List[str], List[str]]:
        """Загружает запросы из файла."""
        domains = []
        queries = []
        try:
            with open(paths.KEYWORDS_FILE, 'r', encoding='utf-8') as txt_file:
                for line in txt_file:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        domains.append(parts[0])
                        queries.append(parts[1])
            return domains, queries
        except Exception as e:
            log_exception(self.logger, "Ошибка при загрузке запросов", e)
            raise

    def _create_threads(self, domains: List[str], queries: List[str]) -> List[threading.Thread]:
        """Создает потоки для обработки запросов."""
        threads = []
        queries_per_thread = len(queries) // self.num_threads
        
        for i in range(self.num_threads):
            start = i * queries_per_thread
            end = len(queries) if i == self.num_threads - 1 else (i + 1) * queries_per_thread
            subset_domains = domains[start:end]
            subset_queries = queries[start:end]
            thread = threading.Thread(target=self.worker, args=(subset_domains, subset_queries))
            threads.append(thread)
        
        return threads


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
