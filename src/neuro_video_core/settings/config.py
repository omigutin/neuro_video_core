from dataclasses import dataclass

from ..decoders.decoder_type import DecoderType


@dataclass(slots=True)
class VideoCoreConfig:
    """
        Configuration for NeuroVideoCore.
        Все параметры легковесные, без привязки к файлам.
        Любой слой приложения может формировать этот объект как ему удобно.
    """

    # Какой декодер использовать
    decoder: DecoderType = DecoderType.OPENCV

    # RingBuffer:
    # 0  → буфер выключен
    # >0 → включён, capacity = buffer_size
    buffer_size: int = 0

    # Асинхронное чтение кадров
    async_enabled: bool = False
    # Задержка между чтениями в AsyncFrameReader (секунды)
    poll_delay: float = 0.0

    # Строгий режим ошибок
    strict_mode: bool = True

    # Влияние на HybridDecoder (на будущее)
    force_opencv_seek: bool = False
