#!/usr/bin/env python3
"""
ordloc v0.2 — a free, hierarchical, self-checking geocode.
Dedicated to the public domain under CC0 1.0.

One geometric payload, three renderings ("profiles"):

  COMPACT   hinir-fanur-ligim              3 proquint words, 17 chars
  STANDARD  edge.suit.paddle.trust.magic   5 words (2048 list) + CRC-8
  LITE      4 words (4096 list) + parity   w3w-length, weaker check

Payload: S2 cell at level 22 (~2.2 m edge, near-uniform worldwide) =
47 bits: 3 face bits + 44 Hilbert-curve position bits. Truncating words
in any profile yields a valid coarser cell ("zoom out").

Requires: s2sphere  (pip install s2sphere)
"""

import math
import os
import sys

import s2sphere

LEVEL = 22
_HERE = os.path.dirname(os.path.abspath(__file__))
CONS, VOWS = "bdfghjklmnprstvz", "aiou"


def _load(name, n):
    with open(os.path.join(_HERE, name)) as f:
        words = [w.strip() for w in f if w.strip()]
    assert len(words) == n, f"{name}: expected {n} words, got {len(words)}"
    return words


W2048 = _load("wordlist_2048.txt", 2048)
W4096 = _load("wordlist_4096.txt", 4096)
_IDX = {
    11: ({w: i for i, w in enumerate(W2048)},
         {w[:4]: i for i, w in enumerate(W2048)}, W2048),
    12: ({w: i for i, w in enumerate(W4096)},
         {w[:4]: i for i, w in enumerate(W4096)}, W4096),
}

# ---------------- geometric core ----------------

def _payload(lat, lon):
    """47-bit level-22 S2 cell: 3 face bits + 44 position bits."""
    cid = s2sphere.CellId.from_lat_lng(
        s2sphere.LatLng.from_degrees(lat, lon)).parent(LEVEL).id()
    return cid >> 17


def _cell(val, pos_bits):
    """Decode (3 face bits + pos_bits position bits), rounding down to a
    valid even level. Returns (lat, lon, cell_edge_m, level)."""
    level = pos_bits // 2
    val >>= pos_bits - 2 * level
    shift = 64 - 3 - 2 * level
    cid = (val << shift) | (1 << (shift - 1))
    ll = s2sphere.CellId(cid).to_lat_lng()
    edge_m = math.sqrt(85011012.19e6 / 4 ** level)
    return ll.lat().degrees, ll.lng().degrees, edge_m, level


def _crc8(val, bits):  # CRC-8, polynomial 0x07
    crc = 0
    for i in range(bits - 1, -1, -1):
        crc ^= ((val >> i) & 1) << 7
        crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _parity(val):
    return bin(val).count("1") & 1

# ---------------- compact profile ----------------

def encode_compact(lat, lon):
    b = _payload(lat, lon) << 1  # pad to 48 bits
    out = []
    for s in (32, 16, 0):
        u = b >> s & 0xFFFF
        out.append(CONS[u >> 12 & 15] + VOWS[u >> 10 & 3]
                   + CONS[u >> 6 & 15] + VOWS[u >> 4 & 3] + CONS[u & 15])
    return "-".join(out)


def decode_compact(code):
    ws = code.lower().strip().split("-")
    if not 1 <= len(ws) <= 3:
        raise ValueError("compact codes have 1-3 words")
    val = 0
    for w in ws:
        if len(w) != 5:
            raise ValueError(f"bad word: {w!r}")
        val = (val << 16 | CONS.index(w[0]) << 12 | VOWS.index(w[1]) << 10
               | CONS.index(w[2]) << 6 | VOWS.index(w[3]) << 4
               | CONS.index(w[4]))
    pad = 1 if len(ws) == 3 else 0
    lat, lon, edge, lvl = _cell(val >> pad, 16 * len(ws) - 3 - pad)
    return lat, lon, edge, lvl, "none"

# ---------------- word profiles ----------------

def _lookup(w, bits):
    idx, pfx, _ = _IDX[bits]
    w = w.lower().strip()
    if w in idx:
        return idx[w]
    if len(w) >= 4 and w[:4] in pfx:  # first-4-letter abbreviation
        return pfx[w[:4]]
    raise ValueError(f"unknown word: {w!r}")


def encode_standard(lat, lon):
    """5 words x 11 bits = 47-bit payload + CRC-8."""
    p = _payload(lat, lon)
    v = (p << 8) | _crc8(p, 47)
    return ".".join(W2048[v >> s & 0x7FF] for s in (44, 33, 22, 11, 0))


def encode_lite(lat, lon):
    """4 words x 12 bits = 47-bit payload + 1 parity bit."""
    p = _payload(lat, lon)
    v = (p << 1) | _parity(p)
    return ".".join(W4096[v >> s & 0xFFF] for s in (36, 24, 12, 0))


def decode_words(code, profile="auto"):
    """Decode STANDARD or LITE codes, including truncated ones.

    profile: 'standard', 'lite', or 'auto'.
    Auto rule: 5 words -> standard; 4 words -> lite unless a word only
    exists in the 2048 list context is impossible (2048 is a subset of
    4096), so truncated standard codes must pass profile='standard'.
    Returns (lat, lon, cell_edge_m, level, check) where check is
    'ok' | 'FAILED' | 'partial' (truncated, no checksum available).
    """
    ws = [w for w in code.replace(",", ".").split(".") if w]
    n = len(ws)
    if profile == "auto":
        profile = "standard" if n == 5 else "lite"
    bits = 11 if profile == "standard" else 12
    full = 5 if profile == "standard" else 4
    if not 1 <= n <= full:
        raise ValueError(f"{profile} codes have 1-{full} words")
    val = 0
    for w in ws:
        val = val << bits | _lookup(w, bits)
    if n == full:
        if profile == "standard":
            p, chk = val >> 8, val & 0xFF
            ok = _crc8(p, 47) == chk
        else:
            p, chk = val >> 1, val & 1
            ok = _parity(p) == chk
        return (*_cell(p, 44), "ok" if ok else "FAILED")
    return (*_cell(val, bits * n - 3), "partial")

# ---------------- CLI ----------------

_USAGE = """ordloc — free hierarchical geocodes (CC0)
usage:
  ordloc.py encode LAT LON [--profile standard|lite|compact|all]
  ordloc.py decode CODE    [--profile standard|lite|auto]
"""


def main(argv):
    if len(argv) < 2:
        print(_USAGE); return 1
    cmd, args = argv[1], argv[2:]
    prof = "all"
    if "--profile" in args:
        i = args.index("--profile")
        prof = args[i + 1]; del args[i:i + 2]
    if cmd == "encode" and len(args) == 2:
        lat, lon = float(args[0]), float(args[1])
        rows = {"standard": encode_standard, "lite": encode_lite,
                "compact": encode_compact}
        for name, fn in rows.items():
            if prof in ("all", name):
                print(f"{name:9} {fn(lat, lon)}")
        return 0
    if cmd == "decode" and len(args) == 1:
        code = args[0]
        if "-" in code:
            lat, lon, edge, lvl, st = decode_compact(code)
        else:
            lat, lon, edge, lvl, st = decode_words(
                code, prof if prof in ("standard", "lite") else "auto")
        print(f"lat={lat:.6f} lon={lon:.6f}  cell~{edge:.1f} m "
              f"(level {lvl})  check={st}")
        return 0
    print(_USAGE); return 1


def cli():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    cli()
