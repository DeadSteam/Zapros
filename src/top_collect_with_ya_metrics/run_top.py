import threading
import time
from typing import List, Tuple
from src.core.logger import get_logger, log_exception
from src.core.paths import paths
from src.core.webdriver_manager import WebDriverManager
from src.top_collect_with_ya_metrics.get_link_top import get_top_links
from src.core.config import DEFAULT_THREADS_COUNT, MAX_LINKS


class LinkCollector:
    """
    Класс для сбора ссылок в многопоточном режиме.
    
    Обеспечивает параллельную обработку запросов с автоматическим управлением
    WebDriver'ами и механизмом повторных попыток при сбоях.
    
    Attributes:
        num_threads: Количество потоков для параллельной обработки
        max_links_per_query: Максимальное количество ссылок на запрос
        lock: Блокировщик для синхронизации записи в файл
        logger: Логгер для записи событий
    """

    def __init__(self, num_threads: int = DEFAULT_THREADS_COUNT, max_links_per_query: int = MAX_LINKS):
        self.num_threads = num_threads
        self.max_links_per_query = max_links_per_query
        self.lock = threading.Lock()
        self.logger = get_logger('link_collector')

    def worker(self, queries: List[str]) -> None:
        """Рабочий процесс для потока."""
        driver = None
        try:
            driver = WebDriverManager.init_driver()

            for query in queries:
                if query:
                    self.logger.info(f"Обработка запроса: {query}")

                    for attempt in range(3):
                        start_time = time.time()
                        links, processed_successfully = get_top_links(driver, query, self.max_links_per_query)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 300:
                            self.logger.warning(
                                f"Попытка {attempt + 1}: Поток завис ({elapsed_time:.1f}с), перезапускаем...")
                            if driver:
                                driver.quit()
                            driver = WebDriverManager.init_driver()
                            continue

                        # Если обработка прошла успешно (проверили нужное количество ссылок)
                        if processed_successfully:
                            if links:
                                with self.lock:
                                    with open(paths.PARSED_LINKS_TOP_FILE, 'a', encoding='utf-8') as res_file:
                                        for link in links:
                                            res_file.write(link + '\n')
                                self.logger.info(f"Найдено и сохранено {len(links)} ссылок для {query}")
                            else:
                                self.logger.info(f"Запрос '{query}' обработан, валидных ссылок не найдено")
                            break
                        else:
                            self.logger.warning(f"Попытка {attempt + 1}: Ошибка при обработке запроса {query}")
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
            queries = self._load_queries()
            threads = self._create_threads(queries)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            self.logger.info("Обработка файла завершена")
        except Exception as e:
            log_exception(self.logger, "Ошибка при сборе ссылок", e)
            raise

    def _load_queries(self) -> List[str]:
        """Загружает запросы из файла (полные строки)."""
        queries = []
        try:
            with open(paths.KEYWORDS_TOP_FILE, 'r', encoding='utf-8') as txt_file:
                for line in txt_file:
                    line = line.strip()
                    if line:  # Если строка не пустая
                        queries.append(line)
            return queries
        except Exception as e:
            log_exception(self.logger, "Ошибка при загрузке запросов", e)
            raise

    def _create_threads(self, queries: List[str]) -> List[threading.Thread]:
        """Создает потоки для обработки запросов."""
        threads = []
        queries_per_thread = len(queries) // self.num_threads

        for i in range(self.num_threads):
            start = i * queries_per_thread
            end = len(queries) if i == self.num_threads - 1 else (i + 1) * queries_per_thread
            subset_queries = queries[start:end]
            thread = threading.Thread(target=self.worker, args=(subset_queries,))
            threads.append(thread)

        return threads


def run_collect_top_links(num_threads: int = DEFAULT_THREADS_COUNT, max_links_per_query: int = MAX_LINKS) -> None:
    """Запускает сбор ссылок с заданными параметрами."""
    collector = LinkCollector(num_threads, max_links_per_query)
    collector.run()