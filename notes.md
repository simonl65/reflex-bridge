# Reflex RC-controller Interface — protocol notes

Device: `0b9b:4012`, `hid-generic` driver, exposed as `/dev/hidrawN`.

## Report descriptor

(paste `sniff.py` output here once captured)

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
