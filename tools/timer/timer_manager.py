from pathlib import Path
from typing import Optional, Dict

from .timer_stats import TimerStats
from .timer_context import TimerContext


class TimerManager:
    """
        Главный менеджер таймеров.
        Собирает, агрегирует и выводит статистику.
    """

    def __init__(self, log_file: Optional[str | Path] = None):
        self.stats: Dict[str, TimerStats] = {}
        self.log_file = Path(log_file) if log_file else None

    # ---------------------------------------------------------
    # Создание таймера
    # ---------------------------------------------------------

    def timer(self, name: str) -> TimerContext:
        """Возвращает контекст для измерения времени блока кода."""
        return TimerContext(name, self)

    # ---------------------------------------------------------
    # Запись данных
    # ---------------------------------------------------------

    def add_time(self, name: str, elapsed: float):
        """Добавляет одно измерение по указанному имени блока."""
        if name not in self.stats:
            self.stats[name] = TimerStats()
        self.stats[name].times.append(elapsed)

    # ---------------------------------------------------------
    # Вывод статистики
    # ---------------------------------------------------------

    def print_summary(self, sort_by: str = "total"):
        """
            Выводит сводную таблицу.

            sort_by:
                "total" — сортировать по суммарному времени
                "avg"   — по среднему
                "max"   — по максимуму
        """
        if not self.stats:
            print("[TimerManager] No stats collected.")
            return

        print("\n" + "=" * 80)
        print("TIMER SUMMARY")
        print("=" * 80)

        # выбор ключа сортировки
        if sort_by == "avg":
            key_fn = lambda item: item[1].avg
        elif sort_by == "max":
            key_fn = lambda item: item[1].max
        else:
            key_fn = lambda item: item[1].total

        for name, stat in sorted(self.stats.items(), key=key_fn, reverse=True):
            print(
                f"{name:25s} | "
                f"count: {stat.count:5d} | "
                f"total: {stat.total:10.6f} | "
                f"avg: {stat.avg:10.6f} | "
                f"min: {stat.min:10.6f} | "
                f"max: {stat.max:10.6f}"
            )

        if self.log_file:
            self._save_to_log()

    def _save_to_log(self):
        """Сохраняет статистику в лог-файл."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf8") as f:
                f.write(self._as_text())
        except Exception as e:
            print(f"[TimerManager] Failed to write log: {e}")

    def _as_text(self) -> str:
        """Форматирует статистику в многострочный текст."""
        lines = ["TIMER SUMMARY\n"]
        for name, stat in self.stats.items():
            lines.append(
                f"{name:25s} | "
                f"count={stat.count} total={stat.total:.6f} "
                f"avg={stat.avg:.6f} min={stat.min:.6f} max={stat.max:.6f}"
            )
        return "\n".join(lines) + "\n"
