"""Render ``docs/RESULTS.md`` from the per-tokenizer JSON files in ``artifacts/eval/``.

The whole file is generated; edit this template, not the markdown.
"""

from __future__ import annotations

import unicodedata
from datetime import date
from pathlib import Path

from .evalsets import REPO_ROOT, load_registry
from .panel import OUT_DIR, load_records

RESULTS_MD = REPO_ROOT / "docs" / "RESULTS.md"
NPI = "flores_devtest/npi_Deva"


def _f(x, digits: int = 2) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def _pct(x, digits: int = 1) -> str:
    return "–" if x is None else f"{100 * x:.{digits}f}%"


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _metric(rec: dict, key: str, field: str):
    return ((rec.get("results") or {}).get(key) or {}).get(field)


def lossless(rec: dict, key: str) -> bool:
    """No unknown tokens and every segment's content survives the round-trip."""
    m = ((rec.get("results") or {}).get(key)) or {}
    return not m.get("unk_rate") and m.get("roundtrip_content_rate") in (None, 1.0)


def _dag(rec: dict, *keys: str) -> str:
    """Mark a number measured on text the tokenizer does not represent losslessly."""
    return " †" if any(not lossless(rec, k) for k in keys) else ""


def _pooled(rec: dict, keys: list[str], num: str, den: str):
    """Ratio of summed fields over several texts, e.g. chars/token over code sets."""
    res = rec.get("results") or {}
    n = sum(res[k][num] for k in keys if k in res)
    d = sum(res[k][den] for k in keys if k in res)
    return n / d if d else None


def roundtrip_overall(rec: dict, field: str = "roundtrip_rate") -> float | None:
    """Share of all eval segments (every panel text) that round-trip."""
    res = rec.get("results") or {}
    segs = sum(m["segments"] for m in res.values())
    ok = sum(round(m[field] * m["segments"]) for m in res.values() if m.get(field) is not None)
    return ok / segs if segs else None


def gate_rows(
    records: dict[str, dict], published: dict[str, float], text: str, tol: float
) -> list[dict]:
    rows = []
    for name, pub in published.items():
        rec = records.get(name)
        row = {"name": name, "published": pub, "ok": False}
        if rec and rec.get("status") == "ok" and text in rec.get("results", {}):
            m = rec["results"][text]
            row |= {
                "joined": m["fertility"],
                "segments": m["fertility_segments"],
                "mean": m["fertility_mean"],
                "bos": m["fertility_segments"] + m["segments"] / m["words"],
            }
            row["ok"] = abs(m["fertility"] - pub) <= tol
        rows.append(row)
    return rows


def _gate_table(rows: list[dict], tol: float) -> list[str]:
    def mark(x, pub):
        if x is None:
            return "–"
        return f"{x:.3f} ({x - pub:+.3f}{'' if abs(x - pub) <= tol else ' ✗'})"

    out = [
        (
            "| Tokenizer | Published | **Ours: whole file** | Δ | Pass | Per-line sum | "
            "Per-line mean | Per-line sum + 1 BOS/line |"
        ),
        "|---|---:|---:|---:|:---:|---:|---:|---:|",
    ]
    for r in rows:
        if "joined" not in r:
            out.append(f"| {r['name']} | {r['published']:.2f} | not measured | | ✗ | | | |")
            continue
        out.append(
            f"| {r['name']} | {r['published']:.2f} | **{r['joined']:.3f}** | "
            f"{r['joined'] - r['published']:+.3f} | {'✓' if r['ok'] else '✗'} | "
            f"{mark(r['segments'], r['published'])} | {mark(r['mean'], r['published'])} | "
            f"{mark(r['bos'], r['published'])} |"
        )
    return out


def missing_chars(rec: dict, charset: str = "nepali_core") -> str:
    """Characters with no token of their own, combining marks shown on a dotted circle."""
    cov = ((rec.get("coverage") or {}).get(charset)) or None
    if cov is None:
        return "–"
    miss = cov["missing"]
    if not miss:
        return "0"
    shown = " ".join(f"◌{c}" if unicodedata.category(c).startswith("M") else c for c in miss)
    return f"{len(miss)}: {_cell(shown)}"


def _label(rec: dict) -> str:
    """Yak builds (and tokenizers added with --add) are bold so they stand out."""
    return f"**{rec['name']}**" if rec.get("group") in ("added", "yak") else rec["name"]


def _leaderboard(ranked: list[dict]) -> list[str]:
    out = [
        (
            "| # | Tokenizer | Vocab | npi | npi per line | eng | hin | mai | npi parity | "
            "npi bytes/tok | orphan marks (npi) | unk (npi) | round-trip exact · content | "
            "Nepali chars without a token |"
        ),
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(ranked, 1):
        out.append(
            f"| {i} | {_label(r)} | {r['vocab_size']:,} | "
            f"**{_f(_metric(r, NPI, 'fertility'), 3)}**{_dag(r, NPI)} | "
            f"{_f(_metric(r, NPI, 'fertility_segments'), 3)} | "
            f"{_f(_metric(r, 'flores_devtest/eng_Latn', 'fertility'), 3)}"
            f"{_dag(r, 'flores_devtest/eng_Latn')} | "
            f"{_f(_metric(r, 'flores_devtest/hin_Deva', 'fertility'), 3)}"
            f"{_dag(r, 'flores_devtest/hin_Deva')} | "
            f"{_f(_metric(r, 'flores_devtest/mai_Deva', 'fertility'), 3)}"
            f"{_dag(r, 'flores_devtest/mai_Deva')} | "
            f"{_f(_metric(r, NPI, 'parity'))} | {_f(_metric(r, NPI, 'bytes_per_token'))} | "
            f"{_pct(_metric(r, NPI, 'orphan_mark_rate'))} | {_pct(_metric(r, NPI, 'unk_rate'), 2)} | "
            f"{_pct(roundtrip_overall(r))} · "
            f"{_pct(roundtrip_overall(r, 'roundtrip_content_rate'))} | {missing_chars(r)} |"
        )
    return out


PROBE_LABELS = {
    "not_nfc": "raw non-NFC hin",
    "zwj": "ZWJ after virama",
    "zwnj": "ZWNJ after virama",
    "vowel_length": "ि/ी ु/ू typos",
    "pipe_danda": "danda typed as pipe",
}


def _robustness_table(ranked: list[dict]) -> list[str]:
    probes = list(PROBE_LABELS)
    out = [
        "| Tokenizer | " + " | ".join(PROBE_LABELS[p] for p in probes) + " |",
        "|---|" + "---:|" * len(probes),
    ]
    for r in ranked:
        rob = r.get("robustness") or {}
        cells = []
        for p in probes:
            m = rob.get(p)
            cells.append(
                "–"
                if not m
                else f"{_f(m['token_ratio'], 3)} · {_pct(m.get('roundtrip_content_rate'), 0)}"
            )
        out.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    return out


def _languages_table(ranked: list[dict]) -> list[str]:
    langs = ["bho_Deva", "san_Deva", "awa_Deva", "mag_Deva", "sat_Olck"]
    out = [
        "| Tokenizer | "
        + " | ".join(lang.split("_")[0] for lang in langs)
        + " | bod chars/tok | hin parity | npi chars/tok | npi vocab used | npi mid-char | "
        "npi byte pieces | everyday npi byte pieces | Devanagari block without a token | "
        "npi Rényi eff. |",
        "|---|" + "---:|" * (len(langs) + 9),
    ]
    for r in ranked:
        cells = [
            _f(_metric(r, f"flores_devtest/{lang}", "fertility"), 3)
            + _dag(r, f"flores_devtest/{lang}")
            for lang in langs
        ]
        cells += [
            _f(_metric(r, "flores_devtest/bod_Tibt", "chars_per_token"))
            + _dag(r, "flores_devtest/bod_Tibt"),
            _f(_metric(r, "flores_devtest/hin_Deva", "parity")),
            _f(_metric(r, NPI, "chars_per_token")),
            _pct(_metric(r, NPI, "vocab_utilization")),
            _pct(_metric(r, NPI, "mid_char_rate")),
            _pct(_metric(r, NPI, "byte_piece_rate"), 2),
            _pct(_metric(r, "npi_everyday_aya", "byte_piece_rate"), 2),
            _block_missing(r),
            _f(_metric(r, NPI, "renyi_efficiency"), 3),
        ]
        out.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    return out


def _block_missing(rec: dict) -> str:
    cov = ((rec.get("coverage") or {}).get("devanagari_block")) or None
    return "–" if cov is None else f"{len(cov['missing'])} / {cov['size']}"


NEPAL_LANGS = ("aph", "dhi", "gvr", "kle", "kyv", "lbr", "lif", "mgp", "new", "rav", "suz", "taj", "thl", "thr")


def nepal_summary(rec: dict) -> dict:
    """Mean fertility over the languages-of-Nepal sets, and the worst (largest) token parity
    against Nepali on the aligned segments, with the language it belongs to."""
    fert = [_metric(rec, f"nepal_langs/{lang}", "fertility") for lang in NEPAL_LANGS]
    fert = [x for x in fert if x is not None]
    par = {
        lang: _metric(rec, f"nepal_langs_aligned/{lang}", "parity")
        for lang in NEPAL_LANGS
    }
    par = {k: v for k, v in par.items() if v is not None}
    worst = max(par.items(), key=lambda kv: kv[1]) if par else (None, None)
    return {
        "mean_fertility": sum(fert) / len(fert) if fert else None,
        "mean_parity": sum(par.values()) / len(par) if par else None,
        "worst_parity": worst[1],
        "worst_lang": worst[0],
    }


def _nepal_langs_table(ranked: list[dict]) -> list[str]:
    out = [
        "| Tokenizer | "
        + " | ".join(NEPAL_LANGS)
        + " | mean fertility | mean parity vs npi | worst parity vs npi |",
        "|---|" + "---:|" * (len(NEPAL_LANGS) + 3),
    ]
    for r in ranked:
        cells = [
            _f(_metric(r, f"nepal_langs/{lang}", "fertility"), 2) + _dag(r, f"nepal_langs/{lang}")
            for lang in NEPAL_LANGS
        ]
        s = nepal_summary(r)
        worst = "–" if s["worst_parity"] is None else f"{s['worst_parity']:.2f} ({s['worst_lang']})"
        cells += [_f(s["mean_fertility"], 3), _f(s["mean_parity"]), worst]
        out.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    return out


def _nepal_section(ranked: list[dict]) -> list[str]:
    """The languages-of-Nepal table, only for tokenizers measured on those sets."""
    measured = [r for r in ranked if any(_metric(r, f"nepal_langs/{x}", "fertility") is not None for x in NEPAL_LANGS)]
    if not measured:
        return []
    return [
        "## Languages of Nepal (held-out text)",
        "",
        (
            "Fertility on 500 held-out segments per language: Athpariya (aph), Dhimal (dhi), Gurung (gvr), "
            "Kulung (kle), Kayort (kyv), Lohorung (lbr), Limbu (lif), Magar (mgp), Newar (new), "
            "Sampang (rav), Sunuwar (suz), Tamang (taj), Tharu Dangaura (thl), Tharu Rana (thr). "
            "Parity is tokens of the same 300 line-aligned segments divided by Nepali tokens (1.00 = "
            "as cheap as Nepali). This text cannot be redistributed, so these sets are not in the "
            "repository and a public run skips them."
        ),
        "",
        *_nepal_langs_table(measured),
        "",
    ]


CODE = ["code_humaneval", "code_mbpp"]
MATH = ["math_gsm8k", "math_latex"]


def _has_code_math(ranked: list[dict]) -> bool:
    """Code and math are optional (``run --code-math``); their columns appear only when measured."""
    return any(k in r.get("results", {}) for r in ranked for k in CODE + MATH)


def _domains_table(ranked: list[dict]) -> list[str]:
    code_math = _has_code_math(ranked)
    out = [
        (
            "| Tokenizer | everyday npi (Aya) fertility | Devanagari words fertility | "
            "Romanized words fertility |"
            + (" code chars/tok | math chars/tok |" if code_math else "")
            + " eng chars/tok |"
        ),
        "|---|---:|---:|---:|" + ("---:|---:|" if code_math else "") + "---:|",
    ]
    for r in ranked:
        cm = (
            f" {_f(_pooled(r, CODE, 'chars', 'tokens'))}{_dag(r, *CODE)} |"
            f" {_f(_pooled(r, MATH, 'chars', 'tokens'))}{_dag(r, *MATH)} |"
            if code_math
            else ""
        )
        out.append(
            f"| {r['name']} | {_f(_metric(r, 'npi_everyday_aya', 'fertility'), 3)}"
            f"{_dag(r, 'npi_everyday_aya')} | "
            f"{_f(_metric(r, 'npi_latn_words_deva', 'fertility'), 3)}"
            f"{_dag(r, 'npi_latn_words_deva')} | "
            f"{_f(_metric(r, 'npi_latn_words', 'fertility'), 3)}{_dag(r, 'npi_latn_words')} |"
            f"{cm} "
            f"{_f(_metric(r, 'flores_devtest/eng_Latn', 'chars_per_token'))}"
            f"{_dag(r, 'flores_devtest/eng_Latn')} |"
        )
    return out


def _failed_table(failed: list[dict]) -> list[str]:
    out = ["| Tokenizer | Source | Reason |", "|---|---|---|"]
    for r in failed:
        spec = r.get("spec") or {}
        src = spec.get("repo") or spec.get("path") or spec.get("encoding") or ""
        err = (r.get("error") or "unknown").strip().split("\n")[-1]
        out.append(f"| {r['name']} | {_cell(src)} | {_cell(err[:220])} |")
    return out


def _sets_table(registry: dict, any_rec: dict | None) -> list[str]:
    out = [
        "| Text | Count mode | Segments | Words | Bytes | License | Source |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    res = (any_rec or {}).get("results") or {}
    for set_id, spec in registry["sets"].items():
        keys = [f"{set_id}/{lang}" for lang in spec["langs"]] if "langs" in spec else [set_id]
        if not spec.get("panel", True) and not any(k in res for k in keys):
            continue
        for key in keys:
            m = res.get(key, {})
            out.append(
                f"| {key} | {spec.get('count', 'segments')} | {m.get('segments', '–')} | "
                f"{m.get('words', '–')} | {m.get('bytes', '–')} | {spec.get('license', '')} | "
                f"{_cell(spec.get('source', ''))} |"
            )
    return out


def render(panel_cfg: dict, records: list[dict], registry: dict) -> str:
    gate = panel_cfg["validity_gate"]
    tol, text = gate["tolerance"], gate["text"]
    by_name = {r["name"]: r for r in records}
    ok = [r for r in records if r.get("status") == "ok"]
    failed = [r for r in records if r.get("status") != "ok"]
    ranked = sorted(
        ok, key=lambda r: (_metric(r, NPI, "fertility") is None, _metric(r, NPI, "fertility") or 0)
    )
    main_rows = gate_rows(by_name, gate["published"], text, tol)
    side_rows = gate_rows(by_name, gate.get("secondary", {}), text, tol)
    n_pass = sum(r["ok"] for r in main_rows)
    seg_pass = sum(
        1 for r in main_rows if "segments" in r and abs(r["segments"] - r["published"]) <= tol
    )
    npi_rec = next((r for r in ok if text in r.get("results", {})), None)
    npi_m = npi_rec["results"][text] if npi_rec else {}
    code_math = _has_code_math(ranked)

    lines = [
        "# Yak tokenizer results",
        "",
        (
            f"> Generated on {date.today().isoformat()} by `uv run python scripts/eval_panel.py run` "
            "from `artifacts/eval/*.json`."
        ),
        "> Do not edit by hand: the template is `src/yak_tokenizer/eval/report.py`.",
        "",
        "## Definitions",
        "",
        "Every tokenizer is fed the same NFC text and never adds special tokens (no BOS/EOS).",
        "Exact formulas are in `src/yak_tokenizer/eval/metrics.py`.",
        "",
        (
            "- **Fertility** = tokens / whitespace words, where words = `len(text.split())` (Python "
            "`str.split()`). On FLORES the token count comes from encoding the **whole file as one "
            "string**, sentences joined by `\\n` (no trailing newline). This is the definition that "
            "reproduces the published numbers (see the gate below). Sets of words or documents are "
            "encoded one segment at a time and summed."
        ),
        (
            "- **Parity** = total tokens of a language / total tokens of English on the 1,012 "
            "line-aligned FLORES+ devtest sentences, each sentence encoded on its own."
        ),
        (
            "- **Bytes/tok** and **chars/tok** = UTF-8 bytes or code points of the counted text / tokens "
            "(higher is better)."
        ),
        (
            "- **Orphan marks** = share of tokens whose first character is a combining mark (Unicode "
            "Mn/Mc/Me: matras, virama, nukta, anusvara, chandrabindu, visarga), i.e. tokens cut off "
            "their consonant. **Mid-char** = share of tokens that start inside a UTF-8 character "
            "(byte fragments)."
        ),
        (
            "- **Round-trip** = share of all eval segments (every panel text) where "
            "`decode(encode(x)) == x`, shown as *exact · content*. *Content* compares the strings "
            "with all whitespace removed, so decoders that only add a prefix space or put spaces "
            "around punctuation (WordPiece) pass, while lost characters (unknown tokens, "
            "normalisation) fail. **unk** = share of tokens that are the unknown token."
        ),
        (
            "- **Vocab used** = distinct token ids in the text / vocab size. **Rényi eff.** = Rényi "
            "entropy (α = 2.5) of the token distribution / log(vocab size)."
        ),
        (
            "- **Nepali chars without a token** = characters of everyday Nepali (independent "
            "vowels, consonants, vowel signs, ँ ं ः ़ ् ऽ, । ॥, digits, ॐ; "
            "`NEPALI_CORE` in `metrics.py`) that no vocabulary token contains whole. Such a "
            "character is still encoded, as unknown or as byte-fallback pieces, but never inside a "
            "learned word: with byte fallback, ऊ alone costs 3 tokens and still round-trips, so "
            "unk and round-trip do not show it. **Devanagari block without a token** is the same "
            "check over every assigned code point U+0900-U+097F (Vedic and Sindhi letters "
            "included). **Byte pieces** = share of tokens that are not whole UTF-8 characters."
        ),
        "- **Vocab** counts every id, including added and special tokens.",
        "",
        "## Validity gate",
        "",
        (
            f"Text: `{text}` (FLORES+ devtest, {npi_m.get('segments', '–')} sentences, "
            f"{npi_m.get('words', '–')} words, {npi_m.get('chars', '–')} chars, "
            f"{npi_m.get('bytes', '–')} bytes with the joining newlines). Target: within ±{tol} of "
            f"{gate['source']}."
        ),
        "",
        f"**Result: {n_pass}/{len(main_rows)} reproduced.**",
        "",
        *_gate_table(main_rows, tol),
        "",
        (
            "**Definition that matches:** tokens of the whole devtest file encoded in one call "
            "(sentences joined by `\\n`, so line breaks are tokenized too), divided by "
            "`str.split()` words, no special tokens. It is the corpus ratio of the file, not a mean "
            "over sentences. Alternatives miss:"
        ),
        "",
        (
            f"- Encoding each sentence separately and summing drops the ~1,011 newline tokens. "
            f"It reproduces only {seg_pass}/{len(main_rows)} numbers (GPT-2 and cl100k fall about "
            "0.05 low). This is the variant behind the quick check gpt2 10.919 / cl100k 6.926 / "
            "o200k 2.320."
        ),
        "- A mean of per-sentence ratios over-weights short sentences and misses GPT-2 by +0.035.",
        (
            "- Adding one BOS per sentence (the HF default for Llama-3) gives the whole-file count "
            "only for tokenizers that spend exactly one token per newline (GPT-2, cl100k, Arkios). "
            "It misses o200k and Llama-3, which merge `।` with the newline, by about +0.05."
        ),
        (
            "- FLORES+ vs FLORES-200 does not matter here. FLORES+ `npi_Deva` devtest has exactly the "
            "word, char and byte counts the Arkios harness logged for FLORES-200 (18,701 / 127,914 / "
            "340,483), and NFC is a no-op on it. NFC does change `hin_Deva`, which is one reason we "
            "always NFC first."
        ),
        "",
        "Cross-checks against other numbers in the same paper (not part of the gate):",
        "",
        *_gate_table(side_rows, tol),
        "",
        "## Leaderboard: Nepali FLORES+ devtest",
        "",
        (
            "Sorted by Nepali fertility (lower is better). Fertility columns are FLORES+ devtest, "
            "whole-file definition. *npi per line* encodes each sentence on its own and sums, so "
            "newlines are not counted; tokenizers that spend a token per newline gain ~0.05 there. "
            "Parity is vs English. Round-trip covers every panel text."
        ),
        "",
        *_leaderboard(ranked),
        "",
        (
            "† = not lossless on that text: the tokenizer emits unknown tokens or loses "
            "characters (content round-trip below 100%), which makes its numbers look better "
            "than they are."
        ),
        "",
        "## Other languages of Nepal and Nepali-specific diagnostics",
        "",
        (
            "FLORES+ devtest fertility for Bhojpuri, Sanskrit, Awadhi, Magahi and Santali (Ol Chiki). "
            "Tibetan has no spaces between words, so it gets chars/token instead."
        ),
        "",
        *_languages_table(ranked),
        "",
        *_nepal_section(ranked),
        "## Domains: everyday and Romanized Nepali" + (", code, math" if code_math else ""),
        "",
        (
            "Everyday Nepali is human-written prompts and answers from the Aya dataset. The word lists "
            "are 2,804 Nepali words in Romanized and Devanagari spelling (one word per segment)."
            + (
                " Code is HumanEval + MBPP and math is GSM8K + MATH, as pooled chars/token."
                if code_math
                else ""
            )
        ),
        "",
        *_domains_table(ranked),
        "",
        "## Robustness probes",
        "",
        (
            "Each cell is *token ratio · content round-trip* on FLORES+ devtest sentences rewritten "
            "the way Nepali text often arrives (`src/yak_tokenizer/eval/robustness.py`). A token "
            "ratio of 1.000 means the variant costs no extra tokens. *raw non-NFC hin* is the "
            "published Hindi file (precomposed nukta letters) against its NFC form; plain NFD is "
            "not used because it changes 1 character of the NFC Nepali devtest. The other probes "
            "rewrite the Nepali devtest: a ZWJ or ZWNJ after every virama before a consonant, "
            "short/long vowel-sign swaps in 20% of eligible words (fixed seed), and every danda "
            "typed as a pipe."
        ),
        "",
        *_robustness_table(ranked),
        "",
        "## Failed or skipped baselines",
        "",
        *(_failed_table(failed) if failed else ["None."]),
        "",
        "Loading notes:",
        "",
        (
            "- `krutrim-1`: its `tokenizer.json` uses ByteLevel with `add_prefix_space=true`, so "
            "every decode gains a leading space. Exact round-trip is 0% for that reason alone; "
            "content round-trip is unaffected."
        ),
        (
            "- `nepberta` ships only `vocab.txt`. AutoTokenizer's BERT defaults would also strip "
            "accents, deleting Devanagari vowel signs and the virama (नेपालमा -> नपालमा). Its "
            "vocab is full of those marks, so it is loaded with `strip_accents=false`."
        ),
        (
            "- Sarvam-M and Krutrim-2 use Mistral's Tekken tokenizer, Qwen3 uses Qwen2.5's, "
            "sarvam-30b is very close to Gemma-3, and gpt-oss (o200k_harmony) tokenizes text "
            "like o200k, so their rows match."
        ),
        "",
        "## Eval sets",
        "",
        (
            "Built by `uv run python scripts/eval_panel.py fetch`. Licenses and attribution are in "
            "`data/eval/SOURCES.md` and checksums in `data/eval/MANIFEST.tsv`. FLORES+ text is kept "
            "out of git, because its gating terms forbid re-hosting it where crawlers can reach it."
        ),
        "",
        *_sets_table(registry, npi_rec),
        "",
    ]
    return "\n".join(lines)


def write_results(panel_cfg: dict, out_dir: Path = OUT_DIR, path: Path = RESULTS_MD) -> Path:
    records = load_records(out_dir)
    path.write_text(render(panel_cfg, records, load_registry()), encoding="utf-8")
    return path
