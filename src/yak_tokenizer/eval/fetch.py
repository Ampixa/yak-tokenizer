"""Build the small evaluation sets under ``data/eval/`` from their Hugging Face sources.

Every builder is deterministic (fixed order or a fixed seed) and records what it wrote in
``data/eval/MANIFEST.tsv``: path, segments, words, chars, bytes, sha256, source repo, the resolved
source revision and the license. Each redistributable file is capped at 2 MB.

FLORES+ is special: its gating terms ask users not to re-host it anywhere web crawlers can reach.
Its text files are therefore written locally only; ``data/eval/flores_plus/.gitignore`` keeps them
out of git, and anyone with access can rebuild them byte-identically with ``fetch_flores``.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # the xet backend stalls on this network

from .evalsets import REPO_ROOT

EVAL_DIR = REPO_ROOT / "data" / "eval"
MANIFEST = EVAL_DIR / "MANIFEST.tsv"
BYTE_CAP = 2_000_000

FLORES_REPO = "openlanguagedata/flores_plus"
FLORES_SPLITS = ("dev", "devtest")
FLORES_LANGS = (
    "npi_Deva",
    "eng_Latn",
    "hin_Deva",
    "mai_Deva",
    "bho_Deva",
    "san_Deva",
    "awa_Deva",
    "mag_Deva",
    "bod_Tibt",
    "sat_Olck",
)
_FLORES_IGNORE = """\
# FLORES+ gating terms: "I agree not to re-host FLORES+ in places where it could be picked up
# by web crawlers". The text stays local; rebuild it with `uv run python scripts/eval_panel.py fetch`.
# MANIFEST.tsv one level up records the sha256 of every file for reproducibility.
dev/
devtest/
"""

MANIFEST_FIELDS = (
    "path",
    "segments",
    "words",
    "chars",
    "bytes",
    "sha256",
    "source",
    "revision",
    "license",
)


def _hub_file(repo: str, filename: str, revision: str | None = None) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo, filename, repo_type="dataset", revision=revision))


def _snapshot_revision(path: Path) -> str:
    parts = path.parts
    return parts[parts.index("snapshots") + 1] if "snapshots" in parts else ""


def _read_parquet(repo: str, filename: str, columns: list[str] | None = None) -> tuple[list, str]:
    import pyarrow.parquet as pq

    path = _hub_file(repo, filename)
    return pq.read_table(path, columns=columns).to_pylist(), _snapshot_revision(path)


def _stats(path: Path, segments: list[str]) -> dict:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "segments": len(segments),
        "words": sum(len(s.split()) for s in segments),
        "chars": sum(len(s) for s in segments),
        "bytes": sum(len(s.encode("utf-8")) for s in segments),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _write_lines(path: Path, lines: list[str]) -> None:
    bad = [i for i, s in enumerate(lines) if "\n" in s or "\r" in s]
    if bad:
        raise ValueError(f"{path}: segments {bad[:5]} contain line breaks")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(rec, ensure_ascii=False) + "\n" for rec in records)


def _cap(records: list[dict], cap: int = BYTE_CAP) -> list[dict]:
    """Keep records in order until the JSONL payload would pass ``cap`` bytes."""
    out, size = [], 0
    for rec in records:
        size += len(json.dumps(rec, ensure_ascii=False).encode("utf-8")) + 1
        if size > cap:
            break
        out.append(rec)
    return out


def fetch_flores(
    langs: tuple[str, ...] = FLORES_LANGS,
    splits: tuple[str, ...] = FLORES_SPLITS,
    out_dir: Path = EVAL_DIR / "flores_plus",
    revision: str | None = None,
) -> list[dict]:
    """Write ``<out_dir>/<split>/<lang>.txt``, one sentence per line, line-aligned by FLORES id."""
    rows_out = []
    for split in splits:
        reference_ids = None
        for lang in langs:
            src = _hub_file(FLORES_REPO, f"{split}/{lang}.jsonl", revision)
            rows = [json.loads(x) for x in src.read_text(encoding="utf-8").split("\n") if x.strip()]
            rows.sort(key=lambda r: int(r["id"]))
            ids = [int(r["id"]) for r in rows]
            if ids != list(range(len(ids))):
                raise ValueError(f"{split}/{lang}: ids are not 0..n-1")
            if reference_ids is None:
                reference_ids = ids
            elif ids != reference_ids:
                raise ValueError(f"{split}/{lang}: not aligned with {langs[0]}")
            lines = [r["text"] for r in rows]
            dest = out_dir / split / f"{lang}.txt"
            _write_lines(dest, lines)
            rows_out.append(
                _stats(dest, lines)
                | {
                    "source": FLORES_REPO,
                    "revision": _snapshot_revision(src),
                    "license": "CC-BY-SA-4.0",
                }
            )
    (out_dir / ".gitignore").write_text(_FLORES_IGNORE, encoding="utf-8")
    return rows_out


def build_code_sets(out_dir: Path = EVAL_DIR / "code") -> list[dict]:
    """HumanEval prompts + canonical solutions (MIT) and the MBPP test split (CC BY 4.0)."""
    out = []
    rows, rev = _read_parquet(
        "openai/openai_humaneval", "openai_humaneval/test-00000-of-00001.parquet"
    )
    recs = _cap([{"text": r["prompt"] + r["canonical_solution"], "id": r["task_id"]} for r in rows])
    dest = out_dir / "humaneval.jsonl"
    _write_jsonl(dest, recs)
    out.append(
        _stats(dest, [r["text"] for r in recs])
        | {"source": "openai/openai_humaneval", "revision": rev, "license": "MIT"}
    )

    rows, rev = _read_parquet("google-research-datasets/mbpp", "full/test-00000-of-00001.parquet")
    recs = _cap(
        [{"text": f"# {r['text']}\n{r['code']}", "id": f"mbpp/{r['task_id']}"} for r in rows]
    )
    dest = out_dir / "mbpp.jsonl"
    _write_jsonl(dest, recs)
    out.append(
        _stats(dest, [r["text"] for r in recs])
        | {"source": "google-research-datasets/mbpp", "revision": rev, "license": "CC-BY-4.0"}
    )
    return out


MATH_SUBJECTS = (
    "algebra",
    "counting_and_probability",
    "geometry",
    "intermediate_algebra",
    "number_theory",
    "prealgebra",
    "precalculus",
)


def build_math_sets(out_dir: Path = EVAL_DIR / "math", per_subject: int = 100) -> list[dict]:
    """GSM8K test (MIT) and a seeded sample of the MATH test set with its LaTeX (MIT)."""
    out = []
    rows, rev = _read_parquet("openai/gsm8k", "main/test-00000-of-00001.parquet")
    recs = [
        {"text": f"{r['question']}\n{r['answer']}", "id": f"gsm8k/test/{i}"}
        for i, r in enumerate(rows)
    ]
    recs = _cap(recs)
    dest = out_dir / "gsm8k.jsonl"
    _write_jsonl(dest, recs)
    out.append(
        _stats(dest, [r["text"] for r in recs])
        | {"source": "openai/gsm8k", "revision": rev, "license": "MIT"}
    )

    recs, rev = [], ""
    for subject in MATH_SUBJECTS:
        rows, rev = _read_parquet(
            "EleutherAI/hendrycks_math", f"{subject}/test-00000-of-00001.parquet"
        )
        picked = sorted(random.Random(f"yak-math-{subject}").sample(range(len(rows)), per_subject))
        recs += [
            {"text": f"{rows[i]['problem']}\n{rows[i]['solution']}", "id": f"math/{subject}/{i}"}
            for i in picked
        ]
    recs = _cap(recs)
    dest = out_dir / "math_latex.jsonl"
    _write_jsonl(dest, recs)
    out.append(
        _stats(dest, [r["text"] for r in recs])
        | {"source": "EleutherAI/hendrycks_math", "revision": rev, "license": "MIT"}
    )
    return out


def build_romanized(out_dir: Path = EVAL_DIR / "npi_latn") -> list[dict]:
    """Validation split of Saugatkafley/Nepali-Roman-Transliteration (MIT): word pairs.

    Two line-aligned word lists: the Romanized spelling and its Devanagari original.
    """
    rows, rev = _read_parquet(
        "Saugatkafley/Nepali-Roman-Transliteration", "data/validation-00000-of-00001.parquet"
    )
    pairs = [(r["english word"].strip(), r["native word"].strip()) for r in rows]
    pairs = [(a, b) for a, b in pairs if a and b and " " not in a and " " not in b]
    out = []
    for name, idx in (("roman_words.txt", 0), ("roman_words_deva.txt", 1)):
        lines = [p[idx] for p in pairs]
        dest = out_dir / name
        _write_lines(dest, lines)
        out.append(
            _stats(dest, lines)
            | {
                "source": "Saugatkafley/Nepali-Roman-Transliteration",
                "revision": rev,
                "license": "MIT",
            }
        )
    return out


def build_everyday(out_dir: Path = EVAL_DIR / "npi_everyday") -> list[dict]:
    """Human-written Nepali prompts and answers from the Aya dataset (Apache-2.0), seeded sample."""
    import pyarrow.parquet as pq

    src = _hub_file("CohereLabs/aya_dataset", "data/train-00000-of-00001.parquet")
    table = pq.read_table(
        src, columns=["inputs", "targets", "language"], filters=[("language", "==", "Nepali")]
    )
    rows = table.to_pylist()
    order = list(range(len(rows)))
    random.Random("yak-aya-npi").shuffle(order)
    recs = [
        {"text": f"{rows[i]['inputs'].strip()}\n{rows[i]['targets'].strip()}", "id": f"aya/npi/{i}"}
        for i in order
    ]
    recs = _cap(recs)
    dest = out_dir / "aya_npi.jsonl"
    _write_jsonl(dest, recs)
    return [
        _stats(dest, [r["text"] for r in recs])
        | {
            "source": "CohereLabs/aya_dataset",
            "revision": _snapshot_revision(src),
            "license": "Apache-2.0",
        }
    ]


def write_manifest(rows: list[dict], path: Path = MANIFEST) -> None:
    """Merge ``rows`` into the manifest, keyed by path."""
    existing: dict[str, dict] = {}
    if path.exists():
        lines = path.read_text(encoding="utf-8").split("\n")
        header = lines[0].split("\t")
        for line in lines[1:]:
            if line.strip():
                rec = dict(zip(header, line.split("\t")))
                existing[rec["path"]] = rec
    for row in rows:
        existing[row["path"]] = {k: str(row.get(k, "")) for k in MANIFEST_FIELDS}
    body = ["\t".join(MANIFEST_FIELDS)]
    body += ["\t".join(existing[p].get(k, "") for k in MANIFEST_FIELDS) for p in sorted(existing)]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


BUILDERS = {
    "flores": fetch_flores,
    "romanized": build_romanized,
    "everyday": build_everyday,
    "code": build_code_sets,
    "math": build_math_sets,
}
OPTIONAL = ("code", "math")


def fetch_all(which: list[str] | None = None) -> list[dict]:
    """Run the named builders; by default every builder except the optional code and math sets."""
    rows: list[dict] = []
    for name in which or [b for b in BUILDERS if b not in OPTIONAL]:
        rows += BUILDERS[name]()
    write_manifest(rows)
    return rows
