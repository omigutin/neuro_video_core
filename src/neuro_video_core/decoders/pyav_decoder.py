import warnings
from pathlib import Path
from typing import Optional

import av
from numpy import ndarray

from .base_decoder import BaseDecoder
from ..settings import VideoCoreConfig
from ..exceptions import VideoOpenError


class PyAVDecoder(BaseDecoder):
    """
        Декодер на базе PyAV (FFmpeg).

        Назначение:
        -----------
        Предоставляет максимально корректную и детерминированную работу с видео:
        * честный FPS;
        * точное количество кадров (если контейнер поддерживает);
        * надёжный seek по временной шкале;
        * корректные PTS/DTS.

        Плюсы:
        ------
        + Корректная временная шкала (time_base).
        + Точный seek — лучше, чем в OpenCV.
        + Поддержка редких форматов и кодеков.

        Минусы:
        -------
        - Сложнее установка (PyAV зависит от FFmpeg).
        - В среднем медленнее OpenCV при последовательном чтении.
        - Позволяет хорошо работать с метаданными, но не всегда быстрее.

        Использование:
        --------------
        Идеален для оффлайн-задач, анализа и точной навигации.
        В HybridDecoder применяется как «источник правды»:
        * PyAV делает seek;
        * OpenCV возвращает кадр.

        Ограничения:
        -------------
        * Работает только на CPU.
        * Не делает точный seek на каждый кадр — FFmpeg всегда ищет ближайший keyframe.
    """

    def __init__(self, path: str | Path, config: VideoCoreConfig):
        """
            Инициализация декодера.
            :param path: путь к видеофайлу
            :param config: объект конфигурации VideoCore
        """
        super().__init__(path, config)

        self._container: Optional[av.container.InputContainer] = None
        self._stream: Optional[av.video.stream.VideoStream] = None
        self._frame_iter = None

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------
    def _init_metadata(self) -> None:
        """ Инициализация fps и total_frames для PyAV. """
        # FPS
        if self._stream.average_rate:
            self._fps = float(self._stream.average_rate)
        else:
            self._fps = None

        # Total frames
        try:
            frames = self._stream.frames
            if frames is not None and frames > 0:
                self._total_frames = frames
            else:
                self._total_frames = None
        except Exception:
            self._total_frames = None

    def open(self) -> bool:
        """
            Открывает контейнер PyAV и инициализирует видеопоток.
            ---------
            1. Открыть контейнер.
            2. Найти видеопоток.
            3. Инициализировать метаданные (fps, total_frames).
            4. Создать итератор кадров.

            Возвращает:
            True  — если контейнер успешно открыт.
            False — если возникла ошибка.
        """
        try:
            self._container = av.open(str(self._path))
        except Exception as e:
            warnings.warn(f"PyAV: failed to open container: {e}")
            return False

        # Получаем первый видеопоток
        try:
            self._stream = self._container.streams.video[0]
        except Exception as e:
            warnings.warn(f"PyAV: no video stream available: {e}")
            return False

        # Инициализация fps и total_frames
        self._init_metadata()

        # Создаем итератор кадров
        self._reset_frame_iterator()

        return True

    def close(self) -> None:
        """ Закрывает контейнер и сбрасывает состояние. """
        if self._container:
            self._container.close()
        self._container = None
        self._stream = None
        self._frame_iter = None
        self._current_frame_id = 0

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def get_total_frames(self) -> int:
        """ Возвращает количество кадров, если контейнер предоставляет эту информацию. """
        if not self._stream:
            return 0

        # Может быть 0 или None — тогда считаем неизвестным.
        frames = self._stream.frames
        return int(frames) if frames and frames > 0 else 0

    def get_fps(self) -> float:
        """ Возвращает честный FPS. """
        if not self._stream:
            return 0.0

        rate = self._stream.average_rate
        return float(rate) if rate else 0.0

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------

    def _reset_frame_iterator(self) -> None:
        """ Создаёт новый итератор кадров. """
        if self._container and self._stream:
            self._frame_iter = self._container.decode(self._stream)

    def _frame_to_pts(self, frame_index: int) -> Optional[int]:
        """
            Переводит индекс кадра в PTS.

            Алгоритм:
            ---------
            seconds = frame_index / fps
            pts = seconds / time_base

            Возвращает pts или None, если вычислить невозможно.
        """
        if not self._fps or self._fps <= 0:
            return None

        try:
            seconds = frame_index / self._fps
            pts = int(seconds / float(self._stream.time_base))
            return pts
        except Exception:
            return None

    def seek(self, frame_index: int) -> bool:
        """
            Выполняет безопасный seek для PyAV.
            Метод:
            ------
            * никого не исключений;
            * возвращает True/False;
            * не изменяет текущий кадр при неуспехе.
            Алгоритм:
            ---------
            1. Клампим индекс.
            2. Проверяем контейнер и поток.
            3. Получаем PTS.
            4. Пытаемся выполнить seek.
            5. При успехе — обновляем current_frame_id.
        """

        # Клампинг
        frame_index = self.clamp_frame_index(frame_index)

        # Проверка контейнера
        if not self._container or not self._stream:
            warnings.warn("PyAV: seek failed — container or stream is not initialized.")
            return False

        # PTS
        pts = self._frame_to_pts(frame_index)
        if pts is None:
            warnings.warn("PyAV: seek failed — could not compute pts value.")
            return False

        # Выполнение seek
        try:
            # Seek только по ключевым кадрам
            self._container.seek(pts, any_frame=False, backward=True)
        except Exception as e:
            warnings.warn(f"PyAV: seek failed — unable to seek: {e}")
            return False

        # Успех → обновление состояния
        self._reset_frame_iterator()
        self._current_frame_id = frame_index

        return True

    def cur_frame_id(self) -> int:
        """ Текущий индекс кадра (поддерживается вручную). """
        return self._current_frame_id

    # ---------------------------------------------------------
    # Reading
    # ---------------------------------------------------------

    def read(self) -> Optional[ndarray]:
        """
            Читает следующий кадр из потока.
            :return: ndarray (BGR) или None, если конец видео
        """
        if not self._frame_iter:
            return None

        try:
            frame = next(self._frame_iter)
        except StopIteration:
            return None

        self._current_frame_id += 1
        return frame.to_ndarray(format="bgr24")
