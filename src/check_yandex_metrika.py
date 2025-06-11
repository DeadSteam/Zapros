import re

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from src.core.logger import get_logger, log_exception
from src.core.config import METRIKA_TIMEOUT


class YandexMetrikaChecker:
    """Класс для проверки наличия Яндекс Метрики на сайтах из выдачи."""
    
    def __init__(self, timeout: int = METRIKA_TIMEOUT):
        """
        Инициализирует проверщик Яндекс Метрики.
        
        Args:
            timeout: Таймаут для загрузки страницы в секундах
        """
        self.timeout = timeout
        self.logger = get_logger('metrika_checker')
        
        # Паттерны для поиска Яндекс Метрики в коде страницы
        self.metrika_patterns = [
            r'function\s*\(\s*m\s*,\s*e\s*,\s*t\s*,\s*r\s*,\s*i\s*,\s*k\s*,\s*a\s*\)',  # Современный паттерн инициализации
            r'https:\/\/mc\.yandex\.ru\/metrika\/tag\.js'  # Новый URL скрипта метрики
        ]

    def create_driver(self) -> Chrome:
        """
        Создает и настраивает экземпляр WebDriver.
        
        Returns:
            Настроенный экземпляр Chrome WebDriver
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
            
            # Установка таймаутов
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_settings.popups": 0,
            })
            
            service = Service(ChromeDriverManager().install())
            driver = Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            
            self.logger.info("WebDriver успешно создан")
            return driver
        except Exception as e:
            log_exception(self.logger, "Ошибка при создании WebDriver", e)
            raise

    def check_site(self, url: str) -> bool:
        """
        Проверяет наличие Яндекс Метрики на указанном сайте.
        
        Args:
            url: URL сайта для проверки
            
        Returns:
            True, если найдена Яндекс Метрика, иначе False
        """
        driver = None
        
        try:
            self.logger.info(f"Проверка сайта: {url}")
            
            # Добавляем протокол, если его нет
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            driver = self.create_driver()
            driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Получаем исходный код страницы
            page_source = driver.page_source
            
            # Проверяем наличие Яндекс Метрики в коде страницы
            has_metrika = self._check_metrika_in_source(page_source)
            
            # Если не нашли в исходном коде, проверяем через JavaScript
            if not has_metrika:
                has_metrika = self._check_metrika_via_js(driver)
            
            status = "найдена" if has_metrika else "не найдена"
            self.logger.info(f"Яндекс Метрика {status} на {url}")
            
            return has_metrika
            
        except TimeoutException:
            self.logger.warning(f"Таймаут при загрузке страницы {url}")
            return False
        except WebDriverException as e:
            log_exception(self.logger, f"Ошибка WebDriver при проверке {url}", e)
            return False
        except Exception as e:
            log_exception(self.logger, f"Ошибка при проверке {url}", e)
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    log_exception(self.logger, "Ошибка при закрытии WebDriver", e)

    def _check_metrika_in_source(self, page_source: str) -> bool:
        """
        Проверяет наличие Яндекс Метрики в исходном коде страницы.
        
        Args:
            page_source: Исходный код страницы
            
        Returns:
            True, если найдена Яндекс Метрика, иначе False
        """
        for pattern in self.metrika_patterns:
            matches = re.search(pattern, page_source)
            if matches:
                return True
        
        return False

    def _check_metrika_via_js(self, driver: Chrome) -> bool:
        """
        Проверяет наличие Яндекс Метрики через JavaScript.
        
        Args:
            driver: Экземпляр WebDriver
            
        Returns:
            True, если найдена Яндекс Метрика, иначе False
        """
        try:
            # Проверка через глобальные объекты Яндекс Метрики
            check_scripts = [
                "return window.Ya && window.Ya.Metrika ? true : false;",
                "return window.Ya && window.Ya.Metrika2 ? true : false;",
                "return window.ym ? true : false;",
                "return window.yaCounter ? Object.keys(window).some(key => key.startsWith('yaCounter')) : false;"
            ]
            
            for script in check_scripts:
                try:
                    result = driver.execute_script(script)
                    if result:
                        return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            log_exception(self.logger, "Ошибка при проверке Яндекс Метрики через JavaScript", e)
            return False 