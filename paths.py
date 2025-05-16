from pathlib import Path
from typing import NoReturn


class PathManager:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.PROJECT_DIR = self.BASE_DIR / "project_folder"
        self.RESULTS_DIR = self.BASE_DIR / "results_folder"
        self.DOMAINS_FILE = self.RESULTS_DIR / "domains.txt"
        self.KEYWORDS_FILE = self.RESULTS_DIR / 'keywords.txt'
        self.PARSED_LINKS_FILE = self.RESULTS_DIR / "parsed_links.txt"
        self.RESULT_FILE = self.BASE_DIR / "result.txt"

    def create_dirs(self) -> None:
        """Создает необходимые директории."""
        self.PROJECT_DIR.mkdir(exist_ok=True)
        self.RESULTS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

    def delete_folder(self, folder_path: Path) -> None:
        """Рекурсивно удаляет директорию и все её содержимое."""
        if folder_path.exists():
            for item in folder_path.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    self.delete_folder(item)
            folder_path.rmdir()

    def cleanup(self) -> None:
        """Очищает все рабочие директории и файлы."""
        self.delete_folder(self.PROJECT_DIR)
        self.delete_folder(self.RESULTS_DIR)
        if self.RESULT_FILE.is_file():
            self.RESULT_FILE.unlink()
        self.create_dirs()


# Создаем глобальный экземпляр для удобного доступа
paths = PathManager()

if __name__ == "__main__":
    paths.cleanup()
