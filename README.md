# reflex-bridge

Userspace bridge that turns a Dipl.-Ing. Stefan Kunde "Reflex RC-controller
Interface" dongle (USB `0b9b:4012`, an old Reflex XTR-family device with no
onboard mode button, permanently locked to a proprietary HID report format)
into a standard virtual joystick via Linux `uinput`, so Heli-X (and anything
else that reads joysticks via SDL/evdev) can see it.

## One-time setup

1. Install the udev rule so your user can read the hidraw device and create
   uinput devices without root:

   ```sh
   sudo cp 99-reflex-rc.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

   Unplug and replug the dongle after this so the new permissions apply.
   You must be in the `plugdev` group (`groups` to check).

2. Install dependencies:

   ```sh
   uv sync
   ```

## Usage

Find which `/dev/hidrawN` the dongle is on (it may move around depending on
plug order):

```sh
grep -l "0b9b" /sys/class/hidraw/*/device/uevent 2>/dev/null
```

Reverse-engineering the protocol (only needed once, results recorded in
`notes.md`):

```sh
uv run sniff.py
```

Running the bridge:

```sh
uv run bridge.py
```

If that command doesn't work try:

```bash
uv run python -u bridge.py /dev/hidraw6
```

Leave it running in a terminal, then launch Heli-X and select "Reflex RC
Bridge" as the controller. In Heli-X's Stick Configuration screen, sweep
each stick through its full range, then assign functions (Aileron,
Elevator, Rudder, Thrust) to the detected axes — do this fresh any time
the bridge's axis set changes, since Heli-X caches calibration per axis
layout in `files/controller/ReflexRCBridge.xml` and stale entries can
cause visibly broken (wrapping) behavior.

Exposed axes: aileron/roll, elevator/pitch, rudder/yaw, throttle, and one
aux channel (CH7, driven by transmitter switch C). See `notes.md` for the
full protocol writeup, including why a second aux channel (CH6) was
deliberately left out (hardware-level glitch, not fixable in software).

## Running automatically (systemd --user service)

To have the bridge start automatically at login instead of running it
manually each time:

```sh
mkdir -p ~/.config/systemd/user
cp reflex-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now reflex-bridge.service
```

Check it's running and see logs:

```sh
systemctl --user status reflex-bridge.service
journalctl --user -u reflex-bridge.service -f
```

It only runs while you're logged in (no lingering enabled), which is fine
since Heli-X is a desktop app anyway. The bridge already retries opening
the hidraw device if it's not present yet, so it's safe to enable this
even before plugging the dongle in, and it'll pick it up whenever you do.

To stop using it:

```sh
systemctl --user disable --now reflex-bridge.service
```

## Diagnostics

- `uv run sniff.py` — dump raw hidraw reports for protocol work
- `uv run capture.py <label> <seconds>` — capture + per-byte stats, saved
  to `capture_<label>.bin`
- `uv run jstest.py [/dev/input/jsN] [seconds]` — read the older joystick
  API directly (useful if evdev looks clean but something downstream,
  like Heli-X, doesn't)
