"""Robustness probes: the same sentences in the variant forms real Nepali text arrives in.

Each probe rewrites FLORES+ devtest sentences deterministically. Every sentence is encoded on its
own, with no special tokens:

* ``not_nfc``: the raw FLORES+ ``hin_Deva`` file, which is not NFC (it uses precomposed nukta
  letters such as U+095B), against its NFC form. Plain NFD is not used, because on NFC Devanagari
  FLORES it changes almost nothing (1 character in the Nepali devtest).
* ``zwj`` / ``zwnj``: a zero-width joiner / non-joiner inserted after every virama that is
  followed by a consonant, as some keyboards and font converters emit for half forms.
* ``vowel_length``: the most common Nepali misspelling, short/long vowel-sign swaps (ि↔ी, ु↔ू).
  In 20% of the words that have such a sign, one occurrence is swapped (fixed seed).
* ``pipe_danda``: the danda ``।`` typed as a pipe ``|``, as is common in informal digital Nepali.

Per probe, over all sentences (O = original, V = variant):

* changed = changed or inserted code points / code points of O
* token_ratio = tokens(V) / tokens(O): above 1 means the variant costs more tokens
* roundtrip_rate = share of variant sentences with decode(encode(v)) == v
* roundtrip_content_rate = the same with all whitespace removed before comparing (joiners are
  not whitespace, so a dropped ZWJ/ZWNJ still counts as a loss)
* unk_rate = unknown-token ids / tokens(V)
"""

from __future__ import annotations

import random
import unicodedata
from collections.abc import Sequence

import regex

from .metrics import same_content

VIRAMA = "्"
ZWJ, ZWNJ = "‍", "‌"
_VIRAMA_BEFORE_CONSONANT = regex.compile(r"्(?=[क-हक़-य़ॸ-ॿ])")
_LENGTH_SWAP = {"ि": "ी", "ी": "ि", "ु": "ू", "ू": "ु"}
PROBES = ("not_nfc", "zwj", "zwnj", "vowel_length", "pipe_danda")


def insert_joiner(text: str, joiner: str) -> tuple[str, int]:
    """Put ``joiner`` after every virama that precedes a consonant. Returns (text, insertions)."""
    out, n = _VIRAMA_BEFORE_CONSONANT.subn(VIRAMA + joiner, text)
    return out, n


def swap_vowel_length(lines: Sequence[str], rate: float = 0.2, seed: str = "yak-typo"):
    """Swap one short/long vowel sign in ``rate`` of the words that contain one."""
    rng = random.Random(seed)
    out, changed = [], 0
    for line in lines:
        words = line.split(" ")
        for j, word in enumerate(words):
            spots = [k for k, ch in enumerate(word) if ch in _LENGTH_SWAP]
            if spots and rng.random() < rate:
                k = rng.choice(spots)
                words[j] = word[:k] + _LENGTH_SWAP[word[k]] + word[k + 1 :]
                changed += 1
        out.append(" ".join(words))
    return out, changed


def _probe_stats(
    adapter, variant: list[str], reference_tokens: int, original_chars: int, changed: int
) -> dict:
    ids = adapter.encode_many(variant)
    decoded = adapter.decode_many(ids)
    tokens = sum(len(x) for x in ids)
    unk = adapter.unk_id
    n_unk = sum(1 for seq in ids for i in seq if i == unk) if unk is not None else 0
    return {
        "changed": changed / original_chars if original_chars else None,
        "token_ratio": tokens / reference_tokens if reference_tokens else None,
        "roundtrip_rate": sum(d == v for d, v in zip(decoded, variant, strict=True)) / len(variant),
        "roundtrip_content_rate": sum(
            same_content(d, v) for d, v in zip(decoded, variant, strict=True)
        )
        / len(variant),
        "unk_rate": n_unk / tokens if tokens else None,
    }


def run_probes(
    adapter, npi_lines: Sequence[str], hin_raw_lines: Sequence[str] | None = None
) -> dict:
    """All probes for one tokenizer. ``npi_lines`` are NFC Nepali sentences; ``hin_raw_lines``
    are the Hindi sentences exactly as published (not NFC)."""
    npi = list(npi_lines)
    base_tokens = sum(len(x) for x in adapter.encode_many(npi))
    chars = sum(len(s) for s in npi)
    out: dict = {}

    if hin_raw_lines:
        raw = list(hin_raw_lines)
        nfc = [unicodedata.normalize("NFC", s) for s in raw]
        nfc_tokens = sum(len(x) for x in adapter.encode_many(nfc))
        changed = sum(1 for s in raw for ch in s if unicodedata.normalize("NFC", ch) != ch)
        out["not_nfc"] = _probe_stats(adapter, raw, nfc_tokens, sum(len(s) for s in raw), changed)

    for name, joiner in (("zwj", ZWJ), ("zwnj", ZWNJ)):
        pairs = [insert_joiner(s, joiner) for s in npi]
        out[name] = _probe_stats(
            adapter, [p[0] for p in pairs], base_tokens, chars, sum(p[1] for p in pairs)
        )

    typo, changed = swap_vowel_length(npi)
    out["vowel_length"] = _probe_stats(adapter, typo, base_tokens, chars, changed)

    piped = [s.replace("।", "|") for s in npi]
    out["pipe_danda"] = _probe_stats(
        adapter, piped, base_tokens, chars, sum(s.count("।") for s in npi)
    )
    return out
