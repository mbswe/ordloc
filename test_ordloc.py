"""ordloc test suite — run: python test_ordloc.py"""
import math
import random

from ordloc import (decode_compact, decode_words, encode_compact,
                     encode_lite, encode_standard, W2048, W4096, _IDX)


def dist_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


def rand_point(rng):
    return math.degrees(math.asin(rng.uniform(-1, 1))), rng.uniform(-180, 180)


def test_roundtrip():
    rng = random.Random(1)
    worst = {"standard": 0, "lite": 0, "compact": 0}
    for _ in range(20000):
        p = rand_point(rng)
        for name, enc, dec in (
                ("standard", encode_standard, decode_words),
                ("lite", encode_lite, lambda c: decode_words(c, "lite")),
                ("compact", encode_compact, decode_compact)):
            la, lo, _, _, st = dec(enc(*p))
            assert st in ("ok", "none"), f"{name}: checksum {st}"
            worst[name] = max(worst[name], dist_m(p, (la, lo)))
    for k, v in worst.items():
        print(f"  {k:9} worst round-trip error: {v:.2f} m")
        assert v < 2.5
    print("PASS roundtrip (20k points x 3 profiles)")


def test_checksum():
    rng = random.Random(2)
    for name, enc, n_words, wl, expect_min in (
            ("standard", encode_standard, 5, W2048, 0.99),
            ("lite", encode_lite, 4, W4096, 0.49)):
        caught = trials = 0
        for _ in range(4000):
            ws = enc(*rand_point(rng)).split(".")
            k = rng.randrange(n_words)
            repl = wl[rng.randrange(len(wl))]
            if repl == ws[k]:
                continue
            ws[k] = repl
            *_, st = decode_words(".".join(ws), name)
            trials += 1
            caught += (st == "FAILED")
        rate = caught / trials
        print(f"  {name:9} single-word typos caught: {rate:.1%}")
        assert rate > expect_min
    print("PASS checksum")


def test_hierarchy():
    lat, lon = 58.5260, 13.4870
    for name, code, prof in (
            ("standard", encode_standard(lat, lon), "standard"),
            ("lite", encode_lite(lat, lon), "lite")):
        ws = code.split(".")
        prev_edge = 0
        for n in range(len(ws), 0, -1):
            la, lo, edge, lvl, _ = decode_words(".".join(ws[:n]), prof)
            assert dist_m((lat, lon), (la, lo)) < edge * 1.5
            assert edge > prev_edge or n == len(ws)
            prev_edge = edge
    print("PASS hierarchy (truncation stays inside coarser cell)")


def test_abbreviation():
    lat, lon = 48.8584, 2.2945
    for prof, enc in (("standard", encode_standard), ("lite", encode_lite)):
        full = enc(lat, lon)
        abbr = ".".join(w[:4] for w in full.split("."))
        a = decode_words(full, prof)
        b = decode_words(abbr, prof)
        assert a == b
    print("PASS abbreviation (first 4 letters decode identically)")


def test_wordlists():
    assert len(set(W2048)) == 2048 and len(set(W4096)) == 4096
    assert set(W2048) <= set(W4096), "2048 list must be a subset of 4096"
    assert len({w[:4] for w in W2048}) == 2048
    assert len({w[:4] for w in W4096}) == 4096
    assert all(w.isalpha() and w.islower() and 3 <= len(w) <= 9
               for w in W4096)
    print("PASS wordlists (sizes, subset, prefix-4 uniqueness, charset)")


def test_uniformity():
    pts = [(0.0, 0.0), (78.22, 15.65), (-54.8, -68.3), (35.68, 139.69)]
    edges = [decode_words(encode_standard(*p))[2] for p in pts]
    assert max(edges) / min(edges) < 1.5
    print(f"  cell edges worldwide: {min(edges):.2f}-{max(edges):.2f} m")
    print("PASS uniformity")


if __name__ == "__main__":
    for t in (test_wordlists, test_roundtrip, test_checksum,
              test_hierarchy, test_abbreviation, test_uniformity):
        t()
    print("\nALL TESTS PASSED")
