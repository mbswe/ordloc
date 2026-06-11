# ordloc Specification v0.2

Status: draft. License: CC0 1.0 (public domain dedication).
Author: Magnus Strömberg <github@magnus.tech>

ordloc is a geocode: a short string identifying a small cell on Earth's
surface. It is designed to be free to implement, hierarchical, and
self-checking. This document is sufficient to write an independent,
interoperable implementation.

## 1. Payload

The payload is a level-22 cell of the S2 geometry system
(https://s2geometry.io). S2 projects the sphere onto the six faces of a
cube and orders cells along a Hilbert curve, giving near-uniform cell
sizes worldwide (level-22 edge ≈ 2.2 m) and strong spatial locality.

A level-22 S2 cell id, in S2's canonical 64-bit form, consists of 3 face
bits, 44 position bits (2 per level), a trailing 1 bit, and 16 zero bits.
The ordloc payload P is the top 47 bits:

    P = cell_id >> 17        (47 bits: 3 face + 44 position)

Decoding reverses this: `cell_id = (P << 17) | (1 << 16)`. The decoded
location is the center of that cell.

## 2. Profiles

All profiles encode the same payload P and are mutually convertible.

### 2.1 STANDARD — 5 words, 2048-word list, CRC-8

    V = (P << 8) | CRC8(P)                       (55 bits)
    code = w[V>>44 & 0x7FF] . w[V>>33 & 0x7FF] . w[V>>22 & 0x7FF]
         . w[V>>11 & 0x7FF] . w[V & 0x7FF]

where `w` is `wordlist_2048.txt` (the BIP-39 English list, MIT licensed),
zero-indexed in file order, and words are joined with "." (decoders MUST
also accept "," and whitespace as separators, case-insensitively).

CRC8 is CRC-8 with polynomial 0x07, initial value 0x00, no reflection,
no final XOR, computed over the 47 payload bits MSB-first.

### 2.2 LITE — 4 words, 4096-word list, parity

    V = (P << 1) | parity(P)                     (48 bits)
    code = w[V>>36 & 0xFFF] . w[V>>24 & 0xFFF] . w[V>>12 & 0xFFF]
         . w[V & 0xFFF]

where `w` is `wordlist_4096.txt` (this distribution; a superset of the
2048 list) and parity(P) is the XOR of all payload bits (even parity).

### 2.3 COMPACT — 3 proquint words

    V = P << 1                                   (48 bits, low bit zero)

V is split into three 16-bit groups (MSB first). Each group becomes one
five-letter word, bits MSB-first:

    c1(4) v1(2) c2(4) v2(2) c3(4)
    consonants (value 0-15): b d f g h j k l m n p r s t v z
    vowels     (value 0-3):  a i o u

Words are joined with "-". COMPACT has no checksum.

## 3. Hierarchy (truncation)

Removing trailing words yields a coarser location. To decode a code of
n words (n < full length), concatenate the word indices into
`bits = B*n` bits (B = 11, 12, or 16 per profile; for a full-length
COMPACT code first drop the final pad bit). Then:

    pos_bits = bits - 3
    level    = floor(pos_bits / 2)
    value  >>= pos_bits - 2*level        (drop the odd bit, if any)

and reconstruct the level-`level` cell id as in §1. Truncated STANDARD
and LITE codes carry no checksum; implementations SHOULD report this.

Approximate cell edge by truncation length:

    STANDARD  5: 2.2 m   4: 9 m     3: 280 m   2: 18 km   1: 576 km
    LITE      4: 2.2 m   3: 140 m   2: 9 km    1: 576 km
    COMPACT   3: 2.2 m   2: 563 m   1: 144 km

Note: a 4-word string is ambiguous between LITE and truncated STANDARD.
Decoders MUST treat 5 words as STANDARD and SHOULD default 4 words to
LITE; decoding truncated STANDARD codes requires an explicit profile
hint from the caller.

## 4. Word lookup and abbreviation

Both wordlists guarantee that no two words share their first four
letters. Decoders MUST accept any input word of length >= 4 whose first
four letters match exactly one list word. Lookup is case-insensitive.

## 5. Wordlist provenance

* wordlist_2048.txt — the BIP-39 English wordlist (MIT license,
  bitcoin/bips repository), unmodified.
* wordlist_4096.txt — the 2048 list plus 2048 additional words selected
  deterministically from the EFF large wordlist (CC-BY 3.0) and the
  google-10000-english list, filtered for: 3-9 letters, lowercase
  alphabetic, unique first-4-letter prefix across the whole list, and
  minimum edit-distance constraints against all previously accepted
  words. The shipped file is normative; the build procedure is
  documentation only.

## 6. Test vectors

    lat=58.526000  lon=13.487000   (Götene, Sweden)
      STANDARD  edge.suit.paddle.trust.magic
      LITE      drainage.rapid.journey.elongated
      COMPACT   hinir-fanur-ligim

    lat=48.858400  lon=2.294500    (Eiffel Tower)
      STANDARD  elevator.cricket.wear.traffic.round

    lat=-33.856800 lon=151.215300  (Sydney Opera House)
      STANDARD  help.nice.often.can.clip

All decode to within 2.2 m of the input coordinates with check=ok.
