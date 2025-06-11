import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

from core.paths import paths
from core.config import LOG_MAX_FILE_SIZE, LOG_BACKUP_COUNT

# Убедимся, что директория для логов существует
paths.LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, log_level: int = logging.INFO, 
                max_file_size: int = LOG_MAX_FILE_SIZE, backup_count: int = LOG_BACKUP_COUNT) -> logging.Logger:
    """
    Настраивает и возвращает логгер с заданным именем, который пишет как в консоль, так и в файл.
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования
        max_file_size: Максимальный размер файла лога в байтах (по умолчанию из config.py)
        backup_count: Количество файлов резервных копий (по умолчанию из config.py)
        
    Returns:
        Настроенный объект логгера
    """
    # Форматтер для файлов и консоли
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        '%Y-%m-%d %H:%M:%S'
    )
    
    # Получаем или создаем логгер
    logger = logging.getLogger(name)
    
    # Если логгер уже настроен, просто возвращаем его
    if logger.handlers:
        return logger
    
    # Устанавливаем уровень логирования
    logger.setLevel(log_level)
    
    # Создаем папку для логов, если её нет
    logs_dir = paths.LOGS_DIR
    
    # Добавляем обработчик для записи в файл
    log_file = logs_dir / f"{name}_{time.strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Возвращает настроенный логгер.
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования
        
    Returns:
        Настроенный объект логгера
    """
    return setup_logger(name, log_level)


# Основной логгер приложения
app_logger = get_logger('app')

# Логгер для капчи
captcha_logger = get_logger('captcha')

# Логгер для поисковых операций
search_logger = get_logger('search')

# Логгер для операций WebDriver
webdriver_logger = get_logger('webdriver')


def log_exception(logger: logging.Logger, message: str, exception: Optional[Exception] = None) -> None:
    """
    Логирует исключение с указанным сообщением.
    
    Args:
        logger: Логгер для записи
        message: Сообщение для логирования
        exception: Исключение для логирования
    """
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True)
    else:
        logger.error(message)


if __name__ == "__main__":
    # Тестируем логгер
    test_logger = get_logger('test')
    test_logger.debug('Это сообщение уровня DEBUG')
    test_logger.info('Это сообщение уровня INFO')
    test_logger.warning('Это сообщение уровня WARNING')
    test_logger.error('Это сообщение уровня ERROR')
    test_logger.critical('Это сообщение уровня CRITICAL') 