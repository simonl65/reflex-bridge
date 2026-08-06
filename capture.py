#!/usr/bin/env python3
"""Capture raw hidraw reports for a fixed duration and print per-byte
statistics (min/max/unique values), plus save the raw reports to a file
for later comparison between two captures (e.g. idle vs. a control held).

Usage: uv run capture.py <label> [seconds] [/dev/hidrawN]
"""

import os
import sys
import time

DEFAULT_PATH = "/dev/hidraw6"


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run capture.py <label> [seconds] [/dev/hidrawN]")
        sys.exit(1)

    label = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PATH

    fd = os.open(path, os.O_RDONLY)
    reports = []
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            data = os.read(fd, 64)
            reports.append(data)
    finally:
        os.close(fd)

    out_path = f"capture_{label}.bin"
    with open(out_path, "wb") as f:
        for r in reports:
            f.write(len(r).to_bytes(1, "little"))
            f.write(r)

    n = len(reports)
    width = len(reports[0]) if reports else 0
    print(f"Captured {n} reports ({width} bytes each) -> {out_path}\n")

    print(f"{'byte':>4}  {'min':>4}  {'max':>4}  {'#uniq':>6}  values")
    for i in range(width):
        vals = [r[i] for r in reports if len(r) > i]
        uniq = sorted(set(vals))
        shown = ", ".join(f"{v:02x}" for v in uniq[:12])
        more = f" (+{len(uniq)-12} more)" if len(uniq) > 12 else ""
        print(f"{i:>4}  {min(vals):>4x}  {max(vals):>4x}  {len(uniq):>6}  {shown}{more}")


if __name__ == "__main__":
    main()
