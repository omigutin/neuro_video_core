import time


class TimerContext:
    """
        Контекстный менеджер, измеряющий время выполнения блока.
        Сам по себе он статистику не хранит — только передаёт её менеджеру.
    """

    def __init__(self, name: str, manager):
        self.name = name
        self.manager = manager
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.perf_counter() - self.t0
        self.manager.add_time(self.name, elapsed)
