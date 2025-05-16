import time
import threading
from typing import List, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from get_link import get_first_yandex_link
from collect_domains import run_collect_domains
from collect_keywords import run_collect_keywords
from create_result import run_create_result
from paths import paths
from logger import get_logger, log_exception, app_logger, webdriver_logger


class WebDriverManager:
    """Класс для управления WebDriver."""
    
    @staticmethod
    def init_driver() -> webdriver.Chrome:
        """Инициализирует WebDriver."""
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            # options.add_argument('--headless')
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            webdriver_logger.info("WebDriver успешно инициализирован")
            return driver
        except Exception as e:
            log_exception(webdriver_logger, "Ошибка при инициализации WebDriver", e)
            raise

class LinkCollector:
    """Класс для сбора ссылок."""
    
    def __init__(self, num_threads: int):
        self.num_threads = num_threads
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

                    for attempt in range(3):
                        start_time = time.time()
                        first_link = get_first_yandex_link(driver, search_query, domain)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 300:
                            self.logger.warning(f"Попытка {attempt + 1}: Поток завис ({elapsed_time:.1f}с), перезапускаем...")
                            if driver:
                                driver.quit()
                            driver = WebDriverManager.init_driver()
                            continue

                        if first_link:
                            with self.lock:
                                with open(paths.PARSED_LINKS_FILE, 'a', encoding='utf-8') as res_file:
                                    res_file.write(first_link + '\n')
                            self.logger.info(f"Найдена ссылка: {first_link}")
                            break
                        else:
                            self.logger.warning(f"Попытка {attempt + 1}: Ссылка не найдена для {search_query}")
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
        self.num_threads = 0

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
            self.num_threads = int(input("Введите количество потоков: "))
            #paths.cleanup()  # Очищаем директории
            #run_collect_domains()  # Собираем домены
            #run_collect_keywords()  # Собираем ключевые слова
            collector = LinkCollector(self.num_threads)
            collector.run()  # Собираем ссылки
            run_create_result()  # Создаем финальный результат
        except ValueError:
            self.logger.error("Некорректное число потоков")
            print("Некорректное число потоков. Попробуйте снова.")
        except Exception as e:
            log_exception(self.logger, "Ошибка в режиме одного файла", e)
            print(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    # Используем нашу систему логирования
    app_logger.info("Запуск приложения")
    
    app = Application()
    app.run()
