import threading
import time
from typing import List
from src.core.logger import get_logger, log_exception
from src.core.paths import paths
from src.core.webdriver_manager import WebDriverManager
from src.yandex_service_collect.get_link import get_yandex_links
from src.core.config import DEFAULT_THREADS_COUNT, MAX_LINKS

class LinkCollector:
    """Класс для сбора ссылок в многопоточном режиме."""
    
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

                    for attempt in range(3):
                        start_time = time.time()
                        links = get_yandex_links(driver, search_query, domain, self.max_links_per_query)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 300:
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

    def _load_queries(self) -> tuple[list, list]:
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

    def _create_threads(self, domains: list, queries: list) -> list:
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

def run_collect_links(num_threads: int = DEFAULT_THREADS_COUNT, max_links_per_query: int = MAX_LINKS) -> None:
    """Запускает сбор ссылок с заданными параметрами."""
    collector = LinkCollector(num_threads, max_links_per_query)
    collector.run() 