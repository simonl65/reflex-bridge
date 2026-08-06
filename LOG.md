# Session log — commands and instructions

Running log of every shell command executed and every instruction given to
the user, in order. Kept per user request so the whole session is auditable.

## Device discovery (read-only)

```
lsusb
```
→ Found `Bus 003 Device 013: ID 0b9b:4012 Dipl.-Ing. Stefan Kunde Reflex RC-controller Interface`

```
ls -la /dev/hidraw*
cat /sys/class/hidraw/hidraw6/device/uevent
```
→ Confirmed dongle is `/dev/hidraw6`, driver `hid-generic`, `HID_ID=0003:00000B9B:00004012`.

```
python3 --version
python3 -c "import evdev"
python3 -c "import hid"
pip3 list | grep -iE "hid|evdev|uinput"
lsmod | grep -iE "uinput|hid"
ls -la /dev/uinput
groups
ls /etc/udev/rules.d/
which heli-x
find / -iname "*heli-x*" -maxdepth 4
```
→ Neither `evdev` nor `hid` python modules installed yet. `uinput` kernel module present. User in `plugdev` group. No existing udev rules for this device. Heli-X found at `~/Desktop/HELI-X` → `~/Downloads/HELI-X11/runHELI-X.sh`.

```
ls -la /home/simon/Desktop/HELI-X
find /home/simon/Desktop/HELI-X -iname "*joystick*" -o -iname "*config*"
ls -la /home/simon/Downloads/HELI-X11
```
→ Heli-X is the LWJGL/Java build; no joystick config files found by name (likely uses SDL joystick enumeration at runtime, not static config files).

```
cat /dev/hidraw6 > /dev/null   # attempted as normal user, before udev rule
sudo -n true                    # checked for passwordless sudo
```
→ Confirmed we did NOT have read access yet, and sudo requires an interactive password (so udev rule install had to be done by the user, not me).

Web searches (read-only, no local system changes): searched for existing public documentation of the `0b9b:4012` byte protocol — found none. Confirmed via search that hidraw is the right approach and that the device is Reflex-XTR-family.

## Project scaffolding

User ran `uv init .` themselves in `/home/simon/Documents/_ELECTRONICS/reflex-bridge` (created `pyproject.toml`, `main.py`, `.venv`, `.python-version`, `.gitignore`, `README.md`, and a git repo on branch `develop`, with an initial commit).

```
uv add evdev
```
→ Installed `evdev==1.9.3` into the project's `.venv`.

Files created by me:
- `99-reflex-rc.rules` — udev rule granting `plugdev` group access to `/dev/hidraw*` for `0b9b:4012`, and to `/dev/uinput`.
- `README.md` — setup/usage instructions (see below for the exact install commands given to the user).
- `sniff.py` — raw hidraw report dumper for protocol reverse-engineering.
- `notes.md` — template table for recording the byte-to-channel mapping.

```
uv run python -m py_compile sniff.py   # syntax check only, no execution against hardware
rm -f main.py                           # removed the uv-init placeholder entrypoint
git add -A
git commit -m "Add udev rule, sniff.py, and notes template for protocol RE"
git commit --amend -m "Add udev rule, sniff.py, and notes template for protocol RE"   # removed an accidental Co-Authored-By line from the first attempt, per user's global CLAUDE.md preference
```

## Instructions given to the user (commands they ran themselves)

**udev rule install** (I'm not allowed to run `sudo` — auto-mode classifier blocks it — so this was always meant to be run by the user):

```sh
sudo cp /home/simon/Documents/_ELECTRONICS/reflex-bridge/99-reflex-rc.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then: unplug and replug the dongle.

User confirmed this was done. Verification (read-only, run by me):

```
ls -la /etc/udev/rules.d/99-reflex-rc.rules
ls -la /dev/hidraw6
ls -la /dev/uinput
groups
```
→ `/dev/hidraw6` is now `crw-rw---- root plugdev` — correct, user can read it.
→ `/dev/uinput` is still `crw------- root root` — the `KERNEL=="uinput"` rule line didn't take effect via `udevadm trigger` (uinput is a static `misc` class device, `udevadm trigger` without a subsystem match doesn't always re-evaluate it).

User ran:

```sh
sudo udevadm trigger --subsystem-match=misc
```

Verification (read-only):

```
ls -la /dev/uinput /dev/hidraw6
```
→ Both now `crw-rw---- root plugdev`. Permissions fully in place, no root needed for the bridge going forward.

## Protocol reverse-engineering (interactive, read-only hardware access)

Fixed a bug in `sniff.py`'s HID report-descriptor ioctl (`fcntl.ioctl` "string arg too long" — Python's ioctl helper has a ~1024-byte immutable-buffer limit; fixed by sizing the descriptor buffer to the actual reported size and using a mutable `bytearray`). Report descriptor itself still isn't readable (`Errno 22 Invalid argument`) — not blocking, raw report reads work fine without it.

Wrote `capture.py` — captures N seconds of raw reports, saves to `capture_<label>.bin`, prints per-byte min/max/unique-value stats. Used repeatedly as: `uv run capture.py <label> <seconds>`, reading `/dev/hidraw6` directly (default path in the script).

Session sequence (each preceded by asking the user to position a specific control and confirm "ready"):
1. `capture_idle1` — hands off, throttle low (baseline)
2. `capture_throttle_high` — throttle full up
3. `capture_throttle_mid` — throttle mid
4. `capture_roll_right` — aileron/roll full right
5. `capture_pitch_fwd` — elevator/pitch full forward
6. `capture_yaw_side` — rudder/yaw full to one side (revealed throttle/rudder gimbal coupling — expected on this Mode 2 TX where throttle+rudder share one physical stick)
7. `capture_idle2` — hands off again, confirmed throttle returned to the same idle value as `idle1`, validating the mapping

Result: mapped rudder=byte0, pitch=byte1, roll=byte2, throttle=byte3:byte4 (big-endian 16-bit). Full detail and byte ranges recorded in `notes.md`. All of this is committed to git incrementally (see `git log`).

Started aux-channel mapping (bytes 5-7, a multiplexed pair selected by a byte-7 flag) but **paused 2026-08-06**: user's Futaba T9CP transmitter battery went flat mid-session and is now charging. User provided the TX's switch inventory (A-H, mostly 2-position, C/E 3-position, H momentary) and noted all switches are currently in "UP" position — recorded in `notes.md`. No commands were run against the hardware after this point; nothing else changed.

**To resume**: re-establish a clean "all switches UP" baseline capture once the TX is charged, then test each switch (A-H) individually the same way the stick axes were tested, to map each into the byte5-7 multiplex slots.
