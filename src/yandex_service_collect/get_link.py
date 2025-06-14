import time
from typing import Optional, List
from urllib.parse import quote_plus, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from src.captcha.captcha_solver import CaptchaSolver
from src.core.logger import get_logger, log_exception
from src.core.config import (
    DEFAULT_TIMEOUT,
    SEARCH_MAX_ATTEMPTS,
    SEARCH_TIMEOUT,
    DEFAULT_TIMEOUT_AFTER_SEARCH,
    SEARCH_RETRY_DELAY,
    MAX_LINKS,
    YANDEX_SEARCH_URL
)


class YandexLinkCollector:
    """Класс для сбора ссылок из результатов поиска Яндекс."""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.logger = get_logger('get_link')
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
        self.captcha_solver = CaptchaSolver(driver)

    def get_yandex_links(self, query: str, domain: str, max_links: int = MAX_LINKS) -> List[str]:
        """Получает список ссылок из результатов поиска Яндекс."""
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
                
                links = self._find_matching_links(domain, max_links)
                if links:
                    found_links = links
                    self.logger.info(f"Найдено {len(links)} ссылок")
                    break
                    
                self.logger.warning(f"Не найдены подходящие ссылки для запроса {query} (попытка {attempt + 1})")
                
                if attempt < max_attempts - 1:
                    # Если это не последняя попытка, делаем паузу и пробуем снова
                    time.sleep(SEARCH_RETRY_DELAY)
                
            except Exception as e:
                log_exception(self.logger, f"Ошибка при поиске (попытка {attempt + 1})", e)
                
                if attempt < max_attempts - 1:
                    # Если это не последняя попытка, делаем паузу и пробуем снова
                    time.sleep(SEARCH_RETRY_DELAY)
                    continue
                else:
                    # Если это последняя попытка, возвращаем пустой список
                    return []
                    
        return found_links

    def _perform_search(self, query: str) -> None:
        """Выполняет поисковый запрос в Яндекс."""
        encoded_query = quote_plus(query)
        self.driver.get(YANDEX_SEARCH_URL.format(encoded_query))

    def _find_matching_links(self, domain: str, max_links: int = MAX_LINKS) -> List[str]:
        """Ищет подходящие ссылки в результатах поиска."""
        links = []
        try:
            # Ищем все элементы результатов поиска
            search_result_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "search-result"))
            )
            
            # Находим все элементы li, которые содержат ссылки
            search_items = search_result_element.find_elements(By.XPATH, "./li")
            
            for item in search_items:
                if len(links) >= max_links:
                    break
                
                try:
                    # Ищем ссылку внутри элемента результата поиска
                    link_element = item.find_element(By.XPATH, ".//div/div[2]/div/a")
                    href = link_element.get_attribute('href')
                    
                    # Проверяем, содержит ли URL нужный домен
                    if href and domain in urlparse(href).netloc:
                        links.append(href)
                except Exception as e:
                    # Игнорируем элементы без ссылок или с ошибками
                    continue
            
            self.logger.info(f"Найдено {len(links)} подходящих ссылок")
            return links
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при поиске ссылок", e)
            return []


def get_yandex_links(driver: WebDriver, query: str, domain: str, max_links: int = MAX_LINKS) -> List[str]:
    """Получает список ссылок из результатов поиска Яндекс."""
    logger = get_logger('get_link')
    try:
        collector = YandexLinkCollector(driver)
        return collector.get_yandex_links(query, domain, max_links)
    except Exception as e:
        log_exception(logger, f"Ошибка при получении ссылок для запроса '{query}' и домена '{domain}'", e)
        return []


# Для совместимости со старым кодом
def get_first_yandex_link(driver: WebDriver, query: str, domain: str) -> Optional[str]:
    """Получает первую ссылку из результатов поиска Яндекс."""
    links = get_yandex_links(driver, query, domain, 1)
    return links[0] if links else None