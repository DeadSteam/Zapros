import time
import requests
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import quote_plus, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from src.captcha.captcha_solver import CaptchaSolver
from src.top_collect_with_ya_metrics.check_yandex_metrika import BatchYandexMetrikaChecker
from src.core.logger import get_logger, log_exception
from src.core.config import (
    DEFAULT_TIMEOUT,
    SEARCH_MAX_ATTEMPTS,
    SEARCH_TIMEOUT,
    DEFAULT_TIMEOUT_AFTER_SEARCH,
    SEARCH_RETRY_DELAY,
    MAX_LINKS,
    YANDEX_SEARCH_URL,
    REQUEST_TIMEOUT
)


class YandexLinkCollector:
    """
    Класс для сбора ссылок из результатов поиска Яндекс с проверкой HTTPS и Яндекс Метрики.
    
    Обеспечивает поиск ссылок в результатах Яндекс поиска с автоматической проверкой
    на наличие HTTPS и Яндекс Метрики, а также решением CAPTCHA при необходимости.
    
    Attributes:
        driver: WebDriver для управления браузером
        logger: Логгер для записи событий
        wait: WebDriverWait для ожидания элементов
        captcha_solver: Решатель CAPTCHA
        metrika_checker: Проверщик Яндекс Метрики (создается с оптимизированным таймаутом)
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.logger = get_logger('get_link_top')
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
        self.captcha_solver = CaptchaSolver(driver)

    def get_yandex_links(self, query: str, max_links: int = MAX_LINKS) -> List[str]:
        """
        Получает список проверенных ссылок из результатов поиска Яндекс.
        
        Проверяет только указанное количество ссылок, независимо от их валидности,
        затем останавливается и переходит к следующему запросу.
        
        Args:
            query: Поисковый запрос
            max_links: Количество ссылок для проверки (не валидных ссылок!)
            
        Returns:
            Список URL валидных ссылок из числа проверенных (HTTPS + Яндекс Метрика)
        """
        max_attempts = SEARCH_MAX_ATTEMPTS
        found_links = []

        for attempt in range(max_attempts):
            try:
                # Таймаут для поисковых запросов
                self.driver.set_page_load_timeout(SEARCH_TIMEOUT)
                self._perform_search(query)

                # Сбрасываем таймаут после выполнения запроса
                self.driver.set_page_load_timeout(DEFAULT_TIMEOUT_AFTER_SEARCH)

                if self.captcha_solver.check_captcha_present():
                    self.logger.info(f"Обнаружена капча, пытаемся решить (попытка {attempt + 1})")
                    self.captcha_solver.handle_captcha()

                links, processed_successfully = self._find_and_check_links(max_links)
                
                # Если обработка прошла успешно (хотя бы одна ссылка была проверена)
                if processed_successfully:
                    found_links = links
                    if links:
                        self.logger.info(f"Найдено {len(links)} валидных ссылок")
                    else:
                        self.logger.info(f"Проверка завершена, валидных ссылок не найдено")
                    break

                # Если не удалось найти ни одной ссылки для проверки
                self.logger.warning(f"Не найдены ссылки для проверки в запросе {query} (попытка {attempt + 1})")

                if attempt < max_attempts - 1:
                    time.sleep(SEARCH_RETRY_DELAY)

            except Exception as e:
                log_exception(self.logger, f"Ошибка при поиске (попытка {attempt + 1})", e)

                if attempt < max_attempts - 1:
                    time.sleep(SEARCH_RETRY_DELAY)
                    continue
                else:
                    return []

        return found_links

    def _perform_search(self, query: str) -> None:
        """Выполняет поисковый запрос в Яндекс."""
        encoded_query = quote_plus(query)
        self.driver.get(YANDEX_SEARCH_URL.format(encoded_query))

    def _find_and_check_links(self, max_links: int = MAX_LINKS) -> Tuple[List[str], bool]:
        """
        Ищет ссылки в результатах поиска и проверяет их на HTTPS и Яндекс Метрику.
        ОПТИМИЗИРОВАНО: Batch-проверка метрики для всех ссылок сразу.
        
        Проверяет только указанное количество ссылок, независимо от их валидности.
        
        Args:
            max_links: Максимальное количество ссылок для проверки
            
        Returns:
            Кортеж: (список валидных ссылок, флаг успешной обработки)
        """
        try:
            # ЭТАП 1: Собираем ссылки и быстро проверяем HTTPS
            candidate_links = self._collect_and_filter_by_https(max_links)
            
            if not candidate_links:
                return [], False  # Не нашли ни одной ссылки
            
            # ЭТАП 2: Batch-проверка метрики для всех HTTPS-ссылок
            valid_links = self._batch_check_metrika(candidate_links)
            
            self.logger.info(f"Обработано ссылок: {len(candidate_links)}, найдено валидных: {len(valid_links)}")
            return valid_links, True

        except Exception as e:
            log_exception(self.logger, "Ошибка при поиске ссылок", e)
            return [], False

    def _collect_and_filter_by_https(self, max_links: int) -> List[str]:
        """
        Собирает ссылки из поисковой выдачи и фильтрует по HTTPS.
        
        Args:
            max_links: Максимальное количество ссылок для проверки
            
        Returns:
            Список HTTPS-ссылок для проверки метрики
        """
        https_links = []
        processed_count = 0
        
        try:
            # Ищем все элементы результатов поиска
            search_result_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "search-result"))
            )

            # Находим все элементы li, которые содержат ссылки
            search_items = search_result_element.find_elements(By.XPATH, "./li")

            for item in search_items:
                if processed_count >= max_links:
                    self.logger.info(f"Достигнут лимит проверяемых ссылок: {max_links}")
                    break

                try:
                    # Ищем ссылку внутри элемента результата поиска
                    link_element = item.find_element(By.XPATH, ".//div/div[2]/div/a")
                    href = link_element.get_attribute('href')

                    if href:
                        processed_count += 1
                        self.logger.info(f"Обрабатываю ссылку {processed_count}/{max_links}: {href}")
                        
                        # Быстрая проверка HTTPS
                        https_url = self._ensure_https(href)
                        if https_url:
                            https_links.append(https_url)
                            self.logger.info(f"✅ HTTPS проверен: {https_url}")
                        else:
                            self.logger.info(f"❌ HTTPS недоступен: {href}")

                except Exception as e:
                    # Игнорируем элементы без ссылок или с ошибками
                    continue

            return https_links

        except Exception as e:
            log_exception(self.logger, "Ошибка при сборе ссылок", e)
            return []

    def _ensure_https(self, url: str) -> Optional[str]:
        """
        Проверяет и обеспечивает HTTPS для URL.
        
        Args:
            url: Исходный URL
            
        Returns:
            HTTPS URL если доступен, иначе None
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Если уже HTTPS
            if parsed_url.scheme == 'https':
                return url

            # Если HTTP, пробуем HTTPS
            https_url = url.replace('http://', 'https://')
            if self._check_https_availability(https_url):
                return https_url

            return None

        except Exception:
            return None

    def _batch_check_metrika(self, urls: List[str]) -> List[str]:
        """
        Batch-проверка Яндекс Метрики для списка ссылок.
        
        Args:
            urls: Список HTTPS-ссылок для проверки
            
        Returns:
            Список ссылок с найденной метрикой
        """
        valid_links = []
        
        if not urls:
            return valid_links
        
        self.logger.info(f"🚀 Начинаю batch-проверку метрики для {len(urls)} ссылок")
        
        try:
            # Используем batch-проверщик с контекстным менеджером
            with BatchYandexMetrikaChecker(timeout=8) as batch_checker:
                metrika_results = batch_checker.check_sites_batch(urls)
                
                for url, has_metrika in metrika_results.items():
                    if has_metrika:
                        valid_links.append(url)
                        self.logger.info(f"✅ Метрика найдена: {url}")
                    else:
                        self.logger.info(f"❌ Метрика не найдена: {url}")
                        
        except Exception as e:
            log_exception(self.logger, "Ошибка при batch-проверке метрики", e)
            # При ошибке batch-проверки просто возвращаем пустой список
            self.logger.warning("Batch-проверка метрики недоступна, пропускаем проверку метрики")
        
        return valid_links

    # Функция _check_link удалена, так как перешли на batch-проверку в _batch_check_metrika

    def _check_https_availability(self, https_url: str) -> bool:
        """
        Проверяет доступность HTTPS версии сайта.
        
        Args:
            https_url: HTTPS URL для проверки
            
        Returns:
            True, если HTTPS доступен
        """
        try:
            response = requests.head(https_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            return response.status_code < 400
        except Exception:
            return False

    def _is_site_accessible(self, url: str) -> bool:
        """
        Быстрая проверка доступности сайта через HTTP HEAD запрос.
        
        Args:
            url: URL для проверки
            
        Returns:
            True, если сайт доступен
        """
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except Exception:
            # Если HEAD не работает, пробуем GET с минимальным таймаутом
            try:
                response = requests.get(url, timeout=3, stream=True)
                response.close()  # Закрываем соединение сразу
                return response.status_code < 400
            except Exception:
                return False


def get_top_links(driver: WebDriver, query: str, max_links: int = MAX_LINKS) -> Tuple[List[str], bool]:
    """
    Получает список проверенных ссылок из результатов поиска Яндекс.
    
    Функция проверяет только указанное количество ссылок, независимо от их валидности,
    затем останавливается и переходит к следующему запросу.
    Если max_links=1, то будет проверена только первая найденная ссылка.
    
    Args:
        driver: WebDriver для поиска
        query: Поисковый запрос
        max_links: Количество ссылок для проверки (НЕ количество валидных ссылок!)
        
    Returns:
        Кортеж: (список валидных ссылок, флаг успешной обработки)
    """
    logger = get_logger('get_link_top')
    try:
        collector = YandexLinkCollector(driver)
        links = collector.get_yandex_links(query, max_links)
        # Если функция вернула результат (даже пустой список), считаем это успехом
        return links, True
    except Exception as e:
        log_exception(logger, f"Ошибка при получении ссылок для запроса '{query}'", e)
        return [], False
