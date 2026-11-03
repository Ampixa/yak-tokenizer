"""Evaluation text sets: the registry in ``configs/eval_sets.yaml`` and loaders for its files.

Two file formats live under ``data/eval/``:

* ``.txt``: one segment per line, separated by ``\\n`` (FLORES sentences, word lists).
  Lines are split on ``\\n`` only, never with ``str.splitlines()``, which would also break on
  U+2028, U+0085 and friends and silently misalign parallel files.
* ``.jsonl``: one ``{"text": str, "id": str}`` object per line (documents that contain newlines,
  such as code or math solutions).

A registry entry with ``langs`` expands into one text per language (``<set>/<lang>``). Sets marked
``aligned: true`` are line-parallel across languages, which is what parity needs.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = REPO_ROOT / "configs" / "eval_sets.yaml"
COUNT_MODES = ("joined", "segments")


@dataclass(frozen=True)
class EvalText:
    """One measurable text: a list of segments plus how to count its tokens."""

    key: str  # "<set>" or "<set>/<lang>"
    set_id: str
    lang: str | None
    domain: str
    path: str
    segments: tuple[str, ...]
    count_mode: str  # "joined": encode the "\n"-joined text; "segments": encode each segment
    aligned: bool = False
    reference: str | None = None  # parity reference language of an aligned set


def read_segments(path: str | Path) -> list[str]:
    """Return the segments stored in a ``.txt`` (one per line) or ``.jsonl`` file."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line)["text"] for line in raw.split("\n") if line.strip()]
    raw = raw.removesuffix("\n")
    return raw.split("\n") if raw else []


def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict:
    with open(path, encoding="utf-8") as fh:
        reg = yaml.safe_load(fh)
    for set_id, spec in reg["sets"].items():
        mode = spec.get("count", "segments")
        if mode not in COUNT_MODES:
            raise ValueError(f"{set_id}: count must be one of {COUNT_MODES}, not {mode!r}")
    return reg


def set_paths(set_id: str, spec: dict, root: Path = REPO_ROOT) -> dict[str | None, Path]:
    """Map language (or None) to the file path of each text in a registry entry."""
    if "langs" in spec:
        return {lang: root / spec["path"].format(lang=lang) for lang in spec["langs"]}
    return {None: root / spec["path"]}


def load_texts(
    registry: dict,
    set_ids: list[str] | None = None,
    root: Path = REPO_ROOT,
    skip_missing: bool = True,
) -> tuple[list[EvalText], list[str]]:
    """Load every text of the selected sets. Returns ``(texts, missing_paths)``.

    Text is NFC-normalised when the entry says ``nfc: true`` (the default), so every tokenizer is
    fed identical code points; the files on disk stay byte-identical to their source.
    """
    texts: list[EvalText] = []
    missing: list[str] = []
    wanted = set_ids or [s for s, spec in registry["sets"].items() if spec.get("panel", True)]
    for set_id in wanted:
        spec = registry["sets"][set_id]
        for lang, path in set_paths(set_id, spec, root).items():
            if not path.exists():
                if not skip_missing:
                    raise FileNotFoundError(path)
                missing.append(str(path.relative_to(root)))
                continue
            segs = read_segments(path)
            if spec.get("nfc", True):
                segs = [unicodedata.normalize("NFC", s) for s in segs]
            texts.append(
                EvalText(
                    key=f"{set_id}/{lang}" if lang else set_id,
                    set_id=set_id,
                    lang=lang,
                    domain=spec.get("domain", set_id),
                    path=str(path.relative_to(root)),
                    segments=tuple(segs),
                    count_mode=spec.get("count", "segments"),
                    aligned=bool(spec.get("aligned", False)),
                    reference=spec.get("reference"),
                )
            )
    return texts, missing
