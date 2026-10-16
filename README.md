# AlfaCode

Decoder for Alfa Romeo immobiliser transponder dumps. Given a transponder
record it recovers the **PIN** and verifies the two **checksum** bytes, from
either a raw hex line or a `.bin` memory dump.

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
