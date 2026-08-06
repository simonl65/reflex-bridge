#!/usr/bin/env python3
"""Minimal /dev/input/jsN reader (the older joystick API), to check
whether it reports the same clean values as evdev, or if it has its own
rescaling bug. See https://www.kernel.org/doc/Documentation/input/joystick-api.txt

Usage: uv run jstest.py [/dev/input/jsN] [seconds]
"""

import os
import struct
import sys
import time

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

EVENT_FMT = "IhBB"
EVENT_SIZE = struct.calcsize(EVENT_FMT)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/input/js0"
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

    fd = os.open(path, os.O_RDONLY)
    deadline = time.time() + seconds
    last = {}
    minmax = {}
    jumps = {}
    try:
        while time.time() < deadline:
            data = os.read(fd, EVENT_SIZE)
            _, value, ev_type, number = struct.unpack(EVENT_FMT, data)
            kind = ev_type & ~JS_EVENT_INIT
            if kind == JS_EVENT_AXIS:
                prev = last.get(number)
                if prev is not None and abs(value - prev) > 15000:
                    jumps[number] = jumps.get(number, 0) + 1
                last[number] = value
                lo, hi = minmax.get(number, (value, value))
                minmax[number] = (min(lo, value), max(hi, value))
    finally:
        os.close(fd)

    for number in sorted(minmax):
        lo, hi = minmax[number]
        print(f"axis {number}: min={lo} max={hi} jumps={jumps.get(number, 0)}")


if __name__ == "__main__":
    main()
