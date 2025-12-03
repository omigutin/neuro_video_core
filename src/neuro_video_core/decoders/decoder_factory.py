from pathlib import Path
from typing import Any

from ..settings import VideoCoreConfig
from .decoder_type import DecoderType
from .opencv_decoder import OpenCVDecoder
from .pyav_decoder import PyAVDecoder
from .hybrid_decoder import HybridDecoder


class DecoderFactory:
    """
        Создаёт экземпляры декодеров по типу DECODER, указанному в конфиге.
    """

    _MAP = {
        DecoderType.OPENCV: OpenCVDecoder,
        DecoderType.PYAV: PyAVDecoder,
        DecoderType.HYBRID: HybridDecoder,
    }

    def __init__(self, config: VideoCoreConfig):
        self._config: VideoCoreConfig = config

    def create(self, path: str | Path):
        """ Создать экземпляр декодера."""

        # Нормализуем тип декодера из конфига
        dec_type = self._normalize_decoder_type(self._config.decoder)

        # AUTO → определить по path
        if dec_type == DecoderType.AUTO:
            dec_type = self._auto_select_decoder_type(path)

        # Проверка поддержки декодера
        if not dec_type.is_supported:
            raise RuntimeError(f"Decoder '{dec_type.value}' is not supported in current build.")

        # Берём ссылку на класс декодера
        decoder_cls = self._MAP.get(dec_type)
        if decoder_cls is None:
            available = ", ".join(d.value for d in self._MAP)
            raise ValueError(f"Decoder '{dec_type.value}' is not registered. Available: {available}")

        return decoder_cls(path=path, config=self._config)

    @staticmethod
    def _normalize_decoder_type(dec_type: Any) -> DecoderType:
        if isinstance(dec_type, DecoderType):
            return dec_type
        if isinstance(dec_type, str):
            dec_type = dec_type.lower()
            return DecoderType(dec_type)
        raise TypeError("decoder must be DecoderType or str")

    @staticmethod
    def _auto_select_decoder_type(path: str | Path) -> DecoderType:
        """ Логика выбора оптимального декодера по типу источника. """
        s = str(path).lower().strip()
        ext = Path(s).suffix.lower()

        if s.startswith(("rtsp://", "http://", "https://")):
            return DecoderType.PYAV

        if s.isdigit() or s.startswith("camera"):
            return DecoderType.OPENCV

        if ext in {".mkv", ".mov", ".ts"}:
            return DecoderType.PYAV

        if ext in {".mp4", ".avi"}:
            return DecoderType.HYBRID

        return DecoderType.HYBRID
