import os
from typing import Dict, Any, Set
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла, если он существует
load_dotenv()

# Функция для получения значения из переменных окружения или значения по умолчанию
def get_env(key: str, default: Any) -> Any:
    """Получает значение из переменных окружения или возвращает значение по умолчанию."""
    value = os.getenv(key)
    
    if value is None:
        return default
    
    # Преобразуем строковые значения в соответствующие типы
    if isinstance(default, int):
        return int(value)
    elif isinstance(default, float):
        return float(value)
    elif isinstance(default, bool):
        return value.lower() in ('true', 'yes', '1')
    else:
        return value

# Общие настройки
DEFAULT_TIMEOUT = get_env('DEFAULT_TIMEOUT', 10)  # Стандартное время ожидания для WebDriverWait
REQUEST_TIMEOUT = get_env('REQUEST_TIMEOUT', 30)  # Таймаут для HTTP-запросов

# Настройки для поиска ссылок
SEARCH_MAX_ATTEMPTS = get_env('SEARCH_MAX_ATTEMPTS', 3)  # Максимальное количество попыток поиска
SEARCH_TIMEOUT = get_env('SEARCH_TIMEOUT', 60)  # Таймаут для поисковых запросов
DEFAULT_TIMEOUT_AFTER_SEARCH = get_env('DEFAULT_TIMEOUT_AFTER_SEARCH', 300)  # Таймаут после выполнения запроса
SEARCH_RETRY_DELAY = get_env('SEARCH_RETRY_DELAY', 5)  # Задержка между попытками поиска в секундах
MAX_LINKS = get_env('MAX_LINKS', 10)  # Максимальное количество возвращаемых ссылок по умолчанию

# Настройки для обработки капчи
CAPTCHA_MAX_ATTEMPTS = get_env('CAPTCHA_MAX_ATTEMPTS', 5)  # Максимальное количество попыток решения капчи
CAPTCHA_RETRY_DELAY = get_env('CAPTCHA_RETRY_DELAY', 3)  # Задержка между попытками решения капчи в секундах
CAPTCHA_ERROR_DELAY = get_env('CAPTCHA_ERROR_DELAY', 2)  # Задержка после ошибки при обработке капчи
CAPTCHA_VERIFICATION_DELAY = get_env('CAPTCHA_VERIFICATION_DELAY', 1)  # Задержка после клика на кнопку верификации

# Настройки для Yandex
YANDEX_SEARCH_URL = get_env('YANDEX_SEARCH_URL', 'https://yandex.ru/search/?text={}&lr=213')

# Настройки логирования
LOG_MAX_FILE_SIZE = get_env('LOG_MAX_FILE_SIZE', 10 * 1024 * 1024)  # Максимальный размер файла лога (10MB)
LOG_BACKUP_COUNT = get_env('LOG_BACKUP_COUNT', 5)  # Количество файлов резервных копий логов

# Настройки для проверки Яндекс Метрики
METRIKA_TIMEOUT = get_env('METRIKA_TIMEOUT', 30)  # Таймаут для загрузки страницы при проверке Яндекс Метрики

# Настройки для Capsola API
CAPSOLA_API_URL = get_env('CAPSOLA_API_URL', 'https://api.capsola.cloud')  # Базовый URL API Capsola
CAPSOLA_API_RESULT_DELAY = get_env('CAPSOLA_API_RESULT_DELAY', 2)  # Задержка между запросами результата капчи в секундах

# Настройки для Bukvarix API
BUKVARIX_API_URL = get_env('BUKVARIX_API_URL', 'http://api.bukvarix.com/v1/site/')  # URL API Bukvarix
BUKVARIX_REQUEST_LIMIT = get_env('BUKVARIX_REQUEST_LIMIT', 10000)  # Лимит запросов к API Bukvarix
BUKVARIX_RETRY_DELAY = get_env('BUKVARIX_RETRY_DELAY', 10)  # Задержка между запросами к API Bukvarix в секундах

# Настройки для сборщика ключевых слов
KEYWORDS_LIMIT = get_env('KEYWORDS_LIMIT', 50000)  # Максимальное количество ключевых слов для сохранения

# Настройки для параллельной обработки
DEFAULT_THREADS_COUNT = get_env('DEFAULT_THREADS_COUNT', 4)  # Количество потоков по умолчанию
MAX_TIMEOUT_PER_REQUEST = get_env('MAX_TIMEOUT_PER_REQUEST', 300)  # Максимальное время на один запрос в секундах
MAX_ATTEMPTS_PER_QUERY = get_env('MAX_ATTEMPTS_PER_QUERY', 3)  # Максимальное количество попыток для одного запроса

# Настройки для сбора доменов
DOMAIN_LOAD_DELAY = get_env('DOMAIN_LOAD_DELAY', 3)  # Задержка для загрузки контента при сборе доменов в секундах
YANDEX_ALL_URL = get_env('YANDEX_ALL_URL', 'https://yandex.ru/all')  # URL для сбора доменов

# Обязательные домены для включения
ALWAYS_INCLUDE_DOMAINS: Set[str] = {
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