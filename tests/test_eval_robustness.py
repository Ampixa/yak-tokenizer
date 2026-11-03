"""Robustness probes and the whitespace-insensitive round-trip, on tiny fixtures."""

import pytest

from yak_tokenizer.eval.metrics import same_content
from yak_tokenizer.eval.robustness import ZWJ, ZWNJ, insert_joiner, run_probes, swap_vowel_length


def test_same_content_ignores_whitespace_only():
    assert same_content(" नेपालमा हिमाल छन् ।", "नेपालमा हिमाल छन्।")
    assert not same_content("नपालमा", "नेपालमा")  # a lost vowel sign is real loss


def test_joiners_go_after_virama_before_consonant():
    text, n = insert_joiner("क्षेत्र र छन्।", ZWJ)
    assert n == 2  # क्ष and त्र; the final छन् has no consonant after its virama
    assert text == f"क्{ZWJ}षेत्{ZWJ}र र छन्।"
    assert insert_joiner("प्र", ZWNJ)[0] == f"प्{ZWNJ}र"


def test_vowel_length_swaps_are_deterministic_and_counted():
    lines = ["नेपाली किताब पुस्तक हुन्छ", "मिति र सुरु"] * 10
    a, n_a = swap_vowel_length(lines)
    b, n_b = swap_vowel_length(lines)
    assert (a, n_a) == (b, n_b) and n_a > 0
    diff = sum(x != y for la, lb in zip(lines, a) for x, y in zip(la, lb))
    assert diff == n_a  # exactly one code point per swapped word
    assert [len(x) for x in a] == [len(x) for x in lines]


class CharAdapter:
    """One token per code point; drops ZWJ/ZWNJ, like a lossy normaliser would."""

    unk_id = None

    def encode_many(self, texts):
        return [[ord(c) for c in t if c not in (ZWJ, ZWNJ)] for t in texts]

    def decode_many(self, seqs):
        return ["".join(map(chr, s)) for s in seqs]


def test_run_probes_reports_ratios_and_roundtrip():
    npi = ["क्षेत्रमा छन्।", "नेपाली किताब।"]
    hin_raw = ["ज़रा"]  # precomposed ज़ is not NFC
    res = run_probes(CharAdapter(), npi, hin_raw)
    assert set(res) == {"not_nfc", "zwj", "zwnj", "vowel_length", "pipe_danda"}
    assert res["zwj"]["token_ratio"] == 1.0  # joiners dropped: no extra tokens...
    assert res["zwj"]["roundtrip_rate"] == 0.5  # ...but the sentence with joiners is lost
    assert res["zwj"]["roundtrip_content_rate"] == 0.5  # joiners are not whitespace
    assert res["pipe_danda"]["token_ratio"] == 1.0 and res["pipe_danda"]["roundtrip_rate"] == 1.0
    assert res["not_nfc"]["changed"] == pytest.approx(1 / 3)
    assert res["not_nfc"]["token_ratio"] == pytest.approx(3 / 4)  # NFC decomposes ज़ into 2
