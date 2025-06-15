import requests
import zipfile
import csv
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from time import sleep

from src.core.logger import get_logger, log_exception
from src.core.paths import paths
from src.core.config import REQUEST_TIMEOUT


class BukvarixCollector:
    """Класс для скачивания и обработки топ-запросов с сайта Букварикс."""
    
    def __init__(self, max_keywords: int = 10000):
        """
        Инициализирует коллектор данных Букварикс.
        
        Args:
            max_keywords: Максимальное количество ключевых слов для сохранения
        """
        self.max_keywords = max_keywords
        self.logger = get_logger('bukvarix_collector')
        self.base_url = "https://www.bukvarix.com/top-keywords/"
        self.session = requests.Session()
        
        # Настройка заголовков для имитации браузера
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def collect_top_keywords(self) -> bool:
        """
        Основной метод для сбора топ-запросов.
        
        Returns:
            True в случае успеха, False при ошибке
        """
        try:
            self.logger.info("Начинаю сбор топ-запросов с Букварикс")
            
            # Создаем необходимые директории
            self._create_directories()
            
            # Скачиваем архив
            archive_path = self._download_archive()
            if not archive_path:
                return False
                
            # Извлекаем CSV файл из архива
            csv_path = self._extract_csv_from_archive(archive_path)
            if not csv_path:
                return False
                
            # Обрабатываем CSV и сохраняем ключевые слова
            success = self._process_csv_file(csv_path)
            
            # Очищаем временные файлы
            self._cleanup_temp_files()
            
            if success:
                self.logger.info(f"Успешно сохранено {self.max_keywords} ключевых слов в {paths.KEYWORDS_TOP_FILE}")
                return True
            else:
                return False
                
        except Exception as e:
            log_exception(self.logger, "Ошибка в основном процессе сбора данных", e)
            self._cleanup_temp_files()
            return False

    def _create_directories(self) -> None:
        """Создает необходимые директории."""
        try:
            paths.PROJECT_DIR_TOP.mkdir(exist_ok=True)
            paths.BUKVARIX_ARCHIVE_DIR.mkdir(exist_ok=True)
            paths.RESULTS_DIR.mkdir(exist_ok=True)
            self.logger.info("Директории созданы")
        except Exception as e:
            log_exception(self.logger, "Ошибка при создании директорий", e)
            raise

    def _download_archive(self) -> Optional[Path]:
        """
        Скачивает архив с сайта Букварикс.
        
        Returns:
            Путь к скачанному архиву или None при ошибке
        """
        try:
            self.logger.info("Начинаю скачивание архива с Букварикс")
            
            # Получаем ссылку на скачивание
            download_url = self._get_download_url()
            if not download_url:
                return None
                
            # Скачиваем файл
            response = self.session.get(download_url, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Определяем имя файла
            archive_name = self._get_filename_from_response(response)
            archive_path = paths.BUKVARIX_ARCHIVE_DIR / archive_name
            
            # Сохраняем файл
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            self.logger.info(f"Архив успешно скачан: {archive_path}")
            return archive_path
            
        except requests.RequestException as e:
            log_exception(self.logger, "Ошибка при скачивании архива", e)
            return None
        except Exception as e:
            log_exception(self.logger, "Неожиданная ошибка при скачивании", e)
            return None

    def _get_download_url(self) -> Optional[str]:
        """
        Получает URL для скачивания архива.
        
        Returns:
            URL для скачивания или None при ошибке
        """
        try:
            # Используем прямую ссылку на архив
            download_url = "https://www.bukvarix.com/TopKeywords.zip"
            
            self.logger.info(f"Используем URL для скачивания: {download_url}")
            return download_url
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при получении URL скачивания", e)
            return None

    def _get_filename_from_response(self, response: requests.Response) -> str:
        """
        Извлекает имя файла из ответа HTTP.
        
        Args:
            response: Ответ HTTP
            
        Returns:
            Имя файла
        """
        try:
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                import re
                filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                if filename_match:
                    return filename_match.group(1)
                    
            # Если не удалось извлечь из заголовков, используем URL
            url_path = urlparse(response.url).path
            if url_path.endswith('.zip'):
                return os.path.basename(url_path)
                
            # По умолчанию
            return "bukvarix_keywords.zip"
            
        except Exception:
            return "bukvarix_keywords.zip"

    def _extract_csv_from_archive(self, archive_path: Path) -> Optional[Path]:
        """
        Извлекает CSV файл из архива.
        
        Args:
            archive_path: Путь к архиву
            
        Returns:
            Путь к извлеченному CSV файлу или None при ошибке
        """
        try:
            self.logger.info("Извлекаю CSV файл из архива")
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Ищем CSV файл в архиве
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                
                if not csv_files:
                    self.logger.error("CSV файл не найден в архиве")
                    return None
                
                # Берем первый найденный CSV файл
                csv_filename = csv_files[0]
                
                # Извлекаем файл
                zip_ref.extract(csv_filename, paths.BUKVARIX_ARCHIVE_DIR)
                csv_path = paths.BUKVARIX_ARCHIVE_DIR / csv_filename
                
                self.logger.info(f"CSV файл извлечен: {csv_path}")
                return csv_path
                
        except zipfile.BadZipFile:
            self.logger.error("Поврежденный архив")
            return None
        except Exception as e:
            log_exception(self.logger, "Ошибка при извлечении CSV файла", e)
            return None

    def _process_csv_file(self, csv_path: Path) -> bool:
        """
        Обрабатывает CSV файл и сохраняет ключевые слова.
        
        Args:
            csv_path: Путь к CSV файлу
            
        Returns:
            True в случае успеха, False при ошибке
        """
        try:
            self.logger.info("Обрабатываю CSV файл")
            
            keywords = []
            
            # Читаем CSV файл с различными кодировками
            encodings = ['utf-8', 'cp1251', 'utf-8-sig']
            
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding, newline='') as csvfile:
                        # Пробуем различные разделители
                        sample = csvfile.read(1024)
                        csvfile.seek(0)
                        
                        delimiter = ';' if ';' in sample else ','
                        
                        reader = csv.reader(csvfile, delimiter=delimiter)
                        
                        # Пропускаем заголовок
                        next(reader, None)
                        
                        for row_num, row in enumerate(reader, 1):
                            if row_num > self.max_keywords:
                                break
                                
                            # Берем третий столбец (индекс 2)
                            if len(row) > 2 and row[2].strip():
                                keywords.append(row[2].strip())
                                
                    break  # Если успешно прочитали, выходим из цикла кодировок
                    
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    if encoding == encodings[-1]:  # Последняя попытка
                        raise e
                    continue
            
            if not keywords:
                self.logger.error("Не удалось извлечь ключевые слова из CSV файла")
                return False
                
            # Сохраняем ключевые слова в файл
            self._save_keywords_to_file(keywords)
            
            self.logger.info(f"Обработано {len(keywords)} ключевых слов")
            return True
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при обработке CSV файла", e)
            return False

    def _save_keywords_to_file(self, keywords: List[str]) -> None:
        """
        Сохраняет ключевые слова в файл.
        
        Args:
            keywords: Список ключевых слов
        """
        try:
            with open(paths.KEYWORDS_TOP_FILE, 'w', encoding='utf-8') as f:
                for keyword in keywords:
                    f.write(keyword + '\n')
                    
            self.logger.info(f"Ключевые слова сохранены в {paths.KEYWORDS_TOP_FILE}")
            
        except Exception as e:
            log_exception(self.logger, "Ошибка при сохранении ключевых слов", e)
            raise

    def _cleanup_temp_files(self) -> None:
        """Очищает временные файлы."""
        try:
            # Не удаляем файлы из project_folder_top, оставляем их для дальнейшего использования
            self.logger.info("Временные файлы сохранены в project_folder_top")
        except Exception as e:
            log_exception(self.logger, "Ошибка при обработке временных файлов", e)


def run_collect_keywords_top():
    """Основная функция для запуска сбора данных."""
    collector = BukvarixCollector(max_keywords=10000)
    success = collector.collect_top_keywords()
    
    if success:
        print("Сбор топ-запросов завершен успешно!")
    else:
        print("Произошла ошибка при сборе данных")
        

if __name__ == "__main__":
    main() 