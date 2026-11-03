"""Yak: a Nepali-first byte-level BPE tokenizer for the languages of Nepal."""

from __future__ import annotations

from pathlib import Path

__version__ = "0.0.1"

# One Hub repo holds every release, one folder per version and size:
#   ampixa/yak-tokenizer/v2.0/128k/tokenizer.json, .../v1.0/32k/tokenizer.json, ...
HUB_REPO = "ampixa/yak-tokenizer"
VERSIONS = {
    "v2.0": ("128k", "64k"),
    "v1.0": ("32k", "64k", "64k-phrase", "128k", "128k-phrase"),
}
LATEST = "v2.0"
SIZES = tuple(f"{v}/{s}" for v, sizes in VERSIONS.items() for s in sizes)


def hub_folder(name: str) -> str | None:
    """Resolve a release name to its folder in the Hub repo, or None if it is not one.

    Accepts "v2.0/128k" style names, and a bare size ("128k", "32k", "64k-phrase"), which means
    the newest version that ships that size.
    """
    if name in SIZES:
        return name
    for version, sizes in VERSIONS.items():  # newest first
        if name in sizes:
            return f"{version}/{name}"
    return None


def load(name_or_path: str = "v2.0/128k", repo: str = HUB_REPO):
    """Load a Yak tokenizer as a ``tokenizers.Tokenizer``.

    ``name_or_path`` is a release ("v2.0/128k", "v2.0/64k", "v1.0/32k", "v1.0/64k",
    "v1.0/64k-phrase", "v1.0/128k", "v1.0/128k-phrase"; a bare size picks the newest version
    with that size), fetched from ``repo`` on the Hugging Face Hub, or a local folder or
    ``tokenizer.json`` file, or a standalone Hub repo ID with a top-level ``tokenizer.json``.
    """
    from tokenizers import Tokenizer

    path = Path(name_or_path)
    if path.is_dir():
        path = path / "tokenizer.json"
    if path.is_file():
        return Tokenizer.from_file(str(path))
    from huggingface_hub import hf_hub_download

    folder = hub_folder(name_or_path)
    if folder is not None:
        return Tokenizer.from_file(hf_hub_download(repo, f"{folder}/tokenizer.json"))
    return Tokenizer.from_file(hf_hub_download(name_or_path, "tokenizer.json"))
