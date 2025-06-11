import logging
from typing import Set, Optional
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.firefox import GeckoDriverManager
import tldextract
import time

from paths import paths
from logger import get_logger, log_exception, webdriver_logger


class DomainExtractor:
    """Класс для извлечения доменов из веб-страницы."""
    
    # Список обязательных доменов как статический атрибут класса
    ALWAYS_INCLUDE: Set[str] = {
        "partnersearch.yandex.kz",
        "www.kinopoisk.ru",
        "eats.yandex.com",
        "disk.yandex.com.am",
        "alice.yandex.ru",
        "ir.yandex.ru",
        "yandex.com",
        "360.yandex.com",
        "dialogs.yandex.ru",
        "tv.yandex.by",
        "browser.yandex.by",
        "teacher.yandex.ru",
        "wordstat.yandex.com",
        "eda.yandex.by",
        "business.go.yandex",
        "300.ya.ru",
        "yandex.kz",
        "yandex.eu",
        "docs.yandex.ru",
        "hd.kinopoisk.ru"
    }

    def __init__(self):
        self.logger = get_logger('domain_extractor')
        self.driver: Optional[webdriver.Firefox] = None
        self.unique_domains: Set[str] = set(self.ALWAYS_INCLUDE)

    def init_driver(self) -> None:
        """Инициализирует веб-драйвер Firefox."""
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--headless')
            
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            self.logger.info("Веб-драйвер успешно инициализирован")
        except Exception as e:
            log_exception(self.logger, "Ошибка при инициализации драйвера", e)
            raise

    def extract_domain_from_url(self, url: str) -> Optional[str]:
        """Извлекает домен из URL."""
        try:
            ext = tldextract.extract(url)
            if ext.domain and ext.suffix:
                return f"{ext.subdomain + '.' if ext.subdomain else ''}{ext.domain}.{ext.suffix}"
            return None
        except Exception as e:
            log_exception(self.logger, f"Ошибка при извлечении домена из URL {url}", e)
            return None

    def process_div_element(self, div_element: WebElement) -> None:
        """Обрабатывает элемент div и извлекает домены из ссылок."""
        try:
            anchors = div_element.find_elements(By.TAG_NAME, "a")
            for anchor in anchors:
                url = anchor.get_attribute("href")
                if url:
                    domain = self.extract_domain_from_url(url)
                    if domain:
                        self.unique_domains.add(domain)
        except Exception as e:
            log_exception(self.logger, "Ошибка при обработке div элемента", e)

    def collect_domains(self) -> None:
        """Собирает домены со страницы."""
        url = "https://yandex.ru/all"
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Даем время для загрузки контента

            i = 1
            while True:
                try:
                    div_xpath = f"/html/body/div[1]/div[5]/div/div/div[{i}]"
                    div_element = self.driver.find_element(By.XPATH, div_xpath)
                    self.process_div_element(div_element)
                    i += 1
                except Exception:
                    break  # Прерываем цикл, если не нашли следующий div

            self.logger.info(f"Собрано {len(self.unique_domains)} уникальных доменов")
        except Exception as e:
            log_exception(self.logger, "Ошибка при сборе доменов", e)
            raise

    def save_domains(self) -> None:
        """Сохраняет собранные домены в файл."""
        try:
            with open(paths.DOMAINS_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.unique_domains)))
            self.logger.info(f"Домены сохранены в файл '{paths.DOMAINS_FILE}'")
        except Exception as e:
            log_exception(self.logger, "Ошибка при сохранении доменов", e)
            raise

    def cleanup(self) -> None:
        """Очищает ресурсы."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Веб-драйвер закрыт")

    def run(self) -> None:
        """Запускает полный процесс сбора доменов."""
        try:
            self.init_driver()
            self.collect_domains()
            self.save_domains()
        finally:
            self.cleanup()


def run_collect_domains() -> None:
    """Запускает процесс сбора доменов."""
    logger = get_logger('collect_domains')
    try:
        logger.info("Начало сбора доменов")
        extractor = DomainExtractor()
        extractor.run()
        logger.info("Сбор доменов успешно завершен")
    except Exception as e:
        log_exception(logger, "Ошибка при сборе доменов", e)
        raise


if __name__ == "__main__":
    # Используем нашу систему логирования
    logger = get_logger('collect_domains_main')
    logger.info("Запуск сбора доменов")
    
    try:
        run_collect_domains()
    except Exception as e:
        log_exception(logger, "Критическая ошибка при сборе доменов", e)
    finally:
        logger.info("Завершение работы скрипта")