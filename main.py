#!/bin/env python3
import argparse
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


parser = argparse.ArgumentParser()
parser.add_argument("size", help="width x height")
args = parser.parse_args()

try:
    W, H = map(int, args.size.split('x'))
except ValueError:
    parser.print_usage(file=sys.stderr)
    sys.exit(1)


ansi_clear = "\033[2J"

digits = [
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
]

past = [
    *digits,
    "quarter",
]
from_ten = [
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    *[f"twenty {digit}" for digit in digits],
    "thirty",
    *[f"thirty {digit}" for digit in digits],
    "forty",
    *[f"forty {digit}" for digit in digits],
    "fifty",
    *[f"fifty {digit}" for digit in digits],
]

hours = ["twelve", *digits, "ten", "eleven"]

starts = [""] # ["the time is", "it is"]

sentences = {}
for ampm in ["am", "pm"]:
    for hour, hour_name in enumerate(hours, (0 if ampm == "am" else 12)):
        sentences[(hour, 0)] = f"{random.choice(starts)} {hour_name}"
        for minute, digit in enumerate(digits, 1):
            sentences[
                (hour, minute)
            ] = f"{digit} past {hour_name}"
        for minute, minute_name in enumerate(from_ten, 10):
            sentences[
                (hour, minute)
            ] = f"{hour_name} {minute_name}"
        # sentences[(hour, 15)] = f"{random.choice(starts)} quarter past {hour_name} {ampm}"

#sentences[(4, 20)] = sentences[(16, 20)] = "it is four twenty blaze it"
#sentences[(13, 35)] = 'one thirty five reticulating splines'
#sentences[(0, 0)] = 'it is midnight'
#sentences[(12, 0)] = 'it is noon'

def insert_special(grid):
    '''
    This is called early on to make sure there is space in our grid for special words
    '''
    grid.insert(['past'], x=10, y=5)
    #grid.insert(['quarter', 'past'], x=5, y=5)
    #grid.insert(['reticulating', 'splines'], x=10, y=10)
    #grid.insert(['midnight'], x=6, y=6)
    #grid.insert(['noon'], x=16, y=8)
    #grid.insert(['blaze', 'it'], x=9, y=15)

def insert_reversed(grid):
    'Once the grid is flipped'
    #for digit in digits:
    #    grid.insert([digit, "pm"], reverse=True)
    #    grid.insert([digit, "am"], reverse=True)

times = list(sentences.keys())


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
        super().__init__(backup if backup else [[" "] * W for y in range(H)])

    def flip(self):
        self[:] = [list(reversed(line)) for line in reversed(self)]

    def used(self):
        return sum(sum(0 if letter == " " else 1 for letter in line) for line in self)

    def search(self, x, y, word, banned, max_distance=None, insert_if_empty=False):
        """
        Search for a word in the grid.
        Returns end position (x, y) and (xd, yd) direction vector
        """
        start_x, start_y = x, y
        priority_q = []
        seen = set()

        def push(x, y):
            """
            Push item to heaped priority queue, with priority as distance from origin
            """
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
            "Check if the position is valid for the word"
            for idx, letter in enumerate(word):
                grid_letter = self[y + idx * yd][x + idx * xd]
                if grid_letter != letter and not (
                    insert_if_empty and grid_letter == " "
                ):
                    return False
            return True

        push(x, y)
        while priority_q:
            (distance, x, y) = heapq.heappop(priority_q)

            directions = ([(+1, 0)] if x + len(word) <= W else []) + (
                [(0, +1)] if y + len(word) <= H else []
            )
            random.shuffle(directions)

            for (xd, yd) in directions:
                if check(x, y, xd, yd):
                    if insert_if_empty:
                        for idx, letter in enumerate(word):
                            self[y + idx * yd][x + idx * xd] = letter
                    return Location(
                        x, y, x + (len(word) - 1) * xd, y + (len(word) - 1) * yd, xd, yd
                    )

            push(x + 1, y)
            push(x, y + 1)

        return None

    def insert(self, words, x=0, y=0, reverse=False):
        """
        Try insert a set of words, return their locations
        """
        locations = []

        banned = set()
        failed = defaultdict(set)
        backups = []

        if reverse:
            words = list(reversed(list(word[::-1] for word in words)))

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
                (10, False),
                (3, True),
                (15, False),
                (5, True),
                (20, False),
                (10, True),
                (None, False),
                (None, True),
            ]
            if idx == len(words) - 1:
                search_configs = [(None, False), (None, True)]

            for (max_distance, insert_if_empty) in search_configs:
                found = self.search(
                    x,
                    y,
                    word,
                    banned,
                    max_distance=max_distance,
                    insert_if_empty=insert_if_empty,
                )

                if found:
                    break

            # if we still haven't found anything, try on a new line
            if not found:
                found = self.search(
                    0, y + len(words[idx - 1]), word, banned, insert_if_empty=True
                )

            if not found:
                try:
                    last = locations.pop()
                except IndexError:
                    return None

                try:
                    prev = locations[-1]
                except IndexError:
                    prev = Location(0, 0, 0, 0, 0, 0)

                self[:] = backups.pop()
                x = prev.xs
                y = prev.ys

                banned = set()
                for location in locations:
                    banned.update(location.banned)
                failed[idx - 1].add((last.xs, last.ys))

                continue

            locations.append(found)
            backups.append(backup)
            x, y = found.xs, found.ys

            banned.update(found.banned)

        return locations

    def render(self, highlight=set()):
        output = ""

        def render(x, y, letter):
            if (x, y) in highlight:
                # apply a green highlight
                letter = "\033[1;32m" + letter + "\033[0m"
            return letter

        for y, line in enumerate(self):
            output += (
                "".join(render(x, y, letter) for x, letter in enumerate(line)) + "\n"
            )
        return output

    def fill(self):
        for x in range(W):
            for y in range(H):
                if self[y][x] == " ":
                    self[y][x] = random.choice(string.ascii_lowercase)

    def display(self, text, highlight=set()):
        sys.stderr.write(
            ansi_clear + text + "\n" +             '=' * W + "\n" + self.render(highlight)
        )
        sys.stderr.flush()

inserted = 0
best = 0


prefix_count = defaultdict(int)
for sentence in sentences.values():
    words = sentence.split(' ')
    for idx in range(len(words)):
        prefix_count[tuple(words[:idx+1])] += 1

def sort_key(sentence):
    words = sentence.split(' ')
    return [
        prefix_count[tuple(words[:idx + 1])] for idx in range(len(words))
    ]


sys.stderr.write(ansi_clear)

while inserted < len(times):
    locations = {}
    grid = Grid()

    # sort times by how often we see their prefices
    times.sort(key=lambda time: sort_key(sentences[time]), reverse=True)

    insert_special(grid)

    # Insert the first half of each phrase
    # print('Inserting first half')
    # for words in time_words:
    #     grid.insert(words[:len(words) // 2])

    # # Flip the board and insert the last half
    # print('Inserting reversed last half')
    grid.flip()
    insert_reversed(grid)
    grid.flip()
    # print(grid.render())

    # Flip back and insert full phrases
    # print("Inserting full phrases")
    random_time = None
    inserted = 0

    for time in times:
        locations[time] = grid.insert(sentences[time].split(' '))
        if not locations[time]:
            if inserted > best:
                best = inserted
                grid.display(
                    f"Best attempt so far {inserted}/{len(times)} [{math.floor(100*inserted/len(times))}% of {W}x{H}]"
                )
            break
        inserted += 1

grid.display("Success!")
grid.fill()

time_highlight = {}
for time, letters in sorted(locations.items()):
    highlight = set()
    for location in letters or []:
        x, y, xe, ye, xd, yd = dataclasses.astuple(location)
        while x <= xe and y <= ye:
            highlight.add((x, y))
            (x, y) = x + xd, y + yd
    time_highlight[time] = highlight

json.dump(
    {
        ("%02d:%02d" % time): list(highlight)
        for time, highlight in time_highlight.items()
    },
    sys.stdout,
    sort_keys=True,
)
sys.stdout.write("\n")
sys.stdout.flush()

for time, highlight in time_highlight.items():
    grid.display("%02d:%02d" % time, highlight)
    sys.stderr.flush()
    sleep(0.25)
