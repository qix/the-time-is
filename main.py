#!/bin/env python3
import functools
import random
import string
import sys

try:
    if len(sys.argv) == 2:
        random.seed(int(sys.argv[1]))
except ValueError:
    print('Usage: the-time-is [integer seed]', file=sys.stderr)
    sys.exit(1)

digits = [
    'one', 'two', 'three', 'four' , 'five', 'six', 'seven', 'eight', 'nine',
]

minutes = [
    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'quarter',
    'sixteen', 'seventeen', 'eighteen', 'nineteen',
    'twenty', *[f'twenty {digit}' for digit in digits],
    'thirty', *[f'thirty {digit}' for digit in digits],
    'forty', *[f'forty {digit}' for digit in digits],
    'fifty', *[f'fifty {digit}' for digit in digits],
]

hours = ['twelve', *digits, 'ten', 'eleven']

times = []
for ampm in ['am', 'pm']:
    for hour in hours:
        times.append(f'the time is {hour} {ampm}.')
        for digit in digits:
            times.append(f'the time is {digit} past {hour} {ampm}.')
        for minute in minutes:
            times.append(f'the time is {hour} {minute} {ampm}.')
        for minute in minutes:
            times.append(f'the time is {hour} {minute} {ampm}.')


W, H = 80, 40
grid = [[' '] * W for y in range(H)]

@functools.lru_cache(maxsize=500000)
def search(x, y, word, insert=False):
    '''
    Search for a word in the grid, returns (start x, start y, finish x, finish y, x diff, y diff)
    '''
    if x + len(word) < W and all(
        grid[y][x + idx] == letter or (insert and grid[y][x + idx] == ' ')
        for idx, letter in enumerate(word)
    ):
        if insert:
            for idx, letter in enumerate(word):
                 grid[y][x + idx] = letter
        return (x, y, x + len(word) - 1, y, +1, 0)

    if y + len(word) < y and all(
        grid[y + idx][x] == letter or (insert and grid[y + idx][x] == ' ')
        for idx, letter in enumerate(word)
    ):
        if insert:
            for idx, letter in enumerate(word):
                 grid[y + idx][x] = letter
        return (x, y, x, y + len(word) - 1, 0, +1)

    rv = None
    if rv is None and x + len(word) + 1 < W:
        rv = search(x+1, y, word, insert=insert)
    if rv is None and y + len(word) + 1 < H:
        rv = search(x, y + 1, word, insert=insert)
    return rv
    


random_time = None
inserted = 0
for time in times:
    x, y = 0, 0
    failed = False
    locations = []

    for word in time.split(' '):
        found = search(x, y, word)
        if found:
            locations.append((word, found))
            _, _, x, y, _, _ = found
            continue
        
        empty = search(x + 2, y, word, True)
        if not empty:
            empty = search(x, y + 2, word, True)

        if not empty:
            failed = True
            break

        locations.append((word, empty))
        _, _, x, y, _, _ = empty

    if failed:
        continue

    inserted += 1
    if random.random() < 1 / (inserted):
        random_time = locations

print(f'Inserted {inserted} of {len(times)} times')
highlight = []
words = []
for location in random_time:
    word, (xs, ys, xe, ye, xd, yd) = location
    words.append(word)
    while xs <= xe and ys <= ye:
        highlight.append((xs, ys))
        xs += xd
        ys += yd


def render(x, y, letter):
    if letter == ' ':
        letter = random.choice(string.ascii_lowercase)
    if (x, y) in highlight:
        # apply a green highlight
        letter = '\033[1;32m' + letter + '\033[0m'
    return letter
    
print()
for y, line in enumerate(grid):
    print(''.join(
        render(x, y, letter)
        for x, letter in enumerate(line)
    ))
print()