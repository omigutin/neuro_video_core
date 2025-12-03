class TimerStats:
    """
        Хранилище статистики по одному имени блока.
        Содержит:
        * индивидуальные измерения
        * сумму
        * min
        * max
        * среднее
    """

    __slots__ = ("times",)

    def __init__(self):
        self.times = []

    @property
    def count(self) -> int:
        return len(self.times)

    @property
    def total(self) -> float:
        return sum(self.times)

    @property
    def avg(self) -> float:
        return self.total / self.count if self.count else 0.0

    @property
    def min(self) -> float:
        return min(self.times) if self.count else 0.0

    @property
    def max(self) -> float:
        return max(self.times) if self.count else 0.0
