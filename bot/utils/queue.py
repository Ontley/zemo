from enum import Enum
from random import shuffle
from typing import (
    Generic,
    Iterable,
    Iterator,
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

    Parameters
    ----------
    items: `Optional[Iterable[T]]`
        The list of items the queue contains
    repeat: `RepeatMode`
        The repeat state
    index: `int`
        The current index
    """

    def __init__(
        self,
        items: Optional[Iterable[T]] = None,
        *,
        repeat: RepeatMode = RepeatMode.All,
        index: int = 0
    ) -> None:
        self._items = [] if items is None else list(items)
        self._repeat = repeat
        self._index = index
        self._jumped = False
        self._advanced = False

    def __iter__(self) -> Iterator[T]:
        """Get self as iterator."""
        while True:
            self._jumped = False
            self._advanced = True
            if self._index >= len(self._items):
                if self._repeat == RepeatMode.Off:
                    raise StopIteration('Queue exhausted')
                self._index %= len(self._items)
            yield self._items[self._index]
            if self._repeat != RepeatMode.Single:
                self._index += 1

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
        """Representation of the Queue object"""
        return f'{type(self).__qualname__}({self._items}, {self._index})'

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

        if self._jumped:
            if self._repeat == RepeatMode.Single != value:
                self._index -= 1
            elif self._repeat != RepeatMode.Single == value:
                self._index += 1
        self._repeat = value

    @property
    def index(self) -> int:
        """
        Get current index.

        Setting the index higher than Queue length will wrap around.

        If repeat is not Single, the next item will be the one ahead of set index,
        use Queue.jump otherwise
        """
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value % len(self._items)
        self._advanced = False

    @property
    def current(self) -> T:
        """Get current item."""
        return self._items[self._index]

    def jump(self, index: int) -> None:
        """
        Force next item to be at `index`, even if repeat mode is changed after.

        Raises
        ------
        `ValueError`: index is out of range
        """
        if index not in range(len(self)):
            raise ValueError('index out of range')
        self._jumped = True
        if self._advanced and self._repeat != RepeatMode.Single:
            index -= 1
        self.index = index

    def skip(self, offset: int = 1) -> None:
        """Skip ahead, force next item to be at current index + `offset`"""
        self._jumped = True
        if self._advanced and self._repeat != RepeatMode.Single:
            offset -= 1
        self.index += offset

    def shuffle(self) -> None:
        """Shuffles the Queue in place, putting the current item T at position 1 (index 0), and shuffling the rest"""
        curr_i, curr = self.index, self.current
        self._items[0], self._items[curr_i] = curr, self._items[0]
        lst = self._items[1:]
        shuffle(lst)
        self._items[1:] = lst
        self._index = 0

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

    def pop(self, position: int = -1) -> T:
        """
        Remove the item at given position (default last item) and return it.

        Decrements index if removed item was before current index.
        """
        if self._index >= position != -1:
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
                del self._items[i]
                if i < self._index:
                    self._index -= 1
