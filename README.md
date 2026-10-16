# AlfaCode

Decoder for Alfa Romeo immobiliser transponder dumps. Given a transponder
record it recovers the **PIN** and verifies the two **checksum** bytes, from
either a raw hex line or a `.bin` memory dump.

## Background

The immobiliser control unit (e.g. unit `60622718`) stores its keys in an
EEPROM. There are **eight memory positions for keys**, each holding one
transponder record. The records come in two roles:

- **Master key** — the programming key, able to enrol further keys.
- **Slave key** — an ordinary driving key.

Every record begins with the fixed transponder header `80 21 2C`. A raw EEPROM
dump of the unit therefore contains several of these records (often with a `0F`
length marker in front and `00` padding after each). Reading a key's record
out of that dump gives you the five key bytes this tool needs.

## Usage

```bash
# Decode a hex dump line
python3 alfacode.py "80 21 2C E6 11 4A 41 6D 9C 63"

# Scan a .bin file (finds every record, skips 0F markers and padding)
python3 alfacode.py "example master key.bin"

# No argument: read a hex line from stdin
echo "80 21 2C E6 11 4A 41 6D 9C 63" | python3 alfacode.py
```

Output:

```
  PIN/AlfaCode : 14164
  key bytes   : E6 11 4A 41 6D
  checksum    : 9C 63
  status      : checksum VALID
```

If the argument is an existing file it is read as binary; otherwise it is
treated as a hex string. Non-hex characters (spaces, newlines) are ignored, so
you can paste a record with or without separators.

## Record format

Each record is the fixed header `80 21 2C` followed by:

| bytes | meaning |
|-------|---------|
| 5     | key bytes |
| 2     | checksum (optional in a hex line) |

In a `.bin` dump this record is often preceded by a `0F` length marker and
followed by `00` padding; the scanner locates records by the `80 21 2C`
signature, so those extra bytes are ignored. Identical records (a key stored in
several memory slots) are reported once.

## PIN algorithm

The PIN comes from the **last 5 nibbles** of the 5 key bytes, one nibble per
digit, mapped as:

1. Convert the nibble to decimal.
2. If the value is greater than 9, subtract 9.
3. If the value is 0, add 7.

Every digit ends up in the range 1–9. The full map:

| nibble | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
|--------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| digit  | 7 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 1 | 2 | 3 | 4 | 5 | 6 |

Example — key `E6 11 4A 41 6D`, last 5 nibbles `A 4 1 6 D`:
`A→1, 4→4, 1→1, 6→6, D→4` → PIN **14164**.

## Checksum algorithm

Two bytes derived from the 5 key bytes:

- **byte 1** = XOR of the 5 key bytes, then XOR with mask `0x0D`
- **byte 2** = ones' complement of byte 1

Example — key `E6 11 4A 41 6D`:
`E6 ^ 11 ^ 4A ^ 41 ^ 6D = 91`, `91 ^ 0D = 9C`; complement → `63` → **9C 63**.

When a hex line (or a `.bin` record) includes the two checksum bytes, the tool
compares them against the computed pair and reports `VALID` or `MISMATCH`.

> The reference notes also mention an alternative first-checksum rule ("OR all
> bytes and mask `0x80`") used in some variants. This tool implements the
> XOR / `0x0D` rule, which is the one that reproduces the master and slave
> checksums in the examples below.

## Worked examples

All verified against the two reference dumps.

| record | key bytes | last 5 nibbles | PIN | checksum |
|--------|-----------|----------------|-----|----------|
| Master | `E6 11 4A 41 6D` | `A 4 1 6 D` | 14164 | `9C 63` ✓ |
| Slave  | `06 59 08 2E 45` | `8 2 E 4 5` | 82545 | `31 CE` ✓ |
| 145    | `A3 86 83 FA 0E` | `3 F A 0 E` | 36175 | — |
| 146    | `1E 2A 8E 04 59` | `E 0 4 5 9` | 57459 | — |
| Code1  | `BF 44 6C 37 34` | `C 3 7 3 4` | 33734 | — |

Checksum worked out for the master and slave records:

```
Master:  E6^11^4A^41^6D = 91,  91 ^ 0D = 9C,  ~9C = 63   ->  9C 63
Slave:   06^59^08^2E^45 = 3C,  3C ^ 0D = 31,  ~31 = CE   ->  31 CE
```

## Using it as a library

The core functions have no CLI dependencies and can be imported:

```python
from alfacode import decode_hex_line, scan_bin

d = decode_hex_line("80 21 2C E6 11 4A 41 6D 9C 63")
print(d.pin, d.checksum_ok)        # 14164 True

with open("example master key.bin", "rb") as f:
    for rec in scan_bin(f.read()):
        print(rec.pin, rec.key)
```
