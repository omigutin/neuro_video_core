from typing import Optional, List, Any


class RingBuffer:
    """
        Кольцевой буфер фиксированной ёмкости.
        Хранит последние N элементов.
        Индексация:
            0           → самый старый элемент
            size - 1    → самый новый элемент
    """

    def __init__(self, capacity: int):
        """
            :param capacity: максимальное количество элементов в буфере
        """
        if capacity <= 0:
            raise ValueError("RingBuffer capacity must be > 0")

        self._capacity = capacity
        self._data: List[Optional[Any]] = [None] * capacity
        self._size = 0
        self._start = 0  # индекс самого старого элемента
        self._end = 0    # позиция для записи нового элемента

    def push(self, item: Any) -> None:
        """ Добавляет элемент в буфер. """
        self._data[self._end] = item

        if self._size < self._capacity:
            self._size += 1
        else:
            # буфер заполнен — сдвигаем начало
            self._start = (self._start + 1) % self._capacity

        self._end = (self._end + 1) % self._capacity

    def get(self, frame_index: int) -> Optional[Any]:
        """
            Возвращает элемент по логическому индексу.
            0 → самый старый
            size-1 → самый новый
        """
        if frame_index < 0 or frame_index >= self._size:
            return None

        real_index = (self._start + frame_index) % self._capacity
        return self._data[real_index]

    def last(self) -> Optional[Any]:
        """ Возвращает самый новый элемент. """
        if self._size == 0:
            return None

        last_index = (self._end - 1 + self._capacity) % self._capacity
        return self._data[last_index]

    def size(self) -> int:
        """ Количество элементов в буфере. """
        return self._size

    def capacity(self) -> int:
        """ Максимальная вместимость буфера. """
        return self._capacity

    def clear(self) -> None:
        """ Очищает буфер. """
        self._data = [None] * self._capacity
        self._size = 0
        self._start = 0
        self._end = 0
