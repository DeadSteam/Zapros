from typing import List, Optional
import random
from pathlib import Path
from dataclasses import dataclass
import sys

from core.paths import paths
from core.logger import get_logger, log_exception


@dataclass
class ProcessingResult:
    """Результат обработки файла."""
    success: bool
    message: str
    error: Optional[Exception] = None


class FileProcessor:
    def __init__(self, input_file: Path, output_file: Path):
        self.input_file = input_file
        self.output_file = output_file
        self.logger = get_logger('file_processor')

    def read_lines(self) -> List[str]:
        """Считывает все строки из входного файла."""
        try:
            with open(self.input_file, "r", encoding="utf-8") as file:
                lines = file.readlines()
                self.logger.info(f"Прочитано {len(lines)} строк из {self.input_file}")
                return lines
        except FileNotFoundError:
            log_exception(self.logger, f"Файл {self.input_file} не найден")
            raise
        except Exception as e:
            log_exception(self.logger, f"Ошибка при чтении файла {self.input_file}", e)
            raise

    @staticmethod
    def clean_lines(lines: List[str]) -> List[str]:
        """Очищает строки от пустых значений и фильтрует по http."""
        cleaned = [line.strip() for line in lines if line.strip().startswith("http")]
        return cleaned

    def write_lines(self, lines: List[str]) -> None:
        """Записывает строки в выходной файл."""
        try:
            with open(self.output_file, "w", encoding="utf-8") as file:
                file.write("\n".join(lines) + "\n")
            self.logger.info(f"Записано {len(lines)} строк в {self.output_file}")
        except Exception as e:
            log_exception(self.logger, f"Ошибка при записи в файл {self.output_file}", e)
            raise

    def remove_duplicates(self) -> None:
        """Удаляет дубликаты из файла."""
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                unique_lines = set(lines)
            
            if len(unique_lines) < len(lines):
                self.logger.info(f"Удалено {len(lines) - len(unique_lines)} дубликатов")

            with open(self.output_file, "w", encoding="utf-8") as f:
                f.writelines(unique_lines)
        except Exception as e:
            log_exception(self.logger, f"Ошибка при удалении дубликатов из {self.output_file}", e)
            raise

    def shuffle_lines(self) -> None:
        """Перемешивает строки в файле."""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            random.shuffle(lines)

            with open(self.output_file, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            self.logger.info("Строки успешно перемешаны")
        except Exception as e:
            log_exception(self.logger, f"Ошибка при перемешивании строк в {self.output_file}", e)
            raise

    def process(self) -> ProcessingResult:
        """Выполняет полный цикл обработки файла."""
        try:
            self.logger.info(f"Начало обработки файла {self.input_file}")
            
            lines = self.read_lines()
            cleaned_lines = self.clean_lines(lines)
            self.write_lines(cleaned_lines)
            self.remove_duplicates()
            self.shuffle_lines()
            
            self.logger.info("Обработка файла успешно завершена")
            return ProcessingResult(success=True, message="Success")
        except Exception as e:
            log_exception(self.logger, f"Ошибка при обработке файла {self.input_file}", e)
            return ProcessingResult(success=False, message=f"Error: {str(e)}", error=e)


def run_create_result(mode: str = "regular") -> ProcessingResult:
    """
    Запускает обработку файлов.
    
    Args:
        mode: Режим работы:
            - "regular" - обычный режим (parsed_links.txt → result.txt)
            - "top" - топ-режим (parsed_links_top.txt → result_top.txt)
    """
    try:
        logger = get_logger('create_result_runner')
        
        if mode == "top":
            input_file = paths.PARSED_LINKS_TOP_FILE
            output_file = paths.RESULT_TOP_FILE
            logger.info("Запуск обработки результатов в ТОП-режиме")
        elif mode == "regular":
            input_file = paths.PARSED_LINKS_FILE
            output_file = paths.RESULT_FILE
            logger.info("Запуск обработки результатов в обычном режиме")
        else:
            raise ValueError(f"Неизвестный режим: {mode}. Используйте 'regular' или 'top'")
        
        logger.info(f"Входной файл: {input_file}")
        logger.info(f"Выходной файл: {output_file}")
        
        processor = FileProcessor(input_file, output_file)
        result = processor.process()
        
        if result.success:
            logger.info(f"Обработка результатов в режиме '{mode}' успешно завершена")
        else:
            logger.warning(f"Обработка результатов в режиме '{mode}' завершена с ошибкой: {result.message}")
        
        return result
        
    except Exception as e:
        logger = get_logger('create_result_runner')
        log_exception(logger, f"Непредвиденная ошибка при запуске обработки результатов в режиме '{mode}'", e)
        return ProcessingResult(success=False, message=f"Error: {str(e)}", error=e)


if __name__ == "__main__":
    try:
        logger = get_logger('create_result')
        
        # Проверяем аргументы
        if len(sys.argv) == 1:
            # Без аргументов - используем режим по умолчанию
            logger.info("Запуск в режиме по умолчанию (regular)")
            result = run_create_result("regular")
            sys.exit(0 if result.success else 1)
        elif len(sys.argv) == 2:
            # Один аргумент - режим работы
            mode = sys.argv[1].lower()
            if mode in ["regular", "top"]:
                logger.info(f"Запуск в режиме: {mode}")
                result = run_create_result(mode)
                sys.exit(0 if result.success else 1)
            else:
                logger.error("Использование: python create_result.py [regular|top] или python create_result.py <input_file> <output_file>")
                sys.exit(1)
        elif len(sys.argv) == 3:
            # Два аргумента - старый режим с указанием файлов
            input_file = sys.argv[1]
            output_file = sys.argv[2]

            logger.info(f"Начало обработки: вход={input_file}, выход={output_file}")
            processor = FileProcessor(input_file, output_file)
            lines = processor.read_lines()
            cleaned_lines = processor.clean_lines(lines)
            processor.write_lines(cleaned_lines)
            logger.info(f"Обработка завершена: {len(cleaned_lines)}/{len(lines)} записей сохранено")
        else:
            logger.error("Использование:")
            logger.error("  python create_result.py                    # режим по умолчанию")
            logger.error("  python create_result.py [regular|top]      # указанный режим")
            logger.error("  python create_result.py <input> <output>   # произвольные файлы")
            sys.exit(1)
            
    except Exception as e:
        log_exception(logger, "Ошибка при выполнении create_result.py", e)
        sys.exit(1)
