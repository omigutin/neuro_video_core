from pathlib import Path
from typing import Optional

from ..decoders.base_decoder import BaseDecoder
from ..decoders import DecoderFactory
from ..settings import VideoCoreConfig
from ..buffer.ring_buffer import RingBuffer
from ..async_reader.async_frame_reader import AsyncFrameReader
from ..exceptions import VideoOpenError


class VideoCore:
    """
        Центральное видео-ядро.

        Выполняет:
        * создание и управление декодером;
        * чтение кадров (sync/async);
        * переходы по кадрам;
        * поддержка буфера;
        * получение метаданных.

        Источником истины о положении в видео является сам декодер.
    """

    def __init__(self, source: str | Path | BaseDecoder, config: Optional[VideoCoreConfig] = None):
        self._config = config or VideoCoreConfig()

        # Создаём или принимаем декодер
        if isinstance(source, BaseDecoder):
            self._decoder = source
        else:
            factory = DecoderFactory(self._config)
            self._decoder = factory.create(source)

        # Буфер
        self._buffer: Optional[RingBuffer] = (
            RingBuffer(self._config.buffer_size)
            if self._config.buffer_size > 0
            else None
        )

        # Async-reader
        self._async_reader: Optional[AsyncFrameReader] = (
            AsyncFrameReader(self._decoder)
            if self._config.async_enabled
            else None
        )

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def open(self) -> None:
        """ Открывает видео-декодер. """
        if not self._decoder.open():
            raise VideoOpenError(f"VideoCore: cannot open decoder for source: {self._decoder}")

    def close(self) -> None:
        """ Закрывает декодер и останавливает async-поток. """
        if self._async_reader:
            self._async_reader.stop()
        self._decoder.close()

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def get_metadata(self) -> dict:
        """ Возвращает FPS и количество кадров из декодера. """
        return {
            "fps": self._decoder.fps,
            "total_frames": self._decoder.total_frames,
        }

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def go_to_frame(self, frame_index: int) -> bool:
        """
            Переходит на указанный кадр.
            Возвращает:
            True  — если переход успешен,
            False — если seek не выполнен.
        """
        return self._decoder.seek(frame_index)

    def get_decoder_frame_id(self) -> int:
        """ Возвращает реальную позицию декодера. """
        return self._decoder.cur_frame_id()

    # ---------------------------------------------------------
    # Reading
    # ---------------------------------------------------------

    def get_frame(self):
        """ Читает один кадр из декодера. При успехе добавляет его в буфер. """
        frame = self._decoder.read()
        if frame is not None and self._buffer:
            self._buffer.push(frame)
        return frame

    # ---------------------------------------------------------
    # Buffer
    # ---------------------------------------------------------

    def get_last_buffered(self):
        return self._buffer.last() if self._buffer else None

    def get_buffer_frame(self, frame_index: int):
        return self._buffer.get(frame_index) if self._buffer else None

    # ---------------------------------------------------------
    # Async
    # ---------------------------------------------------------

    def start_async(self) -> None:
        if self._async_reader:
            self._async_reader.start()

    def stop_async(self) -> None:
        if self._async_reader:
            self._async_reader.stop()

    def get_last_async_frame(self):
        return self._async_reader.get_last() if self._async_reader else None
