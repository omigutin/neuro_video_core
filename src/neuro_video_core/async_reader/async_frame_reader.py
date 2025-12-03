import threading
import time
from typing import Optional, Any


class AsyncFrameReader:
    """
        Асинхронный читатель кадров.
        Запускает отдельный поток, который постоянно вызывает
        decoder.read() и сохраняет последний успешный кадр.
    """

    def __init__(self, decoder: Any, poll_delay: float = 0.0):
        """
            :param decoder: декодер, реализующий BaseDecoder
            :param poll_delay: задержка между попытками чтения (обычно 0)
        """
        self._decoder = decoder
        self._poll_delay = poll_delay

        self._last_frame: Optional[Any] = None
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """ Запускает поток чтения кадров. """
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """ Останавливает поток. """
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._thread = None

    def _run(self) -> None:
        """ Основной цикл чтения кадров. """
        while self._running:
            try:
                frame = self._decoder.read()
            except Exception:
                # не останавливаем приложение из-за ошибки декодера
                frame = None

            if frame is None:
                # если кадры закончились — выходим
                break

            self._last_frame = frame

            if self._poll_delay > 0:
                time.sleep(self._poll_delay)

        self._running = False

    def get_last(self):
        """ Возвращает последний успешно прочитанный кадр. """
        return self._last_frame
