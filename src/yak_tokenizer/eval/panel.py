"""Run the tokenizer panel: every tokenizer on every eval text, one JSON file per tokenizer.

Each tokenizer is measured in its own child process (``python -m yak_tokenizer.eval.panel``),
one at a time by default. Memory goes back to the OS between tokenizers, and a crash in one
tokenizer library cannot take down the run. Results are cached by a fingerprint of the
tokenizer spec and the eval files, so re-running only measures what changed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import resource
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .evalsets import (
    DEFAULT_REGISTRY,
    REPO_ROOT,
    EvalText,
    load_registry,
    load_texts,
    read_segments,
    set_paths,
)
from .metrics import (
    DEVANAGARI_BLOCK,
    NEPALI_CORE,
    TokenTally,
    iter_chunks,
    mean_ratio,
    parity,
    same_content,
    script_coverage,
    summarize,
)

HARNESS_VERSION = "4"
PANEL_CONFIG = REPO_ROOT / "configs" / "eval_panel.yaml"
OUT_DIR = REPO_ROOT / "artifacts" / "eval"
LIBS = ("tokenizers", "transformers", "tiktoken", "sentencepiece", "huggingface_hub")


def load_panel(path: str | Path = PANEL_CONFIG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_.+" else "_" for c in name)


def result_path(name: str, out_dir: Path = OUT_DIR) -> Path:
    return out_dir / f"{safe_name(name)}.json"


def measure_text(adapter, text: EvalText, chunk_chars: int = 2_000_000) -> tuple[dict, list[int]]:
    """Metrics for one text, plus its per-segment token counts (for parity)."""
    segs = list(text.segments)
    seg_ids = adapter.encode_many(segs)
    seg_tokens = [len(ids) for ids in seg_ids]
    seg_words = [len(s.split()) for s in segs]
    decoded = adapter.decode_many(seg_ids)
    roundtrip_ok = sum(d == s for d, s in zip(decoded, segs, strict=True))
    content_ok = sum(same_content(d, s) for d, s in zip(decoded, segs, strict=True))

    tally = TokenTally()
    joined_ok = None
    if text.count_mode == "joined":
        joined_ok = True
        for chunk in iter_chunks(segs, chunk_chars):
            ids = adapter.encode(chunk)
            tally.add(ids, adapter.token_bytes(ids), adapter.unk_id)
            joined_ok = joined_ok and adapter.decode(ids) == chunk
        separators = max(len(segs) - 1, 0)
        chars = sum(len(s) for s in segs) + separators
        nbytes = sum(len(s.encode("utf-8")) for s in segs) + separators
    else:
        for ids in seg_ids:
            tally.add(ids, adapter.token_bytes(ids), adapter.unk_id)
        chars = sum(len(s) for s in segs)
        nbytes = sum(len(s.encode("utf-8")) for s in segs)

    metrics = summarize(
        words=sum(seg_words),
        chars=chars,
        nbytes=nbytes,
        tally=tally,
        segment_tokens=seg_tokens,
        segment_words=seg_words,
        roundtrip_ok=roundtrip_ok,
        content_ok=content_ok,
        segments=len(segs),
        vocab_size=adapter.vocab_size,
    )
    metrics["count_mode"] = text.count_mode
    metrics["roundtrip_joined"] = joined_ok
    return metrics, seg_tokens


def vocab_coverage(adapter) -> dict:
    """:func:`script_coverage` over every id. Ids with no surface form (unused tiktoken ids) are
    counted in ``ids_without_surface``, not guessed."""
    pieces, without = [], 0
    for i in range(adapter.vocab_size):
        try:
            pieces.append(adapter.token_bytes([i])[0])
        except (KeyError, IndexError, ValueError):
            without += 1
    cov = script_coverage(
        pieces, {"devanagari_block": DEVANAGARI_BLOCK, "nepali_core": NEPALI_CORE}
    )
    return cov | {"ids_without_surface": without}


def add_parity(texts: list[EvalText], results: dict, seg_counts: dict) -> None:
    """parity / parity_mean of every aligned text against its set's reference language."""
    for text in texts:
        if not (text.aligned and text.reference):
            continue
        ref_key = f"{text.set_id}/{text.reference}"
        if ref_key in seg_counts:
            lang, ref = seg_counts[text.key], seg_counts[ref_key]
            results[text.key]["parity"] = parity(lang, ref)
            results[text.key]["parity_mean"] = mean_ratio(lang, ref)


def probe_texts(adapter, texts: list[EvalText]) -> dict | None:
    """Robustness probes on the Nepali devtest (plus the raw, non-NFC Hindi file)."""
    from .robustness import run_probes

    by_key = {t.key: t for t in texts}
    npi = by_key.get("flores_devtest/npi_Deva")
    if npi is None:
        return None
    hin = by_key.get("flores_devtest/hin_Deva")
    hin_raw = read_segments(REPO_ROOT / hin.path) if hin else None
    return run_probes(adapter, npi.segments, hin_raw)


def _lib_versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for lib in LIBS:
        try:
            out[lib] = importlib.metadata.version(lib)
        except importlib.metadata.PackageNotFoundError:
            out[lib] = None
    return out


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def fingerprint(spec: dict, set_ids: list[str], registry: dict) -> str:
    files = {}
    for set_id in set_ids:
        for path in set_paths(set_id, registry["sets"][set_id]).values():
            files[str(path)] = _file_digest(path)
    if spec.get("path"):
        local = Path(spec["path"])
        targets = (
            [local]
            if local.is_file()
            else sorted(
                q for q in local.glob("*") if q.suffix in (".json", ".model", ".txt", ".tiktoken")
            )
        )
        for q in targets:
            files[str(q)] = _file_digest(q)
    blob = json.dumps(
        {
            "v": HARNESS_VERSION,
            "spec": spec,
            "sets": set_ids,
            "files": files,
            "sets_cfg": {s: registry["sets"][s] for s in set_ids},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def evaluate_one(
    spec: dict,
    set_ids: list[str],
    out_dir: Path = OUT_DIR,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict:
    """Measure one tokenizer on the selected sets and write ``<out_dir>/<name>.json``."""
    from .adapters import build_adapter

    registry = load_registry(registry_path)
    record: dict = {
        "name": spec["name"],
        "status": "failed",
        "spec": spec,
        "group": spec.get("group"),
        "mirror_of": spec.get("mirror_of"),
        "fingerprint": fingerprint(spec, set_ids, registry),
        "harness": {
            "version": HARNESS_VERSION,
            "libs": _lib_versions(),
            "date": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    }
    stage = "load"
    t0 = time.time()
    try:
        adapter = build_adapter(spec)
        record |= {k: v for k, v in adapter.describe().items() if k != "name"}
        record["load_seconds"] = round(time.time() - t0, 2)
        stage = "measure"
        texts, missing = load_texts(registry, set_ids)
        record["missing_texts"] = missing
        results, seg_counts = {}, {}
        for text in texts:
            results[text.key], seg_counts[text.key] = measure_text(adapter, text)
        add_parity(texts, results, seg_counts)
        record["results"] = results
        stage = "coverage"
        record["coverage"] = vocab_coverage(adapter)
        stage = "robustness"
        record["robustness"] = probe_texts(adapter, texts)
        record["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - a failed baseline is recorded, never fatal
        record["error"] = f"{stage}: {type(exc).__name__}: {exc}"[:600]
        record["traceback"] = traceback.format_exc()[-2000:]
    record["seconds"] = round(time.time() - t0, 2)
    record["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path(spec["name"], out_dir).write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return record


def resolve_spec_paths(spec: dict) -> dict:
    """Make a local ``path`` absolute: relative to the current directory if it exists there,
    otherwise relative to the repo root (so ``artifacts/<run>/tokenizer.json`` works anywhere)."""
    if not spec.get("path"):
        return spec
    p = Path(spec["path"]).expanduser()
    if not p.is_absolute():
        p = p.resolve() if p.exists() else (REPO_ROOT / p)
    if not p.exists():
        raise FileNotFoundError(f"{spec['name']}: no such tokenizer path {p}")
    return spec | {"path": str(p)}


def cached(
    spec: dict,
    set_ids: list[str],
    out_dir: Path = OUT_DIR,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict | None:
    path = result_path(spec["name"], out_dir)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    fp = fingerprint(spec, set_ids, load_registry(registry_path))
    return record if record.get("fingerprint") == fp and record.get("status") == "ok" else None


def run_panel(
    specs: list[dict],
    set_ids: list[str],
    out_dir: Path = OUT_DIR,
    force: bool = False,
    timeout: int = 1800,
    log=print,
) -> list[dict]:
    """Measure each spec in a fresh child process, one at a time. Returns the records."""
    records = []
    for spec in specs:
        spec = resolve_spec_paths(spec)
        hit = None if force else cached(spec, set_ids, out_dir)
        if hit is not None:
            log(f"[cached] {spec['name']}")
            records.append(hit)
            continue
        expected = fingerprint(spec, set_ids, load_registry())
        cmd = [
            sys.executable,
            "-m",
            "yak_tokenizer.eval.panel",
            "--spec",
            json.dumps(spec),
            "--sets",
            ",".join(set_ids),
            "--out",
            str(out_dir),
        ]
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=os.environ | {"HF_HUB_DISABLE_XET": "1"},
            )
            detail = (proc.stderr or proc.stdout or f"exit code {proc.returncode}")[-600:]
        except subprocess.TimeoutExpired:
            detail = f"timed out after {timeout}s"
        path = result_path(spec["name"], out_dir)
        try:
            record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        except json.JSONDecodeError:
            record = None
        if record is None or record.get("fingerprint") != expected:  # the worker died
            record = {
                "name": spec["name"],
                "status": "failed",
                "spec": spec,
                "group": spec.get("group"),
                "error": f"worker: {detail.strip()}"[:600],
            }
            out_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        records.append(record)
        took = time.time() - t0
        npi = (record.get("results") or {}).get("flores_devtest/npi_Deva", {}).get("fertility")
        if record["status"] != "ok":
            log(f"[failed] {spec['name']}: {record.get('error', '')[:200]}")
        elif npi is not None:
            log(
                f"[ok] {spec['name']}: npi fertility {npi:.3f}, {took:.0f}s, "
                f"peak {record.get('peak_rss_mb')} MB"
            )
        else:
            log(f"[ok] {spec['name']}: {took:.0f}s")
    return records


def load_records(out_dir: Path = OUT_DIR) -> list[dict]:
    records = []
    for path in sorted(out_dir.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def _worker(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure one tokenizer (internal worker).")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--sets", required=True)
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args(argv)
    record = evaluate_one(json.loads(args.spec), args.sets.split(","), Path(args.out))
    return 0 if record["status"] == "ok" else 3


if __name__ == "__main__":
    sys.exit(_worker())
