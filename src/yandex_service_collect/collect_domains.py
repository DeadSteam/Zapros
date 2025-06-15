from typing import Set, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
import tldextract
import time

from src.core.paths import paths
from src.core.logger import get_logger, log_exception
from src.core.config import ALWAYS_INCLUDE_DOMAINS, DOMAIN_LOAD_DELAY, YANDEX_ALL_URL
from src.core.webdriver_manager import WebDriverManager


class DomainExtractor:
    """Класс для извлечения доменов из веб-страницы."""
    
    def __init__(self):
        self.logger = get_logger('domain_extractor')
        self.driver: Optional[webdriver.Firefox] = None
        self.unique_domains: Set[str] = set(ALWAYS_INCLUDE_DOMAINS)

    def init_driver(self) -> None:
        """Инициализирует веб-драйвер через WebDriverManager."""
        try:
            # Используем headless режим для сбора доменов
            self.driver = WebDriverManager.get_firefox_driver(headless=True)
            self.logger.info("Веб-драйвер успешно инициализирован через WebDriverManager")
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
        url = YANDEX_ALL_URL
        
        try:
            self.driver.get(url)
            time.sleep(DOMAIN_LOAD_DELAY)  # Даем время для загрузки контента

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