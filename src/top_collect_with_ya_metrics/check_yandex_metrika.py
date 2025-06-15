import re
import requests
from typing import List, Dict, Any
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from src.core.logger import get_logger, log_exception
from src.core.config import METRIKA_TIMEOUT
from src.core.webdriver_manager import WebDriverManager


class BatchYandexMetrikaChecker:
    """
    Оптимизированный класс для проверки Яндекс Метрики на нескольких сайтах
    с переиспользованием одного WebDriver.
    """
    
    def __init__(self, timeout: int = METRIKA_TIMEOUT):
        """
        Инициализирует batch-проверщик Яндекс Метрики.
        
        Args:
            timeout: Таймаут для загрузки страницы в секундах
        """
        self.timeout = timeout
        self.logger = get_logger('batch_metrika_checker')
        self.driver = None
        
        # Паттерны для поиска Яндекс Метрики в коде страницы
        self.metrika_patterns = [
            r'function\s*\(\s*m\s*,\s*e\s*,\s*t\s*,\s*r\s*,\s*i\s*,\s*k\s*,\s*a\s*\)',
            r'https:\/\/mc\.yandex\.ru\/metrika\/tag\.js',
        ]

    def __enter__(self):
        """Контекстный менеджер - создание драйвера."""
        try:
            self.driver = WebDriverManager.get_chrome_driver(headless=True, timeout=self.timeout)
            self.logger.info("BatchYandexMetrikaChecker: WebDriver создан через WebDriverManager")
            return self
        except Exception as e:
            log_exception(self.logger, "Ошибка при создании BatchYandexMetrikaChecker", e)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - закрытие драйвера."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("BatchYandexMetrikaChecker: WebDriver закрыт")
            except Exception as e:
                log_exception(self.logger, "Ошибка при закрытии WebDriver", e)

    def check_sites_batch(self, urls: List[str]) -> Dict[str, bool]:
        """
        Проверяет наличие Яндекс Метрики на нескольких сайтах.
        
        Args:
            urls: Список URL для проверки
            
        Returns:
            Словарь {url: has_metrika}
        """
        results = {}
        
        for url in urls:
            try:
                # Сначала быстрая проверка через requests
                if self._quick_check_via_requests(url):
                    results[url] = True
                    self.logger.info(f"✅ Яндекс Метрика найдена через быструю проверку на {url}")
                    continue
                
                # Затем проверка через переиспользуемый WebDriver
                has_metrika = self._check_via_shared_webdriver(url)
                results[url] = has_metrika
                
                status = "найдена" if has_metrika else "не найдена"
                self.logger.info(f"Яндекс Метрика {status} на {url}")
                
            except Exception as e:
                log_exception(self.logger, f"Ошибка при проверке {url}", e)
                results[url] = False
        
        return results

    def _quick_check_via_requests(self, url: str) -> bool:
        """Быстрая проверка метрики через HTTP запрос."""
        try:
            # Добавляем протокол, если его нет
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            })
            
            if response.status_code == 200:
                page_content = response.text
                return self._check_metrika_in_source(page_content)
            
        except Exception:
            pass
        
        return False

    def _check_via_shared_webdriver(self, url: str) -> bool:
        """Проверка через переиспользуемый WebDriver."""
        if not self.driver:
            return False
            
        try:
            # Добавляем протокол, если его нет
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            self.driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Проверяем в исходном коде
            page_source = self.driver.page_source
            has_metrika = self._check_metrika_in_source(page_source)
            
            # Если не нашли в исходном коде, проверяем через JavaScript
            if not has_metrika:
                has_metrika = self._check_metrika_via_js()
            
            return has_metrika
            
        except TimeoutException:
            self.logger.warning(f"Таймаут при загрузке страницы {url}")
            return False
        except WebDriverException as e:
            self.logger.warning(f"WebDriver ошибка при проверке {url}: {e}")
            # При ошибке WebDriver пробуем пересоздать драйвер
            try:
                if self.driver:
                    self.driver.quit()
                self.driver = WebDriverManager.get_chrome_driver(headless=True, timeout=self.timeout)
            except Exception:
                pass
            return False
        except Exception as e:
            log_exception(self.logger, f"Ошибка при проверке {url}", e)
            return False

    def _check_metrika_in_source(self, page_source: str) -> bool:
        """Проверяет наличие Яндекс Метрики в исходном коде страницы."""
        for pattern in self.metrika_patterns:
            if re.search(pattern, page_source):
                return True
        return False

    def _check_metrika_via_js(self) -> bool:
        """Проверяет наличие Яндекс Метрики через JavaScript."""
        try:
            check_scripts = [
                "return window.Ya && window.Ya.Metrika ? true : false;",
                "return window.Ya && window.Ya.Metrika2 ? true : false;",
                "return window.ym ? true : false;",
                "return window.yaCounter ? Object.keys(window).some(key => key.startsWith('yaCounter')) : false;"
            ]
            
            for script in check_scripts:
                try:
                    result = self.driver.execute_script(script)
                    if result:
                        return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            log_exception(self.logger, "Ошибка при проверке Яндекс Метрики через JavaScript", e)
            return False