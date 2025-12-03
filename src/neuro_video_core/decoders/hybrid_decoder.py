from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

from .base_decoder import BaseDecoder
from .decoder_type import DecoderType
from .opencv_decoder import OpenCVDecoder
from .pyav_decoder import PyAVDecoder
from ..settings import VideoCoreConfig


class HybridDecoder(BaseDecoder):
    """
        Гибридный декодер, объединяющий сильные стороны PyAV и OpenCV.

        Назначение:
        -----------
        Обеспечить:
        * корректные метаданные (FPS, total_frames, временная шкала) — через PyAV;
        * быстрое чтение кадров — через OpenCV;
        * максимально точный seek — PyAV управляет временной шкалой.

        Сильные стороны:
        ----------------
        + PyAV → честный FPS, корректная time_base, надёжные метаданные.
        + OpenCV → быстрый вывод кадров, низкие накладные расходы.
        + Ideal для плеера, продакшн-инструментов и анализа.

        Ограничения:
        ------------
        * Seek остаётся неточным, если OpenCV не может позиционироваться точно на кадр.

        Рекомендуемое использование:
        ----------------------------
        * оффлайн просмотр и точные переходы;
        * анализ видео, где важны FPS и достаточно «почти точного» seek.
    """

    def __init__(self, path: str | Path, config: VideoCoreConfig):
        """
            Инициализация гибридного декодера.
            :param path: путь к видеофайлу
            :param config: объект конфигурации VideoCore
        """
        super().__init__(path, config)

        self._opencv = OpenCVDecoder(self._path, config)
        self._pyav = PyAVDecoder(self._path, config)

        # Декодер, который сделал последний прыжок
        self._last_seek_by: DecoderType | None = None

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def open(self) -> bool:
        """
            Открывает оба декодера.
            Логика:
            -------
            1. PyAV → источник истины по метаданным.
            2. OpenCV → источник кадров.
            3. Если оба не открылись — возвращаем False.
        """
        ok_pyav = self._pyav.open()
        ok_opencv = self._opencv.open()

        if not ok_pyav and not ok_opencv:
            warnings.warn(f"HybridDecoder: unable to open both decoders: {self._path}")
            return False

        # Метаданные берём у PyAV, если он доступен
        if ok_pyav:
            self._fps = self._pyav.fps
            self._total_frames = self._pyav.total_frames
        else:
            self._fps = self._opencv.fps
            self._total_frames = self._opencv.total_frames

        return True

    def close(self) -> None:
        """ Закрывает оба декодера (любым способом). """
        try:
            self._opencv.close()
        finally:
            self._pyav.close()

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def get_fps(self) -> float:
        """
            Возвращает максимально корректный FPS.
            Приоритет:
            1) PyAV
            2) OpenCV (fallback)
        """
        if self._fps is not None:
            return self._fps

        fps = self._pyav.get_fps()
        if not fps or fps <= 0:
            fps = self._opencv.get_fps()

        self._fps = float(fps) if fps else 0.0
        return self._fps

    def get_total_frames(self) -> int:
        """
            Возвращает оценку количества кадров.
            Приоритет:
            1) PyAV — честная мета
            2) OpenCV — fallback
        """
        if self._total_frames is not None:
            return self._total_frames

        total = self._pyav.get_total_frames()
        if not total or total <= 0:
            total = self._opencv.get_total_frames()

        self._total_frames = int(total) if total else 0
        return self._total_frames

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def _frame_to_seconds(self, frame_index: int) -> float:
        """ Перевод индекса кадра в секунды. """
        fps = self.get_fps()
        if fps <= 0:
            return 0.0
        return max(0.0, frame_index / fps)

    def seek(self, frame_index: int) -> bool:
        """
            Выполняет безопасный seek.

            Правила:
            --------
            * никогда не бросает исключений;
            * если PyAV может — он главный;
            * OpenCV используется для синхронизации;
            * если оба не смогли — остаёмся на месте.
        """

        frame_index = self.clamp_frame_index(frame_index)

        pyav_ok = False
        opencv_ok = False

        # Пытаемся PyAV (точно, надёжно)
        pyav_ok = self._pyav.seek(frame_index)
        if pyav_ok:
            # Синхронизируем OpenCV по возможности
            self._opencv.seek(frame_index)
            self._last_seek_by = DecoderType.PYAV
            return True

        # PyAV не смог → пробуем OpenCV
        opencv_ok = self._opencv.seek(frame_index)
        if opencv_ok:
            self._last_seek_by = DecoderType.OPENCV
            return True

        # Оба декодера не смогли
        warnings.warn(f"HybridDecoder: seek failed at frame {frame_index}")
        return False

    def cur_frame_id(self) -> int:
        """
            Возвращает текущий кадр в зависимости от того,
            кто выполнял последний seek.
        """

        # Если был seek PyAV → он источник правды
        if self._last_seek_by is DecoderType.PYAV:
            return self._pyav.cur_frame_id()

        # Если был seek OpenCV → опираемся на OpenCVDecoder._current_frame_id
        if self._last_seek_by is DecoderType.OPENCV:
            return self._opencv.cur_frame_id()

        # Если seek не было:
        # Пробуем OpenCV (быстрый)
        pos = self._opencv.cur_frame_id()
        if pos >= 0:
            return pos

        # fallback PyAV
        return self._pyav.cur_frame_id()

    # ---------------------------------------------------------
    # Reading
    # ---------------------------------------------------------

    def read(self):
        """
            Читает кадр из OpenCVDecoder (быстро).
            PyAV не используется для чтения кадров в MVP:
            он отвечает только за “timeline”.
        """
        return self._opencv.read()
