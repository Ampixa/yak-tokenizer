"""Adapters, the panel's per-text measurement and CLI spec parsing, without any downloads."""

from pathlib import Path

import pytest
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from yak_tokenizer.eval.adapters import (
    HFJsonAdapter,
    byte_symbol_table,
    detect_scheme,
    endsuffix_piece_bytes,
    parse_extra,
    spacemark_piece_bytes,
    wordpiece_piece_bytes,
)
from yak_tokenizer.eval.evalsets import REPO_ROOT, EvalText, read_segments
from yak_tokenizer.eval.panel import add_parity, measure_text, resolve_spec_paths

TEXTS = ["नेपाल सुन्दर देश हो।", "नेपालमा हिमाल छन्।", "Hello world, नेपाल!"] * 20


@pytest.fixture(scope="module")
def bytelevel_json(tmp_path_factory) -> Path:
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=400, show_progress=False, initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
    )
    tok.train_from_iterator(TEXTS, trainer)
    path = tmp_path_factory.mktemp("tok") / "tokenizer.json"
    tok.save(str(path))
    return path


def test_byte_symbol_table_matches_bytelevel_alphabet():
    table = byte_symbol_table()
    assert set(table) == set(pre_tokenizers.ByteLevel.alphabet())
    assert sorted(table.values()) == list(range(256))
    assert table["Ġ"] == 0x20 and table["Ċ"] == 0x0A


def test_piece_conversions():
    assert spacemark_piece_bytes("▁नेपाल") == " नेपाल".encode()
    assert spacemark_piece_bytes("<0xE0>") == b"\xe0"
    assert wordpiece_piece_bytes("##मा") == "मा".encode()
    assert wordpiece_piece_bytes("##") == b"##"


def test_detect_scheme_by_family():
    meta = Tokenizer(models.Unigram([("<unk>", 0.0), ("▁", -1.0), ("a", -2.0)], 0))
    meta.pre_tokenizer = pre_tokenizers.Metaspace()
    meta.decoder = decoders.Metaspace()
    assert detect_scheme(meta) == "spacemark"
    wp = Tokenizer(models.WordPiece({"[UNK]": 0, "नेपाल": 1, "##मा": 2}, unk_token="[UNK]"))
    wp.pre_tokenizer = pre_tokenizers.Whitespace()
    wp.decoder = decoders.WordPiece()
    assert detect_scheme(wp) == "wordpiece"


def test_hf_adapter_surfaces_rebuild_the_text(bytelevel_json):
    ad = HFJsonAdapter("tiny", bytelevel_json)
    assert ad.describe()["piece_scheme"] == "bytelevel"
    text = "नेपालमा हिमाल छन्।\nHello"
    ids = ad.encode(text)
    assert b"".join(ad.token_bytes(ids)) == text.encode()
    assert ad.decode(ids) == text
    assert "".join(ad.token_strings(ids)) == text
    assert ad.encode_many([text, "नेपाल"]) == [ids, ad.encode("नेपाल")]


def test_measure_text_joined_vs_segments(bytelevel_json):
    ad = HFJsonAdapter("tiny", bytelevel_json)
    segs = ("नेपाल सुन्दर देश हो।", "नेपालमा हिमाल छन्।")
    joined = EvalText("t/npi", "t", "npi", "flores", "x", segs, "joined", True, "eng")
    m, seg_tokens = measure_text(ad, joined)
    assert m["tokens"] == len(ad.encode("\n".join(segs)))
    assert m["tokens_segments"] == sum(seg_tokens) == sum(len(ad.encode(s)) for s in segs)
    assert m["words"] == 7
    assert m["fertility"] == m["tokens"] / 7
    assert m["chars"] == len("\n".join(segs))
    assert m["roundtrip_rate"] == 1.0 and m["roundtrip_joined"] is True
    assert m["orphan_mark_rate"] > 0  # GPT-2 style pre-tokenizer cuts at matras

    per_seg = EvalText("w", "w", None, "x", "x", segs, "segments")
    m2, _ = measure_text(ad, per_seg)
    assert m2["tokens"] == m["tokens_segments"]
    assert m2["chars"] == sum(len(s) for s in segs)


def test_parity_attached_to_aligned_texts(bytelevel_json):
    ad = HFJsonAdapter("tiny", bytelevel_json)
    npi = EvalText("s/npi", "s", "npi", "f", "x", ("नेपाल", "हिमाल"), "joined", True, "eng")
    eng = EvalText("s/eng", "s", "eng", "f", "x", ("Nepal", "Himal"), "joined", True, "eng")
    results, counts = {}, {}
    for t in (npi, eng):
        results[t.key], counts[t.key] = measure_text(ad, t)
    add_parity([npi, eng], results, counts)
    assert results["s/eng"]["parity"] == 1.0
    assert results["s/npi"]["parity"] == sum(counts["s/npi"]) / sum(counts["s/eng"])


def test_parse_extra_forms():
    assert parse_extra("yak64k=path/to/tokenizer.json") == {
        "name": "yak64k",
        "group": "added",
        "kind": "auto",
        "path": "path/to/tokenizer.json",
    }
    assert parse_extra("o=tiktoken:o200k_base")["encoding"] == "o200k_base"
    assert parse_extra("h=hf:org/repo")["repo"] == "org/repo"
    assert parse_extra("s=sp:x.model")["kind"] == "sentencepiece"
    with pytest.raises(ValueError):
        parse_extra("no-equals-sign")


def test_resolve_paths_against_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = resolve_spec_paths({"name": "x", "path": "configs/eval_sets.yaml"})
    assert spec["path"] == str(REPO_ROOT / "configs" / "eval_sets.yaml")
    with pytest.raises(FileNotFoundError):
        resolve_spec_paths({"name": "x", "path": "artifacts/does-not-exist/tokenizer.json"})


def test_read_segments_splits_on_newline_only(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("एक दुई\nतीन\n", encoding="utf-8")
    assert read_segments(p) == ["एक दुई", "तीन"]
    j = tmp_path / "a.jsonl"
    j.write_text('{"text": "a\\nb", "id": "1"}\n', encoding="utf-8")
    assert read_segments(j) == ["a\nb"]


def test_flores_files_are_line_aligned():
    base = REPO_ROOT / "data" / "eval" / "flores_plus" / "devtest"
    files = sorted(base.glob("*.txt"))
    if not files:
        pytest.skip("FLORES+ text is local-only; run scripts/eval_panel.py fetch")
    sizes = {f.name: len(read_segments(f)) for f in files}
    assert set(sizes.values()) == {1012}, sizes


def test_missing_wordpiece_decoder_is_attached(tmp_path):
    wp = Tokenizer(models.WordPiece({"[UNK]": 0, "नेपाल": 1, "##मा": 2, "।": 3}, unk_token="[UNK]"))
    wp.pre_tokenizer = pre_tokenizers.BertPreTokenizer()  # saved without a decoder
    path = tmp_path / "tokenizer.json"
    wp.save(str(path))
    ad = HFJsonAdapter("wp", path)
    ids = ad.encode("नेपालमा।")
    assert ad.describe()["decoder_added"] == "wordpiece"
    assert ad.decode(ids) == "नेपालमा ।"  # no "##" left behind; only spacing differs
    assert b"".join(ad.token_bytes(ids)) == "नेपालमा।".encode()


def test_end_of_word_suffix_pieces():
    assert endsuffix_piece_bytes("मा</w>") == "मा".encode()
    assert endsuffix_piece_bytes("नेपाल") == "नेपाल".encode()
