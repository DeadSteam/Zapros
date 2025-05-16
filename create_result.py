from typing import List, Optional
import random
import logging
from pathlib import Path
from dataclasses import dataclass
import sys

from paths import paths
from logger import get_logger, log_exception


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


def run_create_result() -> ProcessingResult:
    """Запускает обработку файлов."""
    try:
        logger = get_logger('create_result_runner')
        logger.info("Запуск обработки результатов")
        processor = FileProcessor(paths.PARSED_LINKS_FILE, paths.RESULT_FILE)
        result = processor.process()
        if result.success:
            logger.info("Обработка результатов успешно завершена")
        else:
            logger.warning(f"Обработка результатов завершена с ошибкой: {result.message}")
        return result
    except Exception as e:
        logger = get_logger('create_result_runner')
        log_exception(logger, "Непредвиденная ошибка при запуске обработки результатов", e)
        return ProcessingResult(success=False, message=f"Error: {str(e)}", error=e)


if __name__ == "__main__":
    try:
        logger = get_logger('create_result')
        if len(sys.argv) != 3:
            logger.error("Использование: python create_result.py <input_file> <output_file>")
            sys.exit(1)

        input_file = sys.argv[1]
        output_file = sys.argv[2]

        logger.info(f"Начало обработки: вход={input_file}, выход={output_file}")
        processor = FileProcessor(input_file, output_file)
        lines = processor.read_lines()
        cleaned_lines = processor.clean_lines(lines)
        processor.write_lines(cleaned_lines)
        logger.info(f"Обработка завершена: {len(cleaned_lines)}/{len(lines)} записей сохранено")
    except Exception as e:
        log_exception(logger, "Ошибка при выполнении create_result.py", e)
        sys.exit(1)
