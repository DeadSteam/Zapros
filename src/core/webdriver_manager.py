from typing import Optional, Union
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager

from src.core.logger import log_exception, webdriver_logger


class WebDriverManager:
    """Универсальный класс для управления WebDriver'ами."""
    
    _firefox_instance: Optional[webdriver.Firefox] = None
    _chrome_instance: Optional[webdriver.Chrome] = None

    @classmethod
    def get_firefox_driver(cls, headless: bool = False, reuse: bool = False) -> webdriver.Firefox:
        """
        Получает Firefox WebDriver.
        
        Args:
            headless: Запустить в headless режиме
            reuse: Переиспользовать существующий экземпляр (если есть)
            
        Returns:
            Экземпляр Firefox WebDriver
        """
        if reuse and cls._firefox_instance:
            webdriver_logger.info("Переиспользование существующего Firefox WebDriver")
            return cls._firefox_instance
            
        try:
            options = FirefoxOptions()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            if headless:
                options.add_argument('--headless')
                webdriver_logger.info("Firefox WebDriver создается в headless режиме")
            
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            
            if reuse:
                cls._firefox_instance = driver
                
            webdriver_logger.info("Firefox WebDriver успешно инициализирован")
            return driver
            
        except Exception as e:
            log_exception(webdriver_logger, "Ошибка при инициализации Firefox WebDriver", e)
            raise

    @classmethod
    def get_chrome_driver(cls, headless: bool = True, reuse: bool = False, timeout: int = 30) -> webdriver.Chrome:
        """
        Получает Chrome WebDriver.
        
        Args:
            headless: Запустить в headless режиме (по умолчанию True для производительности)
            reuse: Переиспользовать существующий экземпляр (если есть)
            timeout: Таймаут загрузки страницы
            
        Returns:
            Экземпляр Chrome WebDriver
        """
        if reuse and cls._chrome_instance:
            webdriver_logger.info("Переиспользование существующего Chrome WebDriver")
            return cls._chrome_instance
            
        try:
            chrome_options = ChromeOptions()
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
            
            if headless:
                chrome_options.add_argument("--headless")
                webdriver_logger.info("Chrome WebDriver создается в headless режиме")
            
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_settings.popups": 0,
            })
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(timeout)
            
            if reuse:
                cls._chrome_instance = driver
                
            webdriver_logger.info("Chrome WebDriver успешно инициализирован")
            return driver
            
        except Exception as e:
            log_exception(webdriver_logger, "Ошибка при инициализации Chrome WebDriver", e)
            raise

    @classmethod
    def init_driver(cls, browser: str = "firefox", **kwargs) -> Union[webdriver.Firefox, webdriver.Chrome]:
        """
        Инициализирует WebDriver (обратная совместимость).
        
        Args:
            browser: Тип браузера ("firefox" или "chrome")
            **kwargs: Дополнительные параметры для драйвера
            
        Returns:
            Экземпляр WebDriver
        """
        if browser.lower() == "chrome":
            return cls.get_chrome_driver(**kwargs)
        else:
            return cls.get_firefox_driver(**kwargs)

    @classmethod
    def quit_all(cls) -> None:
        """Закрывает все сохраненные экземпляры WebDriver."""
        if cls._firefox_instance:
            try:
                cls._firefox_instance.quit()
                webdriver_logger.info("Firefox WebDriver закрыт")
            except Exception as e:
                log_exception(webdriver_logger, "Ошибка при закрытии Firefox WebDriver", e)
            finally:
                cls._firefox_instance = None
                
        if cls._chrome_instance:
            try:
                cls._chrome_instance.quit()
                webdriver_logger.info("Chrome WebDriver закрыт")
            except Exception as e:
                log_exception(webdriver_logger, "Ошибка при закрытии Chrome WebDriver", e)
            finally:
                cls._chrome_instance = None

    @classmethod
    def recreate_driver(cls, browser: str, **kwargs) -> Union[webdriver.Firefox, webdriver.Chrome]:
        """
        Пересоздает драйвер (полезно при сбоях).
        
        Args:
            browser: Тип браузера ("firefox" или "chrome")
            **kwargs: Дополнительные параметры для драйвера
            
        Returns:
            Новый экземпляр WebDriver
        """
        if browser.lower() == "chrome":
            if cls._chrome_instance:
                try:
                    cls._chrome_instance.quit()
                except:
                    pass
                cls._chrome_instance = None
            return cls.get_chrome_driver(reuse=True, **kwargs)
        else:
            if cls._firefox_instance:
                try:
                    cls._firefox_instance.quit()
                except:
                    pass
                cls._firefox_instance = None
            return cls.get_firefox_driver(reuse=True, **kwargs)
