#!/bin/env python3
import functools
import heapq
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

past = [
    *digits,  'quarter',
]
minutes = [
    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
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
        for phrase in past:
            times.append(f'the time is {phrase} past {hour} {ampm}.')
        for minute in minutes:
            times.append(f'the time is {hour} {minute} {ampm}.')

random.shuffle(times)

W, H = 33, 33
grid = [[' '] * W for y in range(H)]

def search(x, y, word, banned,  insert_if_empty=False):
    '''
    Search for a word in the grid.
    Returns end position (x, y) and (xd, yd) direction vector
    '''
    start_x, start_y = x, y
    priority_q = []
    seen = set()

    def push(x, y):
        '''
        Push item to heaped priority queue, with priority as distance from origin
        '''
        if x + len(word) + 1 >= W or y + len(word) + 1 >= H:
            return
        if (x, y) in seen:
            return
        if (x, y) in banned:
            push(x + 1, y)
            push(x, y + 1)
            return
    
        seen.add((x, y))
        heapq.heappush(priority_q, (x - start_x + y - start_y, x, y))


    def check(x, y, xd, yd):
        'Check if the position is valid for the word'
        for idx, letter in enumerate(word):
            grid_letter = grid[y + idx * yd][x + idx * xd]
            if grid_letter != letter and not (insert_if_empty and grid_letter == ' '):
                return False
        return True

    push(x + 1, y)
    push(x, y + 1)
    while priority_q:
        (distance, x, y) = heapq.heappop(priority_q)

        directions = ([(+1, 0)] if x + len(word) < W else []) + ([(0, +1)] if y + len(word) < H else []) 
        random.shuffle(directions)

        for (xd, yd) in directions:
            if check(x, y, xd, yd):
                if insert_if_empty:
                    for idx, letter in enumerate(word):
                        grid[y + idx * yd][x + idx * xd] = letter
                return (x, y, x + (len(word) - 1) * xd, y + (len(word) - 1) * yd, xd, yd)

        push(x + 1, y)
        push(x, y + 1)

    return None
    


random_time = None
inserted = 0
for time in times:
    x, y = 0, 0
    failed = False
    locations = []

    banned = set()


    for word in time.split(' '):
        found = search(x, y, word, banned)
        
        # after searching for existing, try insert it
        if not found:
            found = search(x, y, word, banned, True)

        if not found:
            failed = True
            break

        locations.append((word, found))
        x, y, _, _, xd, yd = found

        # ban words immediately below a horizontal word (or next to vertical)
        for idx in range(len(word)):
            if xd > 0:
                banned.add((x + 1 * idx, y + 1))
            else:
                banned.add((x + 1, y + 1 * idx))

        # ban immediate trailing words
        if xd > 0:
            banned.add((x + len(word), y))
        else:
            banned.add((x, y + len(word)))

    if failed:
        continue

    inserted += 1
    if random.random() < 1 / (inserted):
        random_time = locations

print(f'Inserted {inserted} of {len(times)} times [{W}x{H}]')
highlight = []
words = []
for location in random_time:
    word, (x, y, _, _, xd, yd) = location
    words.append(word)
    for i in range(len(word)):
        highlight.append((x, y))
        (x, y) = x + xd, y + yd


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