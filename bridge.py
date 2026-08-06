#!/usr/bin/env python3
"""Bridge the Reflex RC-controller Interface (0b9b:4012) to a virtual
uinput joystick that Heli-X (or anything else reading /dev/input/jsN or
evdev) can see.

Report layout (8 bytes), reverse-engineered in notes.md. Each main axis is
a 10-bit value split into an 8-bit "fine" byte plus a 2-bit "coarse"
counter packed into byte3:
  byte0            rudder/yaw fine byte;    coarse = byte3 bits[7:6] (x64)
  byte1            elevator/pitch fine byte; coarse = byte3 bits[3:2] (x4)
  byte2            aileron/roll fine byte;   coarse = byte3 bits[1:0] (x1)
  byte4            throttle fine byte;       coarse = byte3 bits[5:4] (x16)
  byte5/byte6      multiplexed aux pair, selected by byte7's high nibble:
                     0x80/0xa0/0xb0 -> byte5 = CH6 pitch curve (tied to
                       throttle, not independently useful for a sim)
                     0xd0/0xe0/0xf0 -> byte6 = CH7 (switch C, 3-position)

Raw values are passed straight through as absolute axes; use Heli-X's own
joystick calibration screen to set centers/endpoints/reversal, same as any
other joystick.

Usage: uv run bridge.py [/dev/hidrawN]
"""

import glob
import os
import sys
import time

from evdev import AbsInfo, UInput, ecodes

VENDOR_ID = 0x0B9B
PRODUCT_ID = 0x4012

AXIS_ROLL = ecodes.ABS_X
AXIS_PITCH = ecodes.ABS_Y
AXIS_YAW = ecodes.ABS_RZ
AXIS_THROTTLE = ecodes.ABS_THROTTLE
AXIS_AUX_PITCH_CURVE = ecodes.ABS_RX
AXIS_AUX_CH7 = ecodes.ABS_RY

CAPABILITIES = {
    ecodes.EV_ABS: [
        (AXIS_ROLL, AbsInfo(value=0, min=0, max=1023, fuzz=0, flat=0, resolution=0)),
        (AXIS_PITCH, AbsInfo(value=0, min=0, max=1023, fuzz=0, flat=0, resolution=0)),
        (AXIS_YAW, AbsInfo(value=0, min=0, max=1023, fuzz=0, flat=0, resolution=0)),
        (AXIS_THROTTLE, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        (AXIS_AUX_PITCH_CURVE, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        (AXIS_AUX_CH7, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
    ]
}


def find_device():
    for uevent_path in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        with open(uevent_path) as f:
            content = f.read().upper()
        if f"{VENDOR_ID:04X}" in content and f"{PRODUCT_ID:04X}" in content:
            return f"/dev/{uevent_path.split('/')[4]}"
    return None


def decode(report, state):
    coarse = report[3]
    state[AXIS_YAW] = ((coarse >> 6) & 0x3) << 8 | report[0]
    state[AXIS_THROTTLE] = (((coarse >> 4) & 0x3) << 8 | report[4]) >> 2
    state[AXIS_PITCH] = ((coarse >> 2) & 0x3) << 8 | report[1]
    state[AXIS_ROLL] = (coarse & 0x3) << 8 | report[2]

    slot = report[7] & 0xF0
    if slot in (0x80, 0xA0, 0xB0):
        state[AXIS_AUX_PITCH_CURVE] = report[5]
    elif slot in (0xD0, 0xE0, 0xF0):
        state[AXIS_AUX_CH7] = report[6]


def run(path):
    ui = UInput(CAPABILITIES, name="Reflex RC Bridge")
    print(f"Virtual joystick created: {ui.device.path}")

    state = {}
    last_sent = {}
    last_emit = 0.0
    min_interval = 1.0 / 60  # cap output rate to avoid overflowing joydev's event queue
    try:
        while True:
            try:
                fd = os.open(path, os.O_RDONLY)
            except FileNotFoundError:
                print(f"Waiting for {path}...")
                time.sleep(1)
                continue

            print(f"Reading from {path}")
            try:
                while True:
                    report = os.read(fd, 64)
                    if len(report) < 8:
                        continue
                    decode(report, state)

                    now = time.monotonic()
                    if now - last_emit < min_interval:
                        continue
                    last_emit = now

                    changed = False
                    for axis, value in state.items():
                        if last_sent.get(axis) != value:
                            ui.write(ecodes.EV_ABS, axis, value)
                            last_sent[axis] = value
                            changed = True
                    if changed:
                        ui.syn()
            except OSError as e:
                print(f"Device error ({e}), reconnecting...")
            finally:
                os.close(fd)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        ui.close()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_device()
    if path is None:
        print(f"No hidraw device found for {VENDOR_ID:04x}:{PRODUCT_ID:04x}")
        sys.exit(1)
    run(path)


if __name__ == "__main__":
    main()
