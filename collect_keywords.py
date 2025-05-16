import os
import requests
import time
import csv
import logging
from io import StringIO
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from paths import paths
from dotenv import load_dotenv
from logger import get_logger, log_exception

@dataclass
class ApiResponse:
    """Результат запроса к API."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    file_path: Optional[Path] = None

class KeywordCollector:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('BUKVARIX_API_KEY')
        self.logger = get_logger('keyword_collector')
        if not self.api_key:
            raise ValueError("API ключ не найден в .env файле")

    def fetch_data(self, domain: str) -> ApiResponse:
        """Получает данные с API и сохраняет в файл."""
        url = f"http://api.bukvarix.com/v1/site/?q={domain}&api_key={self.api_key}&num=10000&format=csv"
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return ApiResponse(
                    success=False,
                    error=f"Ошибка при запросе для {domain}: {response.status_code}"
                )

            content = response.content.decode('utf-8')
            if not content.strip():
                return ApiResponse(
                    success=False,
                    error=f"Ответ пустой для домена {domain}"
                )

            processed_file_path = paths.PROJECT_DIR / f"{domain}.csv"
            self._save_csv_content(content, processed_file_path, domain)
            
            return ApiResponse(
                success=True,
                content=content,
                file_path=processed_file_path
            )
        except Exception as e:
            log_exception(self.logger, f"Ошибка при получении данных для {domain}", e)
            return ApiResponse(success=False, error=str(e))

    def _save_csv_content(self, content: str, file_path: Path, domain: str) -> None:
        """Сохраняет CSV контент в файл."""
        reader = csv.reader(StringIO(content), delimiter=';')
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as outfile:
            writer = csv.writer(outfile, delimiter=';')
            for row in reader:
                row.append(domain)
                writer.writerow(row)

    def process_domains(self) -> None:
        """Обрабатывает список доменов."""
        try:
            with open(paths.DOMAINS_FILE, 'r', encoding='utf-8') as file:
                domains = file.read().splitlines()

            for domain in domains:
                result = self.fetch_data(domain)
                if result.success:
                    self.logger.info(f"Успешно обработан домен: {domain}")
                else:
                    self.logger.error(f"Ошибка обработки домена {domain}: {result.error}")
                time.sleep(10)

            self.logger.info(f"Все CSV файлы собраны в {paths.PROJECT_DIR}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при обработке доменов", e)
            raise

    def merge_files(self) -> None:
        """Объединяет все CSV файлы в один."""
        try:
            csv_files = [f for f in paths.PROJECT_DIR.iterdir() if f.suffix == '.csv']
            output_file = paths.RESULTS_DIR / 'result_csv.csv'

            with open(output_file, 'w', newline='', encoding='utf-8-sig') as outfile:
                writer = csv.writer(outfile, delimiter=';')
                self._process_csv_files(csv_files, writer)

            self.logger.info(f"Все файлы объединены в {output_file}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при объединении файлов", e)
            raise

    def _process_csv_files(self, csv_files: List[Path], writer: csv.writer) -> None:
        """Обрабатывает CSV файлы и записывает в общий файл."""
        header_written = False
        for csv_file in csv_files:
            with open(csv_file, 'r', encoding='utf-8') as infile:
                reader = csv.reader(infile, delimiter=';')
                if not header_written:
                    header = next(reader)
                    writer.writerow([header[0], header[5], header[7]])
                    header_written = True
                else:
                    next(reader)
                
                for row in reader:
                    writer.writerow([row[0], row[5], row[7]])

    def sort_and_save_keywords(self, limit: int = 50000) -> None:
        """Сортирует и сохраняет ключевые слова."""
        try:
            input_file = paths.RESULTS_DIR / 'result_csv.csv'
            with open(input_file, 'r', encoding='utf-8') as infile:
                reader = csv.reader(infile, delimiter=';')
                next(reader)  # Пропускаем заголовок
                sorted_rows = sorted(reader, key=lambda row: int(row[1]), reverse=True)

            with open(paths.KEYWORDS_FILE, 'w', encoding='utf-8') as outfile:
                for row in sorted_rows[:limit]:
                    outfile.write(f"{row[2]} {row[0]}\n")

            self.logger.info(f"Ключевые слова сохранены в {paths.KEYWORDS_FILE}")
        except Exception as e:
            log_exception(self.logger, "Ошибка при сортировке и сохранении ключевых слов", e)
            raise

def run_collect_keywords() -> None:
    """Запускает процесс сбора ключевых слов."""
    logger = get_logger('collect_keywords')
    try:
        logger.info("Начало сбора ключевых слов")
        collector = KeywordCollector()
        collector.process_domains()
        collector.merge_files()
        collector.sort_and_save_keywords()
        logger.info("Сбор ключевых слов успешно завершен")
    except Exception as e:
        log_exception(logger, "Ошибка при сборе ключевых слов", e)
        raise

if __name__ == "__main__":
    # Используем нашу систему логирования
    logger = get_logger('collect_keywords_main')
    logger.info("Запуск сбора ключевых слов")
    
    try:
        run_collect_keywords()
    except Exception as e:
        log_exception(logger, "Критическая ошибка при сборе ключевых слов", e)
    finally:
        logger.info("Завершение работы скрипта")