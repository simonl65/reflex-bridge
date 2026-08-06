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
- mid:      byte3=0xaa byte4=~0x15 (combined ~43541)
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

## Main channel summary (confirmed)

| Channel | Byte(s) | Idle | Full deflection |
|---|---|---|---|
| Rudder/Yaw | byte0 | ~0x09-0x0c | ~0x73-0x75 |
| Elevator/Pitch | byte1 | ~0x0a-0x0c | ~0x72-0x75 |
| Aileron/Roll | byte2 | ~0x0d-0x0f | ~0xa6-0xa9 |
| Throttle | byte3:byte4 (BE 16-bit) | ~0xba,0x96-99 (~47767) | ~0x8a,0x74-78 (~35446), decreasing |

## Aux channels (bytes 5-7, multiplexed)

TBD — testing in progress.

## Byte mapping

| Channel | Byte offset | Width | Bit range | Idle/center | Min | Max | Notes |
|---|---|---|---|---|---|---|---|
| Throttle |  |  |  |  |  |  |  |
| Aileron/Roll |  |  |  |  |  |  |  |
| Elevator/Pitch |  |  |  |  |  |  |  |
| Rudder/Yaw |  |  |  |  |  |  |  |
| Aux 1 |  |  |  |  |  |  |  |
| Aux 2 |  |  |  |  |  |  |  |
| ... |  |  |  |  |  |  |  |
