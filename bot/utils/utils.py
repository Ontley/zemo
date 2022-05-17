__all__ = [
    'readable_time'
]


def readable_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    time = ''
    if h:
        time += f'{h}h'
        if m or s:
            time += ':'
    if m:
        time += f'{m}m'
        if s:
            time += ':'
    if s:
        time += f'{s}s'
    return time


if __name__ == '__main__':
    print(readable_time(5))
    print(readable_time(60))
    print(readable_time(423))
    print(readable_time(3600*2 + 60))
    print(readable_time(213312))
