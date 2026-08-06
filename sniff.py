#!/usr/bin/env python3
"""Dump raw HID reports from the Reflex RC-controller dongle for protocol
reverse-engineering. Move one control at a time and watch which byte(s)
change.

Usage: uv run sniff.py [/dev/hidrawN]
"""

import fcntl
import glob
import os
import struct
import sys
import time

VENDOR_ID = 0x0B9B
PRODUCT_ID = 0x4012

_IOC_READ = 2
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = 8
_IOC_SIZESHIFT = 16
_IOC_DIRSHIFT = 30


def _ior(type_char, nr, size):
    return (
        (_IOC_READ << _IOC_DIRSHIFT)
        | (ord(type_char) << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )


HIDIOCGRDESCSIZE = _ior("H", 0x01, 4)
HIDIOCGRDESC = _ior("H", 0x02, 4 + 4096)
HIDIOCGRAWNAME_256 = (2 << 30) | (ord("H") << 8) | 0x04 | (256 << 16)


def find_device():
    for uevent_path in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        with open(uevent_path) as f:
            content = f.read()
        if f"{VENDOR_ID:04X}" in content.upper() and f"{PRODUCT_ID:04X}" in content.upper():
            hidraw_name = uevent_path.split("/")[4]
            return f"/dev/{hidraw_name}"
    return None


def dump_report_descriptor(fd):
    try:
        size_buf = fcntl.ioctl(fd, HIDIOCGRDESCSIZE, struct.pack("i", 0))
        (size,) = struct.unpack("i", size_buf)
        buf = struct.pack("i", size) + b"\x00" * 4096
        desc_buf = fcntl.ioctl(fd, HIDIOCGRDESC, buf)
        (rsize,) = struct.unpack("i", desc_buf[:4])
        report_bytes = desc_buf[4 : 4 + rsize]
        print(f"Report descriptor ({rsize} bytes):")
        print(" ".join(f"{b:02x}" for b in report_bytes))
        print()
    except OSError as e:
        print(f"Couldn't read report descriptor: {e}")


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = find_device()
        if path is None:
            print(f"No hidraw device found for {VENDOR_ID:04x}:{PRODUCT_ID:04x}")
            print("Pass the device path explicitly, e.g. uv run sniff.py /dev/hidraw6")
            sys.exit(1)

    print(f"Opening {path}")
    fd = os.open(path, os.O_RDONLY)

    dump_report_descriptor(fd)

    print("Reading reports. Move one control at a time. Ctrl-C to stop.\n")

    last = None
    try:
        while True:
            data = os.read(fd, 64)
            now = time.strftime("%H:%M:%S")
            hexstr = " ".join(f"{b:02x}" for b in data)
            if last is not None and len(last) == len(data):
                diff_positions = [i for i, (a, b) in enumerate(zip(last, data)) if a != b]
                if diff_positions:
                    diff_str = ",".join(str(i) for i in diff_positions)
                    print(f"[{now}] {hexstr}   (changed bytes: {diff_str})")
            else:
                print(f"[{now}] {hexstr}   (first report, len={len(data)})")
            last = data
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
