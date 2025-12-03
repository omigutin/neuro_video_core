import cv2
from pathlib import Path
from typing import Optional

from src.neuro_video_core.core.video_core import VideoCore
from src.neuro_video_core.settings import VideoCoreConfig
from src.neuro_video_core.decoders.decoder_type import DecoderType


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
    """Вывод информации о точности перехода."""
    print(
        f"Requested: {requested_frame:6d} | "
        f"Decoder:  {decoder_frame:6d}"
    )


# ============================================================
#               СЦЕНАРИИ ТЕСТИРОВАНИЯ MVP
# ============================================================

def test_sync_read(core: VideoCore, window: str, max_frames: int = 200):
    """Проверка синхронного чтения кадров."""
    _print_header("TEST: Sync reading")

    count = 0
    while True:
        frame = core.get_frame()
        if frame is None:
            print("End of video.")
            break

        _show_frame(window, frame, delay_ms=1)

        decoder_pos = core.get_decoder_frame_id()
        # print(f"Decoder frame: {decoder_pos}")   # for debug

        count += 1
        if count >= max_frames:
            print("Stopping test (limit reached).")
            break


def test_async_read(core: VideoCore, window: str, max_frames: int = 200):
    """Проверка асинхронного чтения кадров."""
    _print_header("TEST: Async reading")

    core.start_async()
    count = 0

    while True:
        frame = core.get_last_async_frame()
        if frame is None:
            continue

        _show_frame(window, frame, delay_ms=1)
        count += 1

        if count >= max_frames:
            print("Stopping async test (limit reached).")
            break

    core.stop_async()


def test_seek_accuracy(core: VideoCore, window: str, frames_to_test: list[int]):
    """Проверка точности seek()."""
    _print_header("TEST: Seek accuracy")

    for idx in frames_to_test:
        print(f"\nSeeking to frame: {idx}...")

        ok = core.go_to_frame(idx)
        if not ok:
            print(f"Seek FAILED for frame {idx}")
            continue

        frame = core.get_frame()
        _show_frame(window, frame, delay_ms=300)

        decoder_pos = core.get_decoder_frame_id()
        _print_seek_info(idx, decoder_pos)


def test_buffer(core: VideoCore, window: str, frames: int = 50):
    """Проверка работы кольцевого буфера."""
    if not core._buffer:
        print("Buffer disabled, skipping test.")
        return

    _print_header("TEST: RingBuffer")

    for _ in range(frames):
        frame = core.get_frame()
        if frame is None:
            break

    print(f"Buffer size = {core._buffer.size}")
    print("Last frame exists:", core.get_last_buffered() is not None)

    last = core.get_last_buffered()
    if last is not None:
        _show_frame(window, last, delay_ms=500)


# ============================================================
#                    ОСНОВНОЙ ЗАПУСК ТЕСТОВ
# ============================================================

def run_tests(
    path: str | Path,
    decoder: DecoderType = DecoderType.HYBRID,
    async_enabled: bool = False,
    buffer_size: int = 0,
):
    window = "NeuroVideoCore — Debug Runner"

    config = VideoCoreConfig(
        decoder=decoder,
        async_enabled=async_enabled,
        buffer_size=buffer_size,
    )

    core = VideoCore(path, config)

    print("\nOpening decoder...")
    core.open()

    # --- METADATA ---
    print("\n--- METADATA ---")
    meta = core.get_metadata()
    print(f"FPS:          {meta['fps']}")
    print(f"Total frames: {meta['total_frames']}")

    # ---------------------------------------------------------
    # Выполнение тестов
    # ---------------------------------------------------------

    test_sync_read(core, window, max_frames=150)

    if async_enabled:
        test_async_read(core, window, max_frames=150)

    test_seek_accuracy(core, window, frames_to_test=[0, 5, 10, 25, 100, 150])

    if buffer_size > 0:
        test_buffer(core, window)

    # ---------------------------------------------------------

    print("\nAll tests completed.")
    core.close()
    cv2.destroyAllWindows()


# ============================================================
#                 ТЕСТОВЫЕ ВЫЗОВЫ ДЛЯ ЗАПУСКА
# ============================================================

if __name__ == "__main__":

    PATH = r"w:\MATLLER\cherkiz\REVISION_9\ml_cam101_05112025_1400.avi"

    # 1) Hybrid + sync
    run_tests(PATH, decoder=DecoderType.HYBRID, async_enabled=False, buffer_size=0)

    # 2) Hybrid + buffer
    # run_tests(PATH, decoder=DecoderType.HYBRID, async_enabled=False, buffer_size=50)

    # 3) Hybrid + async
    # run_tests(PATH, decoder=DecoderType.HYBRID, async_enabled=True, buffer_size=0)

    # 4) Hybrid + async + buffer
    # run_tests(PATH, decoder=DecoderType.HYBRID, async_enabled=True, buffer_size=50)

    # 5) OpenCV-only
    # run_tests(PATH, decoder=DecoderType.OPENCV)

    # 6) PyAV-only
    # run_tests(PATH, decoder=DecoderType.PYAV)
