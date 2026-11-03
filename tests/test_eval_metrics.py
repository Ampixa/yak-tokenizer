"""Metric definitions of the eval harness, each checked on a tiny fixture."""

from collections import Counter

import pytest

from yak_tokenizer.eval.metrics import (
    DEVANAGARI_BLOCK,
    NEPALI_CORE,
    TokenTally,
    classify_token_starts,
    fertility,
    is_byte_piece,
    iter_chunks,
    mean_ratio,
    parity,
    renyi_efficiency,
    roundtrip_rate,
    script_coverage,
    summarize,
    vocab_utilization,
    whitespace_words,
)


def enc(*parts: str) -> list[bytes]:
    return [p.encode("utf-8") for p in parts]


def test_whitespace_words_uses_str_split():
    assert whitespace_words("नेपालमा  हिमाल छन्।\nघर") == 4
    assert whitespace_words(" \t\n") == 0


def test_fertility_is_tokens_per_word():
    assert fertility(10, 4) == 2.5
    assert fertility(3, 0) is None


def test_mean_ratio_skips_empty_items():
    assert mean_ratio([2, 6, 5], [1, 3, 0]) == 2.0
    assert mean_ratio([1], [0]) is None


def test_parity_is_ratio_of_totals():
    assert parity([3, 5], [2, 2]) == 2.0
    with pytest.raises(ValueError):
        parity([1, 2], [1])


def test_roundtrip_rate_is_exact_equality():
    assert roundtrip_rate(["नेपाल", "a b", "x"], ["नेपाल", "a  b", "x"]) == pytest.approx(2 / 3)
    assert roundtrip_rate([], []) is None


def test_vocab_utilization():
    assert vocab_utilization(16, 64) == 0.25


def test_renyi_efficiency_bounds():
    uniform = Counter({0: 5, 1: 5, 2: 5, 3: 5})
    assert renyi_efficiency(uniform, 4) == pytest.approx(1.0)
    assert renyi_efficiency(uniform, 16) == pytest.approx(0.5)
    skewed = Counter({0: 97, 1: 1, 2: 1, 3: 1})
    assert renyi_efficiency(skewed, 4) < 0.2
    assert renyi_efficiency(Counter(), 4) is None


def test_orphan_marks_at_every_matra():
    # नेपाली split before each vowel sign, as a \p{L}+ pre-tokenizer does.
    orphan, mid = classify_token_starts(enc("न", "े", "प", "ा", "ल", "ी"))
    assert (orphan, mid) == (3, 0)


def test_whole_words_have_no_orphans():
    assert classify_token_starts(enc("नेपाली", " भाषा")) == (0, 0)
    # A cut after the matra is fine; a space before a mark is not a mark start.
    assert classify_token_starts(enc("ने", "पाली", " ा")) == (0, 0)


def test_virama_start_is_an_orphan():
    assert classify_token_starts(enc("प्र", "धान", "मन्", "्त्री")) == (1, 0)


def test_byte_fragments_count_as_mid_char():
    aa = "ा".encode()  # 3 bytes: the token holding the lead byte starts on the mark
    orphan, mid = classify_token_starts([b"\xe0\xa4\xa8", aa[:1], aa[1:]])
    assert (orphan, mid) == (1, 1)


def test_token_tally_counts_unknowns_and_distinct_ids():
    tally = TokenTally()
    tally.add([5, 0, 5], enc("ab", "?", "ab"), unk_id=0)
    tally.add([7], enc("ा"), unk_id=0)
    assert (tally.tokens, tally.unk, tally.orphan_marks, len(tally.counts)) == (4, 1, 1, 3)


def test_iter_chunks_rebuilds_the_joined_text():
    segs = ["एक", "दुई तीन", "", "चार"]
    for size in (1, 4, 8, 1000):
        chunks = list(iter_chunks(segs, size))
        assert "".join(chunks) == "\n".join(segs)
    assert len(list(iter_chunks(segs, 1000))) == 1


def test_summarize_formulas():
    tally = TokenTally()
    tally.add([1, 2, 3, 1], enc("न", "े", "पाल", "न"))
    m = summarize(
        words=2,
        chars=10,
        nbytes=24,
        tally=tally,
        segment_tokens=[3, 1],
        segment_words=[1, 1],
        roundtrip_ok=1,
        segments=2,
        vocab_size=100,
    )
    assert m["fertility"] == 2.0
    assert m["fertility_segments"] == 2.0
    assert m["fertility_mean"] == 2.0
    assert m["chars_per_token"] == 2.5
    assert m["bytes_per_token"] == 6.0
    assert m["roundtrip_rate"] == 0.5
    assert m["vocab_utilization"] == 0.03
    assert m["orphan_mark_rate"] == 0.25


def test_script_coverage_finds_a_missing_visarga():
    vocab = enc("नेपाल", " दुख", "ु") + [b"\xe0", b"\xa4", b"\x83"]  # visarga only as byte pieces
    cov = script_coverage(vocab, {"set": "नपलदुखः"})["set"]
    assert cov["missing"] == "ः"
    assert cov["size"] == 7 and abs(cov["covered_share"] - 6 / 7) < 1e-9


def test_script_coverage_counts_a_whole_character_inside_a_byte_level_token():
    assert script_coverage(["ऊर्जा".encode()], {"s": "ऊ"})["s"]["missing"] == ""
    assert script_coverage(["ऊ".encode()[:2]], {"s": "ऊ"})["s"]["missing"] == "ऊ"


def test_charsets_are_nfc_and_assigned():
    import unicodedata

    assert unicodedata.normalize("NFC", NEPALI_CORE) == NEPALI_CORE
    assert len(set(NEPALI_CORE)) == len(NEPALI_CORE)
    assert set(NEPALI_CORE) <= set(DEVANAGARI_BLOCK)
    assert "ः" in NEPALI_CORE and "ऊ" in NEPALI_CORE and "\u0958" not in NEPALI_CORE


def test_byte_pieces_are_tokens_that_are_not_whole_characters():
    assert not is_byte_piece("ऊ".encode())
    assert is_byte_piece("ऊ".encode()[:1]) and is_byte_piece("ऊ".encode()[1:])
    tally = TokenTally()
    tally.add([1, 2, 3, 4], ["ऊ".encode()[:1], "ऊ".encode()[1:2], "ऊ".encode()[2:], b" a"])
    assert tally.byte_pieces == 3
