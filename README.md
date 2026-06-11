# ordloc

A free, hierarchical, self-checking geocode. Public domain (CC0).

Every ~2 m square on Earth gets a speakable address, in your choice of
three interchangeable forms:

    standard  edge.suit.paddle.trust.magic     5 common words + checksum
    lite      drainage.rapid.journey.elongated 4 words + parity bit
    compact   hinir-fanur-ligim                17 chars, for URLs/QR codes

*ordloc* — from Swedish *ord*, "word".

## Why another geocode?

Because the popular word-based one is proprietary, and the open ones
aren't speakable. ordloc gives you all of the following at once, which
no existing scheme does:

* **Free forever.** CC0 spec, ~150 lines of public math, MIT/CC-licensed
  wordlists. No license, no SDK, no company that can disappear and take
  your addresses with it. Works fully offline.
* **Hierarchical.** Drop trailing words to zoom out: `edge.suit.paddle`
  is the ~280 m neighborhood containing `edge.suit.paddle.trust.magic`.
  Nearby places share leading words, so codes sort and index spatially.
* **Self-checking.** Standard codes embed a CRC-8: a misheard word is
  detected 99.6% of the time instead of silently pointing 200 km away.
* **Uniform.** Built on S2 cells: ~2.2 m cells at the equator and at
  78°N alike. Worst-case decode error 1.79 m (beats a 3 m square).
* **Forgiving.** First four letters of each word suffice:
  `edge.suit.padd.trus.magi` decodes identically.

## Usage

    pip install .          # or: pip install -r requirements.txt

    $ ordloc encode 58.5260 13.4870
    standard  edge.suit.paddle.trust.magic
    lite      drainage.rapid.journey.elongated
    compact   hinir-fanur-ligim

    $ ordloc decode edge.suit.paddle.trust.magic
    lat=58.526002 lon=13.487010  cell~2.2 m (level 22)  check=ok

As a library:

    from ordloc import encode_standard, decode_words
    code = encode_standard(58.5260, 13.4870)
    lat, lon, edge_m, level, check = decode_words(code)

## Files

    ordloc/            reference implementation + CLI + wordlists
    test_ordloc.py     test suite (run: python test_ordloc.py)
    SPEC.md             implementation-grade specification
    requirements.txt    runtime dependency (s2sphere)
    pyproject.toml      pip-installable package definition
    LICENSE             CC0 1.0 dedication

## Choosing a profile

Use **standard** by default — the checksum matters whenever a human
relays a code by voice. Use **lite** when matching the 3-4 word length
of other systems matters more than error detection. Use **compact** in
URLs, QR codes, filenames, and logs.

## Status & roadmap

v0.2, prototype quality. Known limitations and welcome contributions:

* JavaScript/browser port (needs a standalone S2 implementation)
* Localized wordlists (BIP-39 community lists exist for 10+ languages)
* Hilbert locality is statistical: points straddling S2 face edges
  don't share prefixes
* The 4096 list's edit-distance curation is heuristic; a phonetic
  (soundex/metaphone) pass would strengthen it

## Related work

Plus Codes (Open Location Code) pioneered the open grid geocode; Geohash
the hierarchical hash; what3words the word-triplet UX; ThisPlace
(Placeware) an early open geohash-to-words experiment; proquints the
pronounceable bit encoding. ordloc combines the open hierarchy of the
first two with the speakability of the rest, and adds checksums.

## Author

Magnus Strömberg — github@magnus.tech
