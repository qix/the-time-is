#!/bin/env python3
import functools
import heapq
import math
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
        times.append(f'{hour} {ampm}.')
        for phrase in past:
            times.append(f'{phrase} past {hour} {ampm}.')
        for minute in minutes:
            times.append(f'{hour} {minute} {ampm}.')

random.shuffle(times)

W, H = 25, 25
grid = [[' '] * W for y in range(H)]

def flip_grid():
    global grid
    grid = [list(reversed(line)) for line in reversed(grid)]

def search(x, y, word, banned, max_distance=None, insert_if_empty=False):
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
        if x >= W or y >= H:
            return
        if (x, y) in seen:
            return
        if (x, y) in banned:
            push(x + 1, y)
            push(x, y + 1)
            return
    
        distance = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2)
        # distance = math.sqrt((x - 0) ** 2 + (y - 0) ** 2)
        if max_distance and distance >= max_distance:
            return

        seen.add((x, y))
        heapq.heappush(priority_q, (distance, x, y))


    def check(x, y, xd, yd):
        'Check if the position is valid for the word'
        for idx, letter in enumerate(word):
            grid_letter = grid[y + idx * yd][x + idx * xd]
            if grid_letter != letter and not (insert_if_empty and grid_letter == ' '):
                return False
        return True

    push(x, y)
    while priority_q:
        (distance, x, y) = heapq.heappop(priority_q)

        directions = ([(+1, 0)] if x + len(word) <= W else []) + ([(0, +1)] if y + len(word) <= H else []) 
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
    
def insert(words):
    '''
    Try insert a set of words, return their locations
    '''
    x, y = 0, 0
    failed = False
    locations = []

    banned = set()
    for idx, word in enumerate(words):
        found = False

        search_configs = [
            (3, False), (1, True),
            (5, False), (3, True),
            (7, False), (5, True),
            (10, False), (7, True),
            (15, False), (10, True),
            (20, False), (15, True),
            (None, False), (None, True),
        ]
        if idx == len(words) - 1:
            search_configs = [(None, False), (None, True)] 


        for (max_distance, insert_if_empty) in search_configs:
            found = search(x, y, word, banned, max_distance=max_distance, insert_if_empty=insert_if_empty)

            if found:
                break

        if not found:
            x = 0
            y = y + len(words[idx - 1]) + 1
            found = search(x, y, word, banned, insert_if_empty=True)

        if not found:
            return None

        locations.append((word, found))
        x, y, _, _, xd, yd = found

        banned.add((x, y))
        
        # ban words immediately below a horizontal word (or next to vertical)
        for idx in range(len(word)):
            if xd > 0:
                banned.add((x + 1 * idx, y + 1))
            else:
                banned.add((x + 1, y + 1 * idx))

        # ban immediate trailing words
        # @TODO: need to ban starting on last letter going same direction (but hard)
        #        ban both for now
        if xd > 0:
            banned.add((x + len(word), y))
            banned.add((x + len(word) - 1, y))
        else:
            banned.add((x, y + len(word)))
            banned.add((x, y + len(word) - 1))


    return locations

def print_grid(highlight=set(), fill=False):
    def render(x, y, letter):
        if letter == ' ' and fill:
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

# Insert the first half of each phrase
print('Inserting first half')
for time in times:
    words = time.split(' ')
    insert(['the', 'time', 'is'] + words[:len(words) // 2])

# Flip the board and insert the last half
print('Inserting reversed last half')
flip_grid()
for time in times:
    words = time.split(' ')
    words = list(reversed(list(word[::-1] for word in words[len(words) // 2:])))
    insert(words)

# Flip back and insert full phrases
print('Inserting full phrases')
flip_grid()
random_time = None
inserted = 0
for time in times:
    locations = insert(['the', 'time', 'is'] + time.split(' '))
    if locations:
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

print_grid(highlight, fill=True)