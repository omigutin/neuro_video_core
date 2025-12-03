from pathlib import Path
from typing import Optional

import cv2
from numpy import ndarray

from .base_decoder import BaseDecoder
from ..settings import VideoCoreConfig
import warnings


class OpenCVDecoder(BaseDecoder):
    """
        Декодер на базе OpenCV (cv2.VideoCapture).

        Назначение:
        -----------
        Лёгкий и быстрый декодер для:
        * локальных видеофайлов,
        * RTSP,
        * камер,
        * быстрых предпросмотров.

        Основные особенности:
        ----------------------
        * Не гарантирует точный seek.
        * FPS и total_frames могут быть неточными.
        * Работает только на CPU.
        * Хорош для линейного чтения кадров.

        В HybridDecoder:
        -----------------
        Используется как источник быстрой выдачи кадров
        при наличии точного позиционирования через PyAV.
    """

    def __init__(self, path: str | Path, config: VideoCoreConfig):
        """ Инициализация декодера. """
        super().__init__(path, config)
        self._cap: Optional[cv2.VideoCapture] = None

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def _init_metadata(self) -> None:
        """
            Инициализация метаданных для OpenCV:
            * FPS
            * total_frames

            Логика:
            -------
            FPS и total_frames могут быть неточными для некоторых контейнеров.
        """
        fps = self.get_fps()
        self._fps = fps if fps > 0 else None

        total = self.get_total_frames()
        self._total_frames = total if total > 0 else None

    def open(self) -> bool:
        """
            Открывает видеопоток.

            Алгоритм:
            ---------
            1. Пытаемся открыть cv2.VideoCapture.
            2. Если не удалось — возвращаем False.
            3. Инициализируем метаданные fps и total_frames.
            4. Возвращаем True.

            :return: True если источник открыт, иначе False.
        """
        self._cap = cv2.VideoCapture(str(self._path))

        if not self._cap.isOpened():
            warnings.warn(f"OpenCV: cannot open video: {self._path}")
            self._cap = None
            return False

        self._init_metadata()
        return True

    def close(self) -> None:
        """ Закрывает видеопоток и освобождает ресурсы. """
        if self._cap:
            self._cap.release()

        self._cap = None
        self._current_frame_id = 0

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def get_fps(self) -> float:
        """
            Возвращает FPS видео. Может быть неточным.
            :return: fps или 0.0, если определить невозможно.
        """
        if not self._cap:
            return 0.0

        fps = self._cap.get(cv2.CAP_PROP_FPS)
        return float(fps) if fps and fps > 0 else 0.0

    def get_total_frames(self) -> int:
        """
            Возвращает количество кадров (может быть неточным).
            :return: число кадров или 0, если определить невозможно.
        """
        if not self._cap:
            return 0

        total = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return total if total > 0 else 0

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def seek(self, frame_index: int) -> bool:
        """
            Перемещает положение чтения на указанный кадр.
            Метод безопасный:
            * не бросает исключений,
            * возвращает True если смещение удалось.

            Seek в OpenCV неточный:
            ------------------------
            * перемещение производится по ключевым кадрам,
            * возможны смещения на ±2–10 кадров.
        """

        if not self._cap:
            warnings.warn("OpenCV: seek failed — decoder not opened.")
            return False

        # Клампим индекс
        frame_index = self.clamp_frame_index(frame_index)

        # Пытаемся перейти
        try:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            return pos == frame_index
        except Exception as e:
            warnings.warn(f"OpenCV: seek failed — {e}")
            return False

    def cur_frame_id(self) -> int:
        """
            Возвращает текущий индекс кадра.

            Логика:
            -------
            1. Пытаемся получить позицию через OpenCV.
            2. Если значение валидно — синхронизируем с _current_frame_id.
            3. Если OpenCV вернул некорректное значение (0 или <0),
               то возвращаем _current_frame_id, сохранив предыдущее состояние.

            Примечание:
            -----------
            OpenCV иногда может вернуть 0 даже в середине видео —
            поэтому _current_frame_id служит стабилизатором.
        """
        if not self._cap:
            return self._current_frame_id

        try:
            pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        except Exception:
            # В случае сбоя возвращаем последний валидный кадр
            return self._current_frame_id

        # Коррекция некорректных значений
        if pos < 0:
            pos = 0

        # Обновляем счётчик в BaseDecoder
        self._current_frame_id = pos
        return pos

    # ---------------------------------------------------------
    # Reading
    # ---------------------------------------------------------

    def read(self) -> Optional[ndarray]:
        """
            Читает один кадр из видео.

            Логика:
            -------
            1. Пытаемся прочитать кадр.
            2. Если не удалось — возвращаем None.
            3. После успешного чтения пытаемся получить позицию из OpenCV.
            4. Если позиция валидна — синхронизируем _current_frame_id.
            5. Если позиция неверна (0 или отрицательная), то:
                * считаем, что кадр инкрементирован,
                * увеличиваем _current_frame_id вручную.
            6. Возвращаем кадр.

            Причины такой логики:
            ----------------------
            POS_FRAMES в OpenCV иногда отдаёт некорректные значения, особенно при:
            * RTSP,
            * USB-камерах,
            * H.264 контейнерах,
            * после seek().
            Поэтому _current_frame_id — стабильный счётчик,
            который используется во всей VideoCore-системе.
        """
        if not self._cap:
            return None

        success, frame = self._cap.read()
        if not success:
            return None

        # --- Попытка получить позицию ---
        pos = None
        try:
            pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        except Exception:
            pos = None

        # --- Проверяем корректность позиции ---
        if pos is not None and pos >= 0:
            # синхронизация с OpenCV-счётчиком
            self._current_frame_id = pos
        else:
            # fallback: OpenCV не дал позицию, но кадр был прочитан
            self._current_frame_id += 1

        return frame

