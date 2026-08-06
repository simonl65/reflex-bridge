# Reflex RC-controller Interface — protocol notes

Device: `0b9b:4012`, `hid-generic` driver, exposed as `/dev/hidrawN`.

## Report descriptor

(paste `sniff.py` output here once captured)

## Report structure

8-byte reports. Bytes 5,6,7 are a multiplexed pair: byte7 is a 2-valued flag
(`0xe8` or `0xa8/a9/ab`-ish) that alternates roughly every other report;
bytes 5-6 carry a different aux channel's value depending on which flag is
set. Bytes 0-4 are present identically regardless of the flag.

Throttle = big-endian 16-bit value across **byte3 (high) : byte4 (low)**,
decreasing as throttle increases:

- idle/low: byte3=0xba byte4=~0x97 (combined ~47767)
- mid: byte3=0xaa byte4=~0x15 (combined ~43541)
- full-high: byte3=0x8a byte4=~0x76 (combined ~35446)

Bytes 0-2 are NOT throttle (stayed in idle jitter cluster 0x09-0x0f across
all three throttle tests) — likely other analog channels at rest.

Aileron/Roll = **byte2**, single byte, ~0-255 range: idle/center ~0x0d-0x0f
(13-15), full-right ~0xa6-0xa9 (166-169). Increases moving right.

Elevator/Pitch = **byte1**, single byte, idle/center ~0x0a-0x0c (10-12),
full-forward ~0x72-0x75 (114-117). Increases moving forward (nose down).

Rudder/Yaw = **byte0**, single byte, idle/center ~0x09-0x0c (9-12),
full-side ~0x73-0x75 (115-117). Same scale as pitch.

NOTE: during the yaw test, bytes 3-4 (throttle) read very differently
(~0x1a,0xf5 -> combined ~6901) than the "mid" throttle test (~43541), even
though only rudder was touched. Suspect Mode 2 gimbal: throttle (vertical)
and rudder (horizontal) share one physical stick, and it may be spring-
centered rather than ratcheted, so gripping it to move rudder also
disturbed the throttle axis. Needs a clean hands-off retest to confirm
throttle returns to a consistent idle value.

CONFIRMED: clean hands-off retest (idle2) shows byte3=0xba, byte4=0x96-0x9a,
matching idle1 exactly. Throttle/rudder gimbal-coupling theory confirmed —
mapping is correct, the yaw-test anomaly was expected physical coupling,
not a protocol misunderstanding.

## Main channel summary — SUPERSEDED, see "10-bit coarse+fine encoding" below

The single-byte mapping below turned out to be wrong: each main axis is
actually a 10-bit value (fine byte + a 2-bit coarse counter packed into
byte3), not a plain 0-255 byte. Discovered when live-testing in Heli-X
showed wrapping/sawtooth behavior on every axis. Kept here for history.

| Channel        | Byte(s)                 | Idle                   | Full deflection                    |
| -------------- | ----------------------- | ---------------------- | ---------------------------------- |
| Rudder/Yaw     | byte0                   | ~0x09-0x0c             | ~0x73-0x75                         |
| Elevator/Pitch | byte1                   | ~0x0a-0x0c             | ~0x72-0x75                         |
| Aileron/Roll   | byte2                   | ~0x0d-0x0f             | ~0xa6-0xa9                         |
| Throttle       | byte3:byte4 (BE 16-bit) | ~0xba,0x96-99 (~47767) | ~0x8a,0x74-78 (~35446), decreasing |

## 10-bit coarse+fine encoding (CORRECT mapping)

Continuous full-range sweeps (not just static endpoint samples) revealed
each main axis's "fine" byte is a sawtooth that wraps through 0-255
multiple times across one physical stick throw — a 2-bit "coarse" counter
elsewhere increments/decrements by a fixed step each time the fine byte
wraps. All four coarse counters are packed into **byte3**:

| Axis     | Fine byte | Coarse bits in byte3 | Coarse step (weight) |
| -------- | --------- | -------------------- | -------------------- |
| Rudder   | byte0     | bits[7:6]            | 64                   |
| Throttle | byte4     | bits[5:4]            | 16                   |
| Elevator | byte1     | bits[3:2]            | 4                    |
| Aileron  | byte2     | bits[1:0]            | 1                    |

Combined 10-bit value per axis: `(coarse_2bit << 8) | fine_byte`, range
0-1023. E.g. rudder = `((byte3 >> 6) & 0x3) << 8 | byte0`.

Confirmed via continuous ~10s sweeps for all 4 axes: elevator
(`capture_elevator_sweep.bin`), throttle (`capture_throttle_sweep.bin`),
rudder (`capture_rudder_sweep.bin`), aileron (`capture_aileron_sweep.bin`)
— in each, only that axis's fine byte swept 0-255 with multiple wraps,
and only its assigned 2-bit field in byte3 changed, by exactly the
predicted weight, while the other three fields in byte3 stayed constant.

This also means the earlier "throttle = byte3:byte4 combined 16-bit"
theory was a coincidence — byte3's throttle-correlated changes were real,
but the correct combination is `(bits[5:4]<<8)|byte4`, not a straight
16-bit big-endian pair.

## Transmitter: Futaba T9CP, helicopter mode

9-channel transmitter. Switch inventory:

| Switch | Positions | Notes / Heli Assignments |
| ------ | --------- | ------------------------ |
| A      | 2         | Elevator Dual Rate       |
| B      | 2         | Rudder Dual Rate / CH9   |
| C      | 3         | CH 7                     |
| D      | 2         | Aileron Dual Rate        |
| E      | 3         | Idle-up 1/2              |
| F      | 2         | Idle-up 3 / CH5          |
| G      | 2         | fwd = Throttle Hold      |
| H      | 2         | momentary (non-latching) |
| Knob A | Variable  | Hovering Pitch           |
| Knob B | Variable  | CH8                      |
| Knob C | Variable  | Hovering Throttle        |

As of 2026-08-06, all switches are in the "UP" position (some had been
mistakenly in other positions during earlier testing — main-channel
readings above were NOT affected since they only measured stick axes).
Which switch corresponds to which logical aux channel (or which TX mixing
output) is not yet known — TX-side switch assignment doesn't necessarily
map 1:1 to raw channel bytes, since T9CP mixing can combine switches into
channels in helicopter mode (e.g. gyro gain, governor, throttle hold,
idle-up/pitch curve selection). Will need to test switches one at a time
once the transmitter is charged and confirm against bytes 5-7.

Receiver Channel Assignments:
CH1: Aileron
CH2: Elevator
CH3: Throttle
CH4: Rubber
CH5: Gyro Sensitivity
CH6: Pitch
CH7: Spare
CH8: Spare

## Aux channels (bytes 5-7, multiplexed)

Confirmed: only 2 aux slots are transmitted, distinguished by `byte7`'s
high nibble. `byte7`'s low bits/exact value jitter a bit within a slot
(not meaningful, some kind of counter/checksum noise) — group by
`byte7 & 0xf0` to isolate the two slots reliably.

- **Slot A** (`byte7 & 0xf0` in `{0x80,0xa0,0xb0}`): value in **byte5**.
  This is **CH6 Pitch** (collective curve) — tracks throttle almost 1:1
  (idle-low throttle ~0x8d-0x90, mid ~0x15-0x18, full-high ~0x00-0x01).
  Switch G (Throttle Hold) overrides it to max (~0xfe-0xff) along with
  overriding throttle itself. Knob A (Hovering Pitch) and switch E
  (idle-up) showed no effect at zero-throttle (curve endpoints are fixed;
  Knob A only moves the curve's midpoint, not visible at the throttle
  extremes tested). `byte6` within slot A is NOT meaningful data — it
  drifted between sessions (0xd3-d5 vs 0x55-57) with no correlation to any
  control tested; likely counter/noise, ignore it.

- **Slot B** (`byte7 & 0xf0` in `{0xd0,0xe0,0xf0}`): value in **byte6**.
  This is **CH7**, controlled by **switch C** (3-position):
  - up (pos 1): byte6 ~0x00-0x01
  - middle (pos 2): byte6 ~0x0d-0x0f
  - down (pos 3): byte6 ~0xfe-0xff (unevenly spaced — this is a raw
    3-position switch output, not a smooth analog range)
    `byte5` within slot B stays ~0x00-0x01 constant — not meaningful data.

UPDATE: live testing in Heli-X showed wrapping that traced back to slot A
(CH6/byte5) specifically. Raw capture analysis of `capture_aileron_sweep.bin`
proved it's a genuine hardware-level artifact, not a decode bug: byte5
chaotically flaps between ~0 and 255 during rapid movement of AILERON (an
unrelated axis) even while byte7's flag correctly indicates "slot A".
CH7 (slot B/byte6) shows zero such artifacts across every sweep test.
**Decision: byte5/CH6 is dropped from bridge.py entirely** — it's not
fixable in software, and it's redundant anyway (TX-computed from
throttle, not independently useful for a sim). Only CH7 (byte6) is used.

Ruled out (no effect on either slot, at least at the settings tested):
switch E (idle-up), Knob A (Hovering Pitch) at zero throttle, Knob B
(CH8 — matches "CH8: Spare" on the receiver, likely genuinely unused).

CH5 (Gyro Sensitivity) and CH8 have not been found in the raw stream —
may not be transmitted at all (only 2 aux slots exist total), or may need
a control not yet tested (switches A, B, D, F, H; Knob C).

## Byte mapping

| Channel        | Byte offset | Width | Bit range | Idle/center | Min | Max | Notes |
| -------------- | ----------- | ----- | --------- | ----------- | --- | --- | ----- |
| Throttle       |             |       |           |             |     |     |       |
| Aileron/Roll   |             |       |           |             |     |     |       |
| Elevator/Pitch |             |       |           |             |     |     |       |
| Rudder/Yaw     |             |       |           |             |     |     |       |
| Aux 1          |             |       |           |             |     |     |       |
| Aux 2          |             |       |           |             |     |     |       |
| ...            |             |       |           |             |     |     |       |
