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

## Session resumed after TX battery charged

Mapped CH6 (byte5, tied to throttle's collective curve) and CH7 (byte6,
switch C, 3-position) — full detail in `notes.md`. User decided not to
chase the remaining switches (A,B,D,E,F,H, knobs) since Heli-X only needs
the 4 main stick axes.

Built `bridge.py` (evdev/uinput virtual joystick), verified clean with
`evtest` — all axes swept full range, no jumps.

## First live Heli-X test — found the axes were fundamentally wrong

User reported wrapping/multi-position behavior on every axis when
actually used in Heli-X's calibration screen. Root cause: the original
single-byte-per-axis mapping was wrong. Continuous full-range sweeps
(not just the earlier static endpoint samples) revealed each main axis
is really a 10-bit value: an 8-bit "fine" byte that sawtooths through
0-255 multiple times per physical stick throw, plus a 2-bit "coarse"
counter — and all four coarse counters turned out to be packed into a
single byte (byte3), one 2-bit field per axis. Found this by capturing
continuous sweeps per axis (`capture_elevator_sweep.bin`,
`capture_throttle_sweep.bin`, `capture_rudder_sweep.bin`,
`capture_aileron_sweep.bin`) and correlating wrap points against every
other byte's changes. Rewrote `bridge.py`'s decode function accordingly;
verified via evtest — zero jumps across all 4 axes.

## Second live Heli-X test — still wrapping, root-caused further

User reported: only 2 of 6 axes were even visible in Heli-X's
calibration UI at first ("z" and "5"), and one of them ("z") still
wrapped ~4 times per full sweep. Diagnosed in stages:

1. Extracted frames from the user's screencast videos (`gst-launch-1.0`,
   no ffmpeg available) to see Heli-X's actual UI, since I have no
   display/screenshot access.
2. Empirically identified which Heli-X UI label corresponded to which
   physical control by asking the user to move one control at a time.
3. Verified our own evdev output was clean via `evtest` (zero jumps) —
   ruled out our main-axis decode logic as the cause.
4. Found a stale Heli-X-cached profile (`~/TOOLS/HELI-X11/files/controller/ReflexRCBridge.xml`)
   with broken calibration constants and both "Pitch" and "Thrust"
   wrongly assigned to the same raw axis — user backed it up/deleted it
   themselves. Wrapping persisted even after a fresh profile.
5. Wrote `jstest.py` to read the older `/dev/input/jsN` joystick API
   directly (Heli-X's LWJGL/SDL stack likely uses this, not evdev
   directly) — found real jumps there even on data that was clean at
   the evdev level, on one specific axis.
6. Traced that axis back to the CH6 aux slot (byte5) and proved via raw
   capture analysis it's a genuine **hardware-level artifact**: byte5
   chaotically flaps between ~0 and 255 during rapid movement of an
   unrelated axis (aileron), even when the multiplex flag correctly
   indicates valid data. Not fixable in software.
7. Dropped CH6 from `bridge.py` entirely (it was redundant anyway —
   TX-computed from throttle). Kept CH7, which is clean across every
   sweep test. Also rate-limited bridge output to 60Hz along the way
   (didn't turn out to be the root cause, but reasonable to keep).
8. User reset the Heli-X profile once more and redid calibration.
   **Confirmed fully working.**

Background jobs started with plain `&`/`disown` in Bash did not survive
between tool calls in this environment — switched to the harness's
`run_in_background` mechanism for the long-running bridge process, which
does persist correctly.
