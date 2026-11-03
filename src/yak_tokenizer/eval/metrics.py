"""Tokenizer metrics. Every formula is corpus-level unless its name says otherwise.

Notation for one eval text made of segments s_1..s_n (FLORES sentences, word-list lines or
documents), measured with one tokenizer, never adding special tokens:

* ``J`` = ``"\\n".join(s_1..s_n)``, the joined text. ``W`` = ``len(J.split())``, the number of
  whitespace-delimited words (Python ``str.split()``, i.e. runs of Unicode whitespace).
* ``T`` = the headline token count. For texts counted ``"joined"`` (FLORES) it is
  ``len(encode(J))``: the whole file in one call, so line breaks cost what they cost. For texts
  counted ``"segments"`` (word lists, documents) it is ``sum_i len(encode(s_i))``.
* ``C`` and ``B`` = code points and UTF-8 bytes of the counted text (``J`` for joined texts, the
  concatenated segments for segment-counted texts).

Formulas:

* fertility = T / W
* fertility_segments = sum_i len(encode(s_i)) / W (no separators between lines)
* fertility_mean = mean_i [ len(encode(s_i)) / len(s_i.split()) ] over segments with words
* chars_per_token = C / T, bytes_per_token = B / T
* parity(L) = sum_i len(encode(L_i)) / sum_i len(encode(E_i)) over line-aligned segments of
  language L and the reference (English) E; parity_mean(L) = mean_i of the per-line ratios
* roundtrip_rate = #{i : decode(encode(s_i)) == s_i} / n (exact string equality)
* roundtrip_content_rate = the same, comparing the strings with all whitespace removed, so a
  decoder that only adds or drops spaces (prefix space, WordPiece spacing around punctuation)
  passes, while one that loses characters (unknown tokens, normalisation) does not
* vocab_utilization = #distinct ids in the counted text / vocab_size
* orphan_mark_rate = #{tokens whose first byte starts a combining-mark character} / T. A combining
  mark is Unicode category Mn, Mc or Me; in Devanagari these are the vowel signs (matras), virama,
  nukta, anusvara, chandrabindu and visarga. A token that begins with one was cut off its
  consonant: the matra-splitting failure.
* mid_char_rate = #{tokens whose first byte is a UTF-8 continuation byte} / T: tokens that begin
  inside a character (byte-level fragments or byte-fallback pieces).
* byte_piece_rate = #{tokens whose surface bytes are not valid UTF-8 on their own} / T: byte
  fragments, from byte-level BPE that never merged a character or from byte fallback for a
  character missing from the vocab. Unlike unk_rate, these round-trip, so they hide a missing
  character; ऊ through byte fallback is 3 tokens.
* unk_rate = #{tokens equal to the unknown id} / T
* renyi_efficiency = H_a(p) / log |V| with H_a(p) = log(sum_t p_t^a) / (1 - a), a = 2.5, p the
  unigram distribution of token ids in the counted text and |V| the vocab size
  (Zouhar et al., 2023, "Tokenization and the Noiseless Channel").

Per tokenizer (not per text), :func:`script_coverage`: the characters of a set (all assigned
Devanagari code points U+0900-U+097F, and :data:`NEPALI_CORE`) that no vocabulary token contains
whole. A missing character is still encoded, as unknown or as byte pieces, but never as part of a
learned word.
"""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

# Characters of everyday Nepali writing: independent vowels, consonants, signs, vowel signs,
# virama, avagraha, danda and double danda, digits and om. Excludes Vedic accents, Marwari and
# Sindhi letters, and the precomposed nukta letters (U+0958-U+095F), which NFC decomposes.
NEPALI_CORE = "अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहँंः़ऽािीुूृेैोौ्।॥०१२३४५६७८९ॐ"
DEVANAGARI_BLOCK = "".join(
    chr(c) for c in range(0x0900, 0x0980) if unicodedata.category(chr(c)) != "Cn"
)


def script_coverage(pieces: Iterable[bytes], charsets: dict[str, str]) -> dict:
    """For each named character set, the characters no token contains whole.

    ``pieces`` are the surface bytes of every vocabulary id. A character counts as covered when
    some token decodes to text containing it, so a byte-level token holding all three bytes of ऊ
    covers it and a lone lead byte does not.
    """
    seen: set[str] = set()
    for piece in pieces:
        seen.update(piece.decode("utf-8", errors="ignore"))
    out = {}
    for name, chars in charsets.items():
        missing = [c for c in chars if c not in seen]
        out[name] = {
            "size": len(chars),
            "missing": "".join(missing),
            "covered_share": 1 - len(missing) / len(chars),
        }
    return out


def is_byte_piece(piece: bytes) -> bool:
    """A token that is not whole characters: a byte fragment or a byte-fallback piece."""
    try:
        piece.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def whitespace_words(text: str) -> int:
    return len(text.split())


def safe_ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def fertility(tokens: int, words: int) -> float | None:
    """Tokens per whitespace word."""
    return safe_ratio(tokens, words)


def mean_ratio(nums: Sequence[int], dens: Sequence[int]) -> float | None:
    """Mean of per-item ratios, skipping items whose denominator is zero."""
    pairs = [n / d for n, d in zip(nums, dens, strict=True) if d]
    return sum(pairs) / len(pairs) if pairs else None


def parity(lang_tokens: Sequence[int], ref_tokens: Sequence[int]) -> float | None:
    """Total tokens of a language over total tokens of the reference on aligned lines."""
    if len(lang_tokens) != len(ref_tokens):
        raise ValueError("parity needs line-aligned texts of equal length")
    return safe_ratio(sum(lang_tokens), sum(ref_tokens))


def roundtrip_rate(originals: Sequence[str], decoded: Sequence[str]) -> float | None:
    if len(originals) != len(decoded):
        raise ValueError("round-trip needs one decoded string per original")
    return safe_ratio(sum(o == d for o, d in zip(originals, decoded)), len(originals))


def same_content(a: str, b: str) -> bool:
    """Equal once all whitespace is removed."""
    return "".join(a.split()) == "".join(b.split())


def vocab_utilization(distinct_ids: int, vocab_size: int) -> float | None:
    return safe_ratio(distinct_ids, vocab_size)


def renyi_efficiency(counts: Counter, vocab_size: int, alpha: float = 2.5) -> float | None:
    total = sum(counts.values())
    if not total or vocab_size < 2:
        return None
    power_sum = sum((c / total) ** alpha for c in counts.values())
    entropy = math.log(power_sum) / (1.0 - alpha)
    return entropy / math.log(vocab_size)


def _utf8_len(lead: int) -> int:
    if lead < 0x80:
        return 1
    if lead >= 0xF0:
        return 4
    if lead >= 0xE0:
        return 3
    return 2


def is_combining_mark(ch: str) -> bool:
    return unicodedata.category(ch).startswith("M")


def classify_token_starts(pieces: Sequence[bytes]) -> tuple[int, int]:
    """Count tokens that start on a combining mark, and tokens that start inside a character.

    ``pieces`` are the surface bytes of consecutive tokens. A token's first character is decoded
    from the concatenated stream, so a mark whose bytes spill into the next token still counts.
    """
    stream = b"".join(pieces)
    orphan = mid = pos = 0
    for piece in pieces:
        if piece:
            lead = stream[pos]
            if 0x80 <= lead < 0xC0:
                mid += 1
            else:
                char_bytes = stream[pos : pos + _utf8_len(lead)]
                try:
                    ch = char_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    ch = ""
                if ch and is_combining_mark(ch):
                    orphan += 1
        pos += len(piece)
    return orphan, mid


@dataclass
class TokenTally:
    """Running token statistics over one text (possibly encoded in several chunks)."""

    tokens: int = 0
    orphan_marks: int = 0
    mid_char: int = 0
    byte_pieces: int = 0
    unk: int = 0
    counts: Counter = field(default_factory=Counter)

    def add(self, ids: Sequence[int], pieces: Sequence[bytes], unk_id: int | None = None) -> None:
        self.tokens += len(ids)
        self.counts.update(ids)
        orphan, mid = classify_token_starts(pieces)
        self.orphan_marks += orphan
        self.mid_char += mid
        self.byte_pieces += sum(1 for p in pieces if is_byte_piece(p))
        if unk_id is not None:
            self.unk += sum(1 for i in ids if i == unk_id)


def summarize(
    *,
    words: int,
    chars: int,
    nbytes: int,
    tally: TokenTally,
    segment_tokens: Sequence[int],
    segment_words: Sequence[int],
    roundtrip_ok: int,
    content_ok: int | None = None,
    segments: int,
    vocab_size: int,
) -> dict:
    """All per-text metrics as a flat dict (see the module docstring for the formulas)."""
    t = tally.tokens
    return {
        "segments": segments,
        "words": words,
        "chars": chars,
        "bytes": nbytes,
        "tokens": t,
        "tokens_segments": sum(segment_tokens),
        "fertility": fertility(t, words),
        "fertility_segments": fertility(sum(segment_tokens), words),
        "fertility_mean": mean_ratio(segment_tokens, segment_words),
        "chars_per_token": safe_ratio(chars, t),
        "bytes_per_token": safe_ratio(nbytes, t),
        "roundtrip_rate": safe_ratio(roundtrip_ok, segments),
        "roundtrip_content_rate": None if content_ok is None else safe_ratio(content_ok, segments),
        "vocab_used": len(tally.counts),
        "vocab_utilization": vocab_utilization(len(tally.counts), vocab_size),
        "orphan_mark_rate": safe_ratio(tally.orphan_marks, t),
        "mid_char_rate": safe_ratio(tally.mid_char, t),
        "byte_piece_rate": safe_ratio(tally.byte_pieces, t),
        "unk_rate": safe_ratio(tally.unk, t),
        "renyi_efficiency": renyi_efficiency(tally.counts, vocab_size),
    }


def iter_chunks(segments: Sequence[str], max_chars: int = 2_000_000) -> Iterable[str]:
    """Yield pieces of ``"\\n".join(segments)`` that concatenate back to it exactly.

    Each chunk holds whole segments and, except the last, ends with the ``"\\n"`` that separated
    it from the next one. Files up to ``max_chars`` (all of FLORES) are a single chunk, so their
    count is identical to encoding the whole file at once.
    """
    buf: list[str] = []
    size = 0
    for i, seg in enumerate(segments):
        piece = seg if i == len(segments) - 1 else seg + "\n"
        if buf and size + len(piece) > max_chars:
            yield "".join(buf)
            buf, size = [], 0
        buf.append(piece)
        size += len(piece)
    if buf:
        yield "".join(buf)
