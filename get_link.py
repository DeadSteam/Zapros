import re
import time
import base64
import logging
from typing import Optional, List, Tuple
from PIL import Image
from io import BytesIO
from urllib.parse import quote_plus, urlparse
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from capsola import solve_captcha
from logger import get_logger, log_exception, captcha_logger


class YandexLinkCollector:
    """Класс для сбора ссылок из результатов поиска Яндекс."""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.logger = get_logger('get_link')
        self.wait = WebDriverWait(driver, 10)

    def get_first_yandex_link(self, query: str, domain: str) -> Optional[str]:
        """Получает первую ссылку из результатов поиска Яндекс."""
        max_attempts = 3

        time.sleep(100)
        for attempt in range(max_attempts):
            try:
                # Таймаут для поисковых запросов
                self.driver.set_page_load_timeout(60)
                self._perform_search(query)
                
                # Сбрасываем таймаут после выполнения запроса
                self.driver.set_page_load_timeout(300)
                
                if self._check_captcha_present():
                    self.logger.info(f"Обнаружена капча, пытаемся решить (попытка {attempt + 1})")
                    self._handle_captcha()
                
                link = self._find_matching_link(domain)
                if link:
                    return link
                    
                self.logger.warning(f"Не найдена подходящая ссылка для запроса {query} (попытка {attempt + 1})")
                
                if attempt < max_attempts - 1:
                    # Если это не последняя попытка, делаем паузу и пробуем снова
                    time.sleep(5)
                
            except Exception as e:
                log_exception(self.logger, f"Ошибка при поиске (попытка {attempt + 1})", e)
                
                if attempt < max_attempts - 1:
                    # Если это не последняя попытка, делаем паузу и пробуем снова
                    time.sleep(5)
                    continue
                else:
                    # Если это последняя попытка, возвращаем None
                    return None
                    
        return None

    def _perform_search(self, query: str) -> None:
        """Выполняет поисковый запрос в Яндекс."""
        encoded_query = quote_plus(query)
        self.driver.get(f"https://yandex.ru/search/?text={encoded_query}&lr=213")

    def _check_captcha_present(self) -> bool:
        """Проверяет наличие капчи на странице."""
        return bool(self.driver.find_elements(By.XPATH, '//*[@id="js-button"]'))

    def _handle_captcha(self) -> None:
        """Обрабатывает различные типы капчи."""
        try:
            self._click_verification_button()
            
            # Ждем появления формы капчи
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/main/div/form')))
            except Exception as e:
                log_exception(self.logger, "Форма капчи не появилась после клика на кнопку верификации", e)
                return
            
            max_attempts = 5
            attempts = 0
            
            while self._is_captcha_form_present() and attempts < max_attempts:
                attempts += 1
                self.logger.info(f"Попытка решения капчи #{attempts}")
                
                try:
                    if self._is_image_captcha():
                        self.logger.info("Обнаружена капча с изображениями")
                        self._solve_image_captcha()
                    elif self._is_text_captcha():
                        self.logger.info("Обнаружена текстовая капча")
                        self._solve_text_captcha()
                    elif self._is_puzzle_captcha():
                        self.logger.info("Обнаружена капча-пазл")
                        self._solve_puzzle_captcha()
                    elif self._is_captcha_solved():
                        self.logger.info("Капча решена успешно")
                        break
                    else:
                        self.logger.warning(f"Неизвестный тип капчи (попытка {attempts})")
                        time.sleep(2)  # Пауза перед следующей проверкой
                except Exception as e:
                    log_exception(self.logger, f"Ошибка при обработке капчи (попытка {attempts})", e)
                    time.sleep(2)  # Пауза перед следующей попыткой
                    
                # Проверяем, решилась ли капча
                if self._is_captcha_solved():
                    self.logger.info("Капча решена успешно")
                    break
                    
                # Пауза между попытками
                time.sleep(3)
                
            if attempts >= max_attempts and self._is_captcha_form_present():
                self.logger.warning("Достигнуто максимальное количество попыток решения капчи")
        except Exception as e:
            log_exception(self.logger, "Критическая ошибка при обработке капчи", e)

    def _click_verification_button(self) -> None:
        """Нажимает на кнопку верификации."""
        try:
            verification_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, 'js-button'))
            )
            actions = ActionChains(self.driver)
            actions.move_to_element(verification_button).perform()
            verification_button.click()
            time.sleep(1)
        except Exception as e:
            log_exception(self.logger, "Не удалось найти или нажать на кнопку верификации", e)
            raise

    def _is_captcha_form_present(self) -> bool:
        """Проверяет наличие формы капчи."""
        try:
            return bool(self.driver.find_elements(By.XPATH, '/html/body/div[1]/div/main/div/form'))
        except Exception as e:
            log_exception(self.logger, "Ошибка при проверке наличия формы капчи", e)
            return False

    def _is_image_captcha(self) -> bool:
        """Проверяет наличие капчи с изображениями."""
        return bool(self.driver.find_elements(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[2]/div/canvas'))

    def _solve_image_captcha(self) -> None:
        """Решает капчу с изображениями."""
        try:
            image_element = self.driver.find_element(By.XPATH, '/html/body/div[1]/div/main/div/form/div/div/div[1]/div/img')
            image_url = image_element.get_attribute('src')
            
            png = self.driver.find_element(By.XPATH, '/html/body/div[1]/div/main/div/form/div/div/div[2]/div').screenshot_as_png
            image = Image.open(BytesIO(png))
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            task = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Используем новый интерфейс capsola
            result = solve_captcha('smart', img_url=image_url, task=task)
            
            if result.success and result.data:
                coordinates = [(float(x), float(y)) for x, y in re.findall(r'x=(\d+\.\d+),y=(\d+\.\d+)', result.data['response'])]
                
                location = image_element.location
                for x, y in coordinates:
                    actions = ActionChains(self.driver)
                    actions.reset_actions()
                    actions.move_by_offset(location['x'] + x, location['y'] + y).click().perform()
                    
                self._click_confirm_button()
            else:
                log_exception(self.logger, f"Не удалось решить капчу с изображениями: {result.error}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении капчи с изображениями", e)

    def _is_text_captcha(self) -> bool:
        """Проверяет наличие текстовой капчи."""
        return bool(self.driver.find_elements(By.XPATH, '//*[@id="xuniq-0-1"]'))

    def _solve_text_captcha(self) -> None:
        """Решает текстовую капчу."""
        try:
            image_element = self.driver.find_element(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[1]/img')
            image_url = image_element.get_attribute('src')
            
            # Используем новый интерфейс capsola
            result = solve_captcha('text', img_url=image_url)
            
            if result.success and result.data:
                element = self.driver.find_element(By.XPATH, '//*[@id="xuniq-0-1"]')
                element.send_keys(result.data['response'])
                self._click_confirm_button()
            else:
                log_exception(self.logger, f"Не удалось решить текстовую капчу: {result.error}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении текстовой капчи", e)

    def _is_puzzle_captcha(self) -> bool:
        """Проверяет наличие капчи-пазла."""
        return bool(self.driver.find_elements(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[3]/div[1]/div[2]'))

    def _solve_puzzle_captcha(self) -> None:
        """Решает капчу-пазл."""
        try:
            page_source = self.driver.page_source
            page_source_base64 = base64.b64encode(page_source.encode('utf-8')).decode('utf-8')
            
            # Используем новый интерфейс capsola
            result = solve_captcha('puzzle', page_source=page_source_base64)
            
            if result.success and result.data:
                count = result.data['response']
                
                for _ in range(int(count)):
                    button = self.driver.find_element(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[3]/div[2]/button[1]')
                    button.click()
                    
                button = self.driver.find_element(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[3]/div[1]/div[2]')
                button.click()
            else:
                log_exception(self.logger, f"Не удалось решить капчу-пазл: {result.error}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении капчи-пазл", e)

    def _is_captcha_solved(self) -> bool:
        """Проверяет, решена ли капча."""
        try:
            # Проверяем наличие поисковой строки, которая появляется после решения капчи
            return bool(self.driver.find_elements(By.XPATH, '/html/body/div[1]/div[1]/header/form/div[1]'))
        except Exception as e:
            log_exception(self.logger, "Ошибка при проверке решения капчи", e)
            return False

    def _click_confirm_button(self) -> None:
        """Нажимает кнопку подтверждения."""
        button = self.driver.find_element(By.XPATH, '//*[@id="advanced-captcha-form"]/div/div/div[3]/button[3]/div')
        button.click()

    def _find_matching_link(self, domain: str) -> Optional[str]:
        """Ищет первую подходящую ссылку в результатах поиска."""
        for position in [2, 3]:
            try:
                xpath = f'//*[@id="search-result"]/li[{position}]/div/div[2]/div/a'
                element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                link = element.get_attribute('href')
                if link and domain in urlparse(link).netloc:
                    return link
            except Exception as e:
                log_exception(self.logger, f"Не удалось получить ссылку на позиции {position}", e)
                continue
        return None


def get_first_yandex_link(driver: WebDriver, query: str, domain: str) -> Optional[str]:
    """Получает первую ссылку из результатов поиска Яндекс."""
    logger = get_logger('get_link')
    try:
        collector = YandexLinkCollector(driver)
        return collector.get_first_yandex_link(query, domain)
    except Exception as e:
        log_exception(logger, f"Ошибка при получении ссылки для запроса '{query}' и домена '{domain}'", e)
        return None