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
