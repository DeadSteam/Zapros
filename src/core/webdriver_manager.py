from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from src.core.logger import log_exception, webdriver_logger


class WebDriverManager:
    """Класс для управления WebDriver."""

    @staticmethod
    def init_driver() -> webdriver.Firefox:
        """Инициализирует WebDriver Firefox."""
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            # options.add_argument('--headless')  # Раскомментировать для headless режима
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            webdriver_logger.info("WebDriver успешно инициализирован")
            return driver
        except Exception as e:
            log_exception(webdriver_logger, "Ошибка при инициализации WebDriver", e)
            raise
