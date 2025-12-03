import cv2
from pathlib import Path
from typing import Optional

from src.neuro_video_core.core.video_core import VideoCore
from src.neuro_video_core.settings import VideoCoreConfig
from src.neuro_video_core.decoders.decoder_type import DecoderType

# Новый импорт
from tools.timer import TimerManager

# Глобальный таймер для всех тестов
TM = TimerManager()


# ============================================================
#                    ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
# ============================================================

def _print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _show_frame(window: str, frame, delay_ms: int = 1):
    """Удобный показ кадра в отдельном окне."""
    if frame is None:
        return
    cv2.imshow(window, frame)
    cv2.waitKey(delay_ms)


def _print_seek_info(requested_frame: int, decoder_frame: int):
    print(f"Requested: {requested_frame:6d} | Decoder:  {decoder_frame:6d}")


# ============================================================
#                   ФУНКЦИИ ТЕСТОВ (с таймерами)
# ============================================================

def test_sync_read(core: VideoCore, window: str, max_frames: int, label: str):
    _print_header(f"{label} — Sync reading")

    with TM.timer(f"{label}_sync_read"):
        count = 0
        while True:
            frame = core.get_frame()
            if frame is None:
                break

            _show_frame(window, frame, delay_ms=1)

            count += 1
            if count >= max_frames:
                break


def test_async_read(core: VideoCore, window: str, max_frames: int, label: str):
    _print_header(f"{label} — Async reading")

    core.start_async()

    with TM.timer(f"{label}_async_read"):
        count = 0
        while True:
            frame = core.get_last_async_frame()
            if frame is None:
                continue

            _show_frame(window, frame, delay_ms=1)
            count += 1

            if count >= max_frames:
                break

    core.stop_async()


def test_seek_accuracy(core: VideoCore, window: str, frames_to_test: list[int], label: str):
    _print_header(f"{label} — Seek accuracy")

    for idx in frames_to_test:

        with TM.timer(f"{label}_seek"):
            ok = core.go_to_frame(idx)

        if not ok:
            print(f"Seek failed for frame {idx}")
            continue

        frame = core.get_frame()
        _show_frame(window, frame, delay_ms=200)

        decoder_pos = core.get_decoder_frame_id()
        _print_seek_info(idx, decoder_pos)


def test_buffer(core: VideoCore, window: str, frames: int, label: str):
    _print_header(f"{label} — RingBuffer")

    with TM.timer(f"{label}_buffer"):
        for _ in range(frames):
            frame = core.get_frame()
            if frame is None:
                break

    last = core.get_last_buffered()
    print("Last frame exists:", last is not None)
    if last is not None:
        _show_frame(window, last, delay_ms=400)


# ============================================================
#                     ЗАПУСК ОДНОЙ КОНФИГУРАЦИИ
# ============================================================

def run_tests(
    path: str | Path,
    decoder: DecoderType,
    async_enabled: bool,
    buffer_size: int,
    label: str
):
    window = "NeuroVideoCore — Debug Runner"

    _print_header(f"RUNNING TESTS FOR {label}")

    config = VideoCoreConfig(
        decoder=decoder,
        async_enabled=async_enabled,
        buffer_size=buffer_size,
    )

    core = VideoCore(path, config)
    core.open()

    meta = core.get_metadata()
    print(f"FPS: {meta['fps']} | Total frames: {meta['total_frames']}")

    # Тесты
    test_sync_read(core, window, max_frames=150, label=label)

    if async_enabled:
        test_async_read(core, window, max_frames=150, label=label)

    test_seek_accuracy(core, window, frames_to_test=[0, 5, 10, 25, 100, 150], label=label)

    if buffer_size > 0:
        test_buffer(core, window, frames=50, label=label)

    core.close()
    cv2.destroyAllWindows()


# ============================================================
#                        ТОЧКА ВХОДА
# ============================================================

if __name__ == "__main__":

    PATH = r"w:\MATLLER\cherkiz\REVISION_9\ml_cam101_05112025_1400.avi"

    # ---------------------------------------------------------
    # СПИСОК КОНФИГУРАЦИЙ ДЛЯ АВТОМАТИЧЕСКОГО ЗАПУСКА
    # ---------------------------------------------------------

    CONFIGS = [
        # Hybrid
        {"decoder": DecoderType.HYBRID, "async_enabled": False, "buffer_size": 0,  "label": "Hybrid_sync"},
        {"decoder": DecoderType.HYBRID, "async_enabled": False, "buffer_size": 50, "label": "Hybrid_buffer"},
        {"decoder": DecoderType.HYBRID, "async_enabled": True,  "buffer_size": 0,  "label": "Hybrid_async"},
        {"decoder": DecoderType.HYBRID, "async_enabled": True, "buffer_size": 50, "label": "Hybrid_async_buffer"},

        # OpenCV
        {"decoder": DecoderType.OPENCV, "async_enabled": False, "buffer_size": 0,  "label": "OpenCV_sync"},
        {"decoder": DecoderType.OPENCV, "async_enabled": False, "buffer_size": 50, "label": "OpenCV_buffer"},
        {"decoder": DecoderType.OPENCV, "async_enabled": True, "buffer_size": 0, "label": "OpenCV_async"},
        {"decoder": DecoderType.OPENCV, "async_enabled": True, "buffer_size": 50, "label": "OpenCV_async_buffer"},

        # PyAV
        {"decoder": DecoderType.PYAV, "async_enabled": False, "buffer_size": 0,  "label": "PyAV_sync"},
        {"decoder": DecoderType.PYAV, "async_enabled": False, "buffer_size": 50, "label": "PyAV_buffer"},
        {"decoder": DecoderType.PYAV, "async_enabled": True, "buffer_size": 0, "label": "PyAV_async"},
        {"decoder": DecoderType.PYAV, "async_enabled": True, "buffer_size": 50, "label": "PyAV_async_buffer"},
    ]

    # ---------------------------------------------------------
    # Запуск всех тестов подряд
    # ---------------------------------------------------------

    for cfg in CONFIGS:
        run_tests(
            PATH,
            decoder=cfg["decoder"],
            async_enabled=cfg["async_enabled"],
            buffer_size=cfg["buffer_size"],
            label=cfg["label"]
        )

    # ---------------------------------------------------------
    # Финальная таблица сравнения
    # ---------------------------------------------------------

    TM.print_summary(sort_by="total")

