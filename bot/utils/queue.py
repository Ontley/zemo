"""
Provides a Queue class, which can be iterated over in 3 different ways.

See Queue class for more information.
"""

from enum import Enum
from typing import (
    Generic,
    Iterable,
    Optional,
    TypeVar,
)
from typing_extensions import Self


__all__ = [
    'RepeatMode',
    'Queue'
]


T = TypeVar('T')


class RepeatMode(Enum):
    """Enum for Queue repeat modes."""

    Off = 'off'
    Single = 'single'
    All = 'all'


class Queue(Generic[T]):
    """
    A iterable, repeatable queue.

    ----------
    Attributes
    ----------
    - items: `Optional[Iterable[T]]
        The list of items the queue contains
    - repeat: `RepeatMode`
        The repeat state
    - index: `int`
        The current index
    """

    def __init__(
        self,
        items: Optional[Iterable[T]] = None,
        *,
        repeat: RepeatMode = RepeatMode.All,
        index: int = 0
    ) -> None:
        self._items = [] if items is None else items
        self._repeat = repeat
        self._index = index

    def __iter__(self) -> Self:
        """Get self as iterator."""
        return self

    def __next__(self) -> T:
        """Get the next element from the Queue object."""

        # TODO: not worky
        if self._index >= len(self._items):
            if self._repeat == RepeatMode.Off:
                raise StopIteration('Queue exhausted')
            self._index %= len(self._items)
        item = self._items[self.index]
        if self._repeat != RepeatMode.Single:
            self._index += 1
        return item

    def __getitem__(self, index: int) -> T:
        """Get the item at the given index."""
        return self._items[index]

    def __setitem__(self, index: int, value: T) -> None:
        """Set the item at the given index."""
        self._items[index] = value

    def __contains__(self, item: T) -> bool:
        """Check if the Queue contains the item."""
        return item in self._items

    def __bool__(self) -> bool:
        """Check if the queue is non-empty."""
        return self._items != []

    def __eq__(self, other: Iterable[T]) -> bool:
        """Compare the items of the iterables."""
        if not isinstance(other, Iterable):
            return False
        return len(self) == len(other) and \
            all(s_item == o_item for s_item, o_item in zip(self._items, other))

    def __add__(self, other: Self) -> Self:
        """Concatenate two Queues."""
        if not isinstance(other, Queue):
            raise TypeError(
                f'Can only concatenate {type(self).__name__} (not "{type(other).__name__}") and {type(self).__name__}'
            )
        return Queue(items=self._items + other._items)

    def __iadd__(self, other: Self) -> None:
        """Concatenate to self."""
        if not isinstance(other, Queue):
            raise TypeError(
                f'Can only concatenate {type(self).__name__} (not "{type(other).__name__}") and {type(self).__name__}'
            )
        self._items += other._items

    def __mult__(self, times: int) -> Self:
        """
        Repeat the Queue an integer amount of times.

        Returns a Queue with the same repeat mode
        """
        if not isinstance(times, int):
            raise TypeError(
                f'Can not multiply {type(self).__name__} by non-int of type {type(times).__name__}'
            )
        return Queue(
            items=self._items*times,
            repeat=self._repeat
        )

    def __imult__(self, times: int) -> None:
        """Repeat own items an integer amount of times."""
        if not isinstance(times, int):
            raise TypeError(
                f'Can not multiply {type(self).__name__} by non-int of type {type(times).__name__}'
            )
        self._items *= times

    def __len__(self) -> int:
        """Get the amount of items the Queue contains."""
        return len(self._items)

    def __repr__(self) -> str:
        """Return a representation of the Queue object"""
        return f'{type(self).__qualname__}({tuple(self._items)!r}, {self._index})'

    __hash__ = None

    @property
    def items(self) -> list[T]:
        """Get a reference of the queue items."""
        return self._items

    @property
    def repeat(self) -> RepeatMode:
        """Get the queue's repeat mode."""
        return self._repeat

    @repeat.setter
    def repeat(self, value: RepeatMode):
        if not isinstance(value, RepeatMode):
            raise TypeError(f"value must be of type {RepeatMode.__qualname__}")
        if value == RepeatMode.Single and self._repeat != RepeatMode.Single:
            self._index -= 1
        self._repeat = value

    @property
    def index(self) -> int:
        """
        Get current index.

        Setting the index higher than Queue length will wrap on `next()` call.
        """
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    @property
    def current(self) -> tuple[int, T]:
        """Get current index and item."""
        if self._repeat == RepeatMode.Single:
            return self._index, self._items[self._index]
        return self._index - 1, self._items[self._index - 1]

    def append(self, item: T) -> None:
        """Append a value to the end of the queue."""
        self._items.append(item)

    def insert(self, position: int, item: T) -> None:
        """
        Insert a value at given position.

        Increments index if item was inserted before current index.
        """
        self._items.insert(position, item)
        if position <= self._index:
            self.index += 1

    def clear(self) -> None:
        """Clear the queue."""
        self._items.clear()

    def pop(self, position: Optional[int]) -> T:
        """
        Remove the item at given position and return it.

        Decrements index if removed item was before current index.
        """
        if position <= self._index:
            self._index -= 1
        return self._items.pop(position)

    def remove(
        self,
        item: T,
    ) -> None:
        """
        Remove first instance of `item` found.

        Decrements index if removed item was before current index.
        """
        for i, iitem in enumerate(self._items):
            if iitem == item:
                self.pop(i)
