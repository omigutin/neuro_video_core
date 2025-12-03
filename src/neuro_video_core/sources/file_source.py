from pathlib import Path
from typing import Union

from .base_source import BaseSource


class FileSource(BaseSource):
    """
        Источник локального видео-файла.
        Выполняет только:
        * нормализацию пути;
        * проверку существования;
        * возврат URI.
        Декодированием занимается Decoder.
    """

    def __init__(self, path: Union[str, Path]):
        """
            :param path: путь к видео-файлу
        """
        self._path: Path = Path(path).expanduser().resolve()

        if not self._path.exists():
            raise FileNotFoundError(f"Video file does not exist: {self._path}")

    def get_uri(self) -> str:
        """ Возвращает абсолютный путь к файлу. """
        return str(self._path)
