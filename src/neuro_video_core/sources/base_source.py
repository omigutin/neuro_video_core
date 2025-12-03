from abc import ABC, abstractmethod


class BaseSource(ABC):
    """
        Базовый интерфейс для любых источников видео:
        - файлы
        - rtsp-потоки
        - http(s) видео
        - камеры
        - raw кадры
        - mmap
        и т.д.
        (Пока не используем — задел на будущее.)
    """

    @abstractmethod
    def get_uri(self) -> str:
        """Возвращает нормализованный URI/путь к источнику."""
        pass
