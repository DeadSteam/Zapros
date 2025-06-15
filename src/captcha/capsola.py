import time
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests
from dotenv import load_dotenv
import os

from src.core.logger import get_logger, log_exception
from src.core.config import CAPSOLA_API_URL, CAPSOLA_API_RESULT_DELAY


@dataclass
class CapsolaResponse:
    """Результат запроса к API Capsola."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CapsolaAPI:
    """Класс для работы с API Capsola."""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('CAPSOLA_API_KEY')
        self.logger = get_logger('capsola_api')
        self.base_url = CAPSOLA_API_URL
        
        if not self.api_key:
            raise ValueError("API ключ не найден в .env файле")
            
        self.headers = {
            'Content-type': 'application/json',
            'X-API-Key': self.api_key
        }

    def _create_task(self, data: Dict[str, Any]) -> Optional[str]:
        """Создает задачу в API."""
        try:
            response = requests.post(
                url=f'{self.base_url}/create',
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status'] == 1:
                return result['response']
            return None
        except Exception as e:
            log_exception(self.logger, "Ошибка при создании задачи", e)
            return None

    def _get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получает результат задачи."""
        try:
            while True:
                time.sleep(CAPSOLA_API_RESULT_DELAY)
                response = requests.post(
                    url=f'{self.base_url}/result',
                    json={'id': task_id},
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                if result['status'] == 1:
                    return result
                if result['status'] == 0 and result['response'] != 'CAPCHA_NOT_READY':
                    return None
        except Exception as e:
            log_exception(self.logger, "Ошибка при получении результата", e)
            return None

    def solve_smart_captcha(self, img_url: str, task: str) -> CapsolaResponse:
        """Решает SmartCaptcha."""
        try:
            # Получаем изображение
            img_response = requests.get(img_url)
            img_response.raise_for_status()
            click_base64 = base64.b64encode(img_response.content).decode('utf-8')
            
            # Создаем задачу
            data = {
                'type': 'SmartCaptcha',
                'click': click_base64,
                'task': task,
            }
            
            task_id = self._create_task(data)
            if not task_id:
                return CapsolaResponse(success=False, error="Не удалось создать задачу")
            
            # Получаем результат
            result = self._get_result(task_id)
            if result:
                return CapsolaResponse(success=True, data=result)
            return CapsolaResponse(success=False, error="Не удалось получить результат")
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении SmartCaptcha", e)
            return CapsolaResponse(success=False, error=str(e))

    def solve_text_captcha(self, img_url: str) -> CapsolaResponse:
        """Решает TextCaptcha."""
        try:
            # Получаем изображение
            img_response = requests.get(img_url)
            img_response.raise_for_status()
            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
            
            # Создаем задачу
            data = {
                'type': 'TextCaptcha',
                'task': image_base64,
            }
            
            task_id = self._create_task(data)
            if not task_id:
                return CapsolaResponse(success=False, error="Не удалось создать задачу")
            
            # Получаем результат
            result = self._get_result(task_id)
            if result:
                return CapsolaResponse(success=True, data=result)
            return CapsolaResponse(success=False, error="Не удалось получить результат")
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении TextCaptcha", e)
            return CapsolaResponse(success=False, error=str(e))

    def solve_puzzle_captcha(self, page_source: str) -> CapsolaResponse:
        """Решает PuzzleCaptcha."""
        try:
            # Создаем задачу
            data = {
                'type': 'PazlCaptcha',
                'task': page_source,
            }
            
            task_id = self._create_task(data)
            if not task_id:
                return CapsolaResponse(success=False, error="Не удалось создать задачу")
            
            # Получаем результат
            result = self._get_result(task_id)
            if result:
                return CapsolaResponse(success=True, data=result)
            return CapsolaResponse(success=False, error="Не удалось получить результат")
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при решении PuzzleCaptcha", e)
            return CapsolaResponse(success=False, error=str(e))


def solve_captcha(captcha_type: str, **kwargs) -> CapsolaResponse:
    """Универсальная функция для решения капчи."""
    logger = get_logger('capsola')
    try:
        api = CapsolaAPI()
        
        if captcha_type == 'smart':
            return api.solve_smart_captcha(kwargs['img_url'], kwargs['task'])
        elif captcha_type == 'text':
            return api.solve_text_captcha(kwargs['img_url'])
        elif captcha_type == 'puzzle':
            return api.solve_puzzle_captcha(kwargs['page_source'])
        else:
            return CapsolaResponse(success=False, error=f"Неизвестный тип капчи: {captcha_type}")
            
    except Exception as e:
        log_exception(logger, "Ошибка при решении капчи", e)
        return CapsolaResponse(success=False, error=str(e))


if __name__ == "__main__":
    # Тестирование модуля
    logger = get_logger('capsola_test')
    logger.info("Тестирование модуля Capsola")
