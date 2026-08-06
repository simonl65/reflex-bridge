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

Leave it running in a terminal, then launch Heli-X and select "Reflex RC
Bridge" as the controller.
