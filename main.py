#!/bin/env python3
import dataclasses
import functools
import heapq
import json
import math
import random
import string
import sys
from collections import defaultdict
from copy import deepcopy
from time import sleep

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
from_ten = [
    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen',
    'twenty', *[f'twenty {digit}' for digit in digits],
    'thirty', *[f'thirty {digit}' for digit in digits],
    'forty', *[f'forty {digit}' for digit in digits],
    'fifty', *[f'fifty {digit}' for digit in digits],
]

hours = ['twelve', *digits, 'ten', 'eleven']

starts = ['the time is', 'it is']

times = {}
for ampm in ['am', 'pm']:
    for hour, hour_name in enumerate(hours, (0 if ampm == 'am' else 12)):
        times[(hour, 0)] = f'{random.choice(starts)} {hour_name} {ampm}'
        for minute, digit in enumerate(digits, 1):
            times[(hour, minute)] = f'{random.choice(starts)} {digit} past {hour_name} {ampm}'
        for minute, minute_name in enumerate(from_ten, 10):
            times[(hour, minute)] = f'{random.choice(starts)} {hour_name} {minute_name} {ampm}'
        times[(hour, 15)] = f'{random.choice(starts)} quarter past {hour_name} {ampm}'

times[(4, 20)] = times[(16, 20)] = "it is four twenty blaze it"

time_words = [sentence.split(' ') for sentence in times.values()]

W, H = 22, 22

@dataclasses.dataclass
class Location:
    # x/y start, x/y end, x/y direction
    xs: int
    ys: int
    xe: int
    ye: int
    xd: int
    yd: int

    @property
    def length(self):
        return 1 + self.xe - self.xs + self.ye - self.ys

    @property
    def banned(self):
        rv = set()
        rv.add((self.xs, self.ys))
        
        # ban words immediately below a horizontal word (or next to vertical)
        for idx in range(self.length):
            if self.xd > 0:
                rv.add((self.xs + 1 * idx, self.ys + 1))
            else:
                rv.add((self.xs + 1, self.ys + 1 * idx))

        # ban immediate trailing words
        # @TODO: need to ban starting on last letter going same direction (but hard)
        #        ban both for now
        if self.xd > 0:
            rv.add((self.xs + self.length, self.ys))
            rv.add((self.xs + self.length - 1, self.ys))
        else:
            rv.add((self.xs, self.ys + self.length))
            rv.add((self.xs, self.ys + self.length - 1))

        return rv

class Grid(list):
    def __init__(self, backup=None):
        super().__init__(backup if backup else [[' '] * W for y in range(H)])

    def flip(self):
        self[:] = [list(reversed(line)) for line in reversed(self)]

    def used(self):
        return sum(sum(0 if letter == ' ' else 1 for  letter in line) for line in self)

    def search(self, x, y, word, banned, max_distance=None, insert_if_empty=False):
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
        
            distance_start = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2)
            distance_origin = math.sqrt((x - 0) ** 2 + (y - 0) ** 2)

            if max_distance and distance_start >= max_distance:
                return

            seen.add((x, y))
            heapq.heappush(priority_q, (distance_origin, x, y))


        def check(x, y, xd, yd):
            'Check if the position is valid for the word'
            for idx, letter in enumerate(word):
                grid_letter = self[y + idx * yd][x + idx * xd]
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
                            self[y + idx * yd][x + idx * xd] = letter
                    return Location(x, y, x + (len(word) - 1) * xd, y + (len(word) - 1) * yd, xd, yd)

            push(x + 1, y)
            push(x, y + 1)

        return None
    
    def insert(self, words):
        '''
        Try insert a set of words, return their locations
        '''
        x, y = 0, 0
        failed = False
        locations = []

        banned = set()
        failed = defaultdict(set)
        backups = []

        # with open('progress', 'a') as f:
        #     print(words, file=f)
        #     print(grid.render(), file=f)

        while len(locations) < len(words):
            idx = len(locations)
            word = words[len(locations)]
            found = False
            banned.update(failed[idx])

            assert len(backups) == len(locations)
            backup = deepcopy(self[:])

            # print(' '.join(words), '--', ' '.join(f'{l.xs}:{l.ys}' for l in locations), list(failed[idx]))
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
                found = self.search(x, y, word, banned, max_distance=max_distance, insert_if_empty=insert_if_empty)

                if found:
                    break

            # if we still haven't found anything, try on a new line
            if not found:
                found = self.search(0, y + len(words[idx - 1]), word, banned, insert_if_empty=True)

            if not found:
                try:
                    last = locations.pop()
                except IndexError:
                    return None

                try:
                    prev = locations[-1]
                except IndexError:
                    prev = Location(0,0,0,0,0,0)
                # print(x, y, words, word)
                # print(locations)
                before = self.used()
                # print(self.render())
                self[:] = backups.pop()
                if self.used() != before:
                    print(before, 'AFTER', self.used())
                # print(self.render())
                x = prev.xs
                y = prev.ys

                banned = set()
                for location in locations:
                    banned.update(location.banned)

                banned.add((last.xs, last.ys))
                failed[idx - 1].add((last.xs, last.ys))

                continue

            locations.append(found)
            backups.append(self[:])
            x, y, _, _, xd, yd = dataclasses.astuple(found)

            banned.update(found.banned)


        return locations

    def render(self, highlight=set()):
        output = ''
        def render(x, y, letter):
            if (x, y) in highlight:
                # apply a green highlight
                letter = '\033[1;32m' + letter + '\033[0m'
            return letter
            
        for y, line in enumerate(self):
            output += (''.join(
                render(x, y, letter)
                for x, letter in enumerate(line)
            ) + '\n')
        return output

    def fill(self):
        for x in range(W):
            for y in range(H):
                if self[x][y] == ' ':
                    self[x][y] = random.choice(string.ascii_lowercase)

inserted = 0
while inserted < len(times):
    locations = {}
    grid = Grid()

    random.shuffle(time_words)
    # Insert the first half of each phrase
    # print('Inserting first half')
    # for words in time_words:
    #     grid.insert(words[:len(words) // 2])

    # # Flip the board and insert the last half
    # print('Inserting reversed last half')
    # grid.flip()
    # for words in time_words:
    #     count = 1
    #     grid.insert(list(reversed(list(word[::-1] for word in words[-count:]))))
    # grid.flip()
    # print(grid.render())

    # Flip back and insert full phrases
    print('Inserting full phrases')
    grid.flip()
    random_time = None
    inserted = 0
    for time, sentence in times.items():
        locations[time] = grid.insert(sentence.split(' '))
        if not locations[time]:
            print(f'Failed after {inserted} of {len(times)} times [{W}x{H}]')
            break
        inserted += 1

print(f'Inserted {inserted} of {len(times)} times [{W}x{H}]')

# grid.fill()

time_highlight = {}
for time, letters in locations.items():
    highlight = set()
    for location in (letters or []):
        x, y, xe, ye, xd, yd = dataclasses.astuple(location)
        while x <= xe and y <= ye:
            highlight.add((x, y))
            (x, y) = x + xd, y + yd
    time_highlight[time] = highlight

with open('output.json', 'w') as f:
    json.dump({
        ('%02d:%02d' % time): list(highlight) for time, highlight in time_highlight.items()
    }, f, sort_keys=True) 
    f.write('\n')

for time, highlight in time_highlight.items():
    sys.stdout.write('\033[2J' + '%02d:%02d' % time + '\n' + grid.render(highlight))
    sys.stdout.flush()
    sleep(0.1)
