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
    Off = 'none'
    Single = 'single'
    All = 'all'


class Queue(Generic[T]):
    '''
    A iterable, repeatable queue

    ----------
    Attributes
    ----------
    items: `list[T]`
        The list of items the queue contains
    repeat: `RepeatMode`
        The repeat state
    index: `int`
        The current index
    '''

    def __init__(
        self,
        items: Optional[Iterable[T]] = None,
        *,
        repeat: RepeatMode = RepeatMode.Off,
        index: int = 0
    ) -> None:
        self._items = [] if items is None else items
        self._repeat = repeat
        self._index = index

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> T:
        if self._repeat == RepeatMode.Single:
            return self._items[self._index]
        else:
            if self._index >= len(self._items):
                if self._repeat == RepeatMode.Off:
                    raise StopIteration
                self._index %= len(self._items)
            self._index += 1
            return self._items[self._index - 1]

    def __getitem__(self, key: int) -> T:
        return self._items[key]

    def __setitem__(self, key: int, value: T) -> None:
        self._items[key] = value

    def __contains__(self, item: T) -> bool:
        return item in self._items

    def __bool__(self) -> bool:
        return self._items != []

    def __add__(self, other) -> Self:
        return Queue(items=self._items + other._items)

    def __iadd__(self, other) -> None:
        self._items += other._items

    def __mult__(self, times: int) -> Self:
        if not isinstance(times, int):
            raise TypeError('Queue can only be multiplied with an integer')
        return Queue(items=self._items*times)

    def __imult__(self, times: int) -> None:
        if not isinstance(times, int):
            raise TypeError('Queue can only be multiplied with an integer')
        self._items *= times

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f'Queue({self._items!r}, {self._index})'

    __hash__ = None

    @property
    def items(self) -> list[T]:
        return self._items

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @repeat.setter
    def repeat(self, value: RepeatMode):
        if type(value) is not RepeatMode:
            raise TypeError("value must be of type RepeatMode")
        if value == RepeatMode.Single and self._repeat != RepeatMode.Single:
            self._index -= 1
        self._repeat = value

    @property
    def index(self) -> int:
        '''
        Get current index

        Setting the index to a value larger than the length of the queue will wrap around
        '''
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = (self._index + value) % len(self._items)

    @property
    def current(self) -> tuple[int, T]:
        '''Current index and item'''
        if self._repeat == RepeatMode.Single:
            return self._index, self._items[self._index]
        else:
            return self._index - 1, self._items[self._index - 1]

    def append(self, item: T) -> None:
        '''Append a value to the end of the queue'''
        self._items.append(item)

    def insert(self, position: int, item: T) -> None:
        '''
        Insert a value at given position

        Automatically increments index if item was inserted before current index
        '''
        self._items.insert(position, item)
        if position <= self._index:
            self.index += 1

    def clear(self) -> None:
        '''
        Clear the queue
        '''
        self._items.clear()

    def pop(self, position: int) -> T:
        '''
        Remove the item at given position and return it

        Automatically decrements index if the index of the popped item was before current index
        '''
        if position <= self._index:
            self._index -= 1
        return self._items.pop(position)

    def remove(
        self,
        item: T,
    ) -> None:
        '''
        Remove first instance of `item` found

        Automatically decrements index if the index a removed item was before current index
        '''
        for i, it in enumerate(self._items):
            if it == item:
                self.pop(i)


if __name__ == '__main__':
    # lazy testing
    base = range(5, 15, 2)
    q1 = Queue(base)
    for _, item in zip(range(2), q1):
        print(item)
    print('-'*80, 'all')
    q1.repeat = RepeatMode.All
    for _, item in zip(range(10), q1):
        print(item)
    print('-'*80, 'single')
    q1.repeat = RepeatMode.Single
    for _, item2 in zip(range(3), q1):
        print(item2)
