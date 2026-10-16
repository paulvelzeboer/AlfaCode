#!/usr/bin/env python3
"""Alfa Romeo immobiliser transponder decoder.

Recovers the PIN and verifies the two checksum bytes from a transponder
dump, given either a raw hex line or a .bin memory dump.

Record layout (after the fixed 80 21 2C header):
    5 key bytes  +  2 checksum bytes

PIN:   taken from the last 5 nibbles of the 5 key bytes, one nibble per
       digit, using the map  >9 -> subtract 9,  0 -> add 7.
CKSUM: byte1 = XOR of the 5 key bytes, XOR 0x0D
       byte2 = ones' complement of byte1

Usage:
    python alfacode.py "80 21 2C E6 11 4A 41 6D 9C 63"
    python alfacode.py "example master key.bin"
    python alfacode.py              # reads a hex line from stdin
"""

import sys
import os

HEADER = (0x80, 0x21, 0x2C)
MASK = 0x0D


def map_nibble(n: int) -> int:
    """Map one hex nibble (0-15) to its PIN digit."""
    v = n
    if v > 9:
        v -= 9
    if n == 0:
        v = 7
    return v


def checksum(key: list[int]) -> tuple[int, int]:
    """Return the two checksum bytes for the 5 key bytes."""
    x = 0
    for b in key:
        x ^= b
    cs1 = (x ^ MASK) & 0xFF
    cs2 = (~cs1) & 0xFF
    return cs1, cs2


def pin_from_key(key: list[int]) -> str:
    """Recover the 5-digit PIN from the 5 key bytes."""
    nibbles = []
    for b in key:
        nibbles.append(b >> 4)
        nibbles.append(b & 0x0F)
    return "".join(str(map_nibble(n)) for n in nibbles[-5:])


class Decoded:
    def __init__(self, key, given=None):
        self.key = key
        self.pin = pin_from_key(key)
        self.cs1, self.cs2 = checksum(key)
        self.given = given  # (b1, b2) read from the dump, or None

    @property
    def checksum_ok(self):
        if self.given is None:
            return None
        return self.given == (self.cs1, self.cs2)

    def report(self) -> str:
        key = " ".join(f"{b:02X}" for b in self.key)
        lines = [
            f"  PIN/AlfaCode : {self.pin}",
            f"  key bytes   : {key}",
            f"  checksum    : {self.cs1:02X} {self.cs2:02X}",
        ]
        if self.checksum_ok is True:
            lines.append("  status      : checksum VALID")
        elif self.checksum_ok is False:
            g = " ".join(f"{b:02X}" for b in self.given)
            lines.append(f"  status      : checksum MISMATCH (dump has {g})")
        else:
            lines.append("  status      : no checksum in dump (computed above)")
        return "\n".join(lines)


def decode_bytes(data: list[int]) -> Decoded:
    """Decode a byte sequence: strip an 80 21 2C header if present."""
    if len(data) >= 3 and tuple(data[:3]) == HEADER:
        data = data[3:]
    if len(data) < 5:
        raise ValueError("need 5 key bytes after the 80 21 2C header")
    key = data[:5]
    given = tuple(data[5:7]) if len(data) >= 7 else None
    return Decoded(key, given)


def decode_hex_line(line: str) -> Decoded:
    hexdigits = "".join(c for c in line if c in "0123456789abcdefABCDEF")
    if not hexdigits:
        raise ValueError("no hex digits found")
    if len(hexdigits) % 2:
        raise ValueError("odd number of hex digits")
    data = [int(hexdigits[i:i + 2], 16) for i in range(0, len(hexdigits), 2)]
    return decode_bytes(data)


def scan_bin(data: bytes) -> list[Decoded]:
    """Find every 80 21 2C record in a binary dump, deduped in order."""
    seen = set()
    out = []
    for i in range(len(data) - 9):
        if data[i] == 0x80 and data[i + 1] == 0x21 and data[i + 2] == 0x2C:
            rec = tuple(data[i:i + 10])
            if rec not in seen:
                seen.add(rec)
                out.append(decode_bytes(list(rec)))
    return out


def main(argv: list[str]) -> int:
    arg = argv[1] if len(argv) > 1 else sys.stdin.readline()

    if os.path.isfile(arg):
        with open(arg, "rb") as f:
            data = f.read()
        records = scan_bin(data)
        if not records:
            print(f"No 80 21 2C record found in {arg}")
            return 1
        word = "record" if len(records) == 1 else "distinct records"
        print(f"{arg} - {len(records)} {word} found\n")
        for i, d in enumerate(records, 1):
            print(f"[{i}]")
            print(d.report())
            print()
        return 0

    try:
        print(decode_hex_line(arg).report())
    except ValueError as e:
        print(f"error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
