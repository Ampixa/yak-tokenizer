"""One interface over every tokenizer family the panel compares.

Every adapter exposes:

* ``name``, ``kind``, ``source``, ``revision``, ``vocab_size`` (including added/special tokens),
  ``unk_id`` (or None when the tokenizer cannot emit an unknown token).
* ``encode(text) -> list[int]``: never adds BOS/EOS or any other special token.
* ``decode(ids) -> str``: keeps every token, and does no "clean-up" of spaces.
* ``token_bytes(ids) -> list[bytes]``: the surface bytes each token stands for. Byte-level
  symbols are mapped back to bytes, the SentencePiece space mark becomes a space, ``<0xNN>``
  byte-fallback pieces become that byte, and WordPiece ``##`` prefixes are removed.
  ``token_strings`` is the same, decoded for display.

Families: tiktoken encodings, raw ``tokenizer.json`` files (Rust ``tokenizers``), transformers
``AutoTokenizer`` (fast or SentencePiece-backed) and raw SentencePiece ``.model`` files.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken"))
os.environ.setdefault("RAYON_NUM_THREADS", "4")  # other jobs share this machine

SPACE_MARK = "▁"  # SentencePiece's visible space
_HEX_PIECE = re.compile(r"<0x([0-9A-Fa-f]{2})>")
_UNK_NAMES = ("<unk>", "[UNK]", "<UNK>", "<|unk|>")

# Files worth fetching from a model repo to build its tokenizer (never weights).
TOKENIZER_FILES = [
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "added_tokens.json",
    "config.json",
    "vocab.json",
    "vocab.txt",
    "merges.txt",
    "*.model",
    "*.tiktoken",
]


def byte_symbol_table() -> dict[str, int]:
    """Map each stand-in character of a byte-level BPE vocabulary back to its byte value.

    Byte-level BPE stores raw bytes as printable characters: printable Latin-1 bytes stand for
    themselves and the other 68 bytes are shifted to U+0100 onwards, in byte order.
    """
    printable = [*range(0x21, 0x7F), *range(0xA1, 0xAD), *range(0xAE, 0x100)]
    table = {chr(b): b for b in printable}
    shifted = (b for b in range(256) if b not in table.values())
    for offset, b in enumerate(shifted):
        table[chr(0x100 + offset)] = b
    return table


_BYTE_SYMBOLS = byte_symbol_table()


def bytelevel_piece_bytes(piece: str) -> bytes:
    try:
        return bytes(_BYTE_SYMBOLS[c] for c in piece)
    except KeyError:  # added tokens are stored as plain text
        return piece.encode("utf-8")


def spacemark_piece_bytes(piece: str) -> bytes:
    hit = _HEX_PIECE.fullmatch(piece)
    if hit:
        return bytes([int(hit.group(1), 16)])
    return piece.replace(SPACE_MARK, " ").encode("utf-8")


def endsuffix_piece_bytes(piece: str, suffix: str = "</w>") -> bytes:
    """Original-style BPE marks the end of a word with a suffix on its last piece."""
    return (piece.removesuffix(suffix)).encode("utf-8")


def wordpiece_piece_bytes(piece: str, prefix: str = "##") -> bytes:
    return (
        piece[len(prefix) :] if piece.startswith(prefix) and piece != prefix else piece
    ).encode()


def _walk_types(node) -> list[str]:
    """All "type" values and short strings in a decoder/pre-tokenizer JSON tree."""
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "type" and isinstance(v, str):
                found.append(v)
            else:
                found += _walk_types(v)
    elif isinstance(node, list):
        for v in node:
            found += _walk_types(v)
    elif isinstance(node, str) and len(node) <= 4:
        found.append(node)
    return found


def _state(component) -> list[str]:
    if component is None:
        return []
    try:
        raw = component.__getstate__()
        return _walk_types(json.loads(raw.decode() if isinstance(raw, bytes) else raw))
    except Exception:  # noqa: BLE001 - introspection is best-effort
        return [type(component).__name__]


def detect_scheme(tok) -> str:
    """How a ``tokenizers.Tokenizer``'s vocabulary strings map to surface text."""
    dec, pre = _state(tok.decoder), _state(tok.pre_tokenizer)
    model = type(tok.model).__name__
    if "ByteLevel" in dec:
        return "bytelevel"
    if "BPEDecoder" in dec:
        return "endsuffix"
    if "WordPiece" in dec:
        return "wordpiece"
    if "Metaspace" in dec or "ByteFallback" in dec or SPACE_MARK in dec:
        return "spacemark"
    if "ByteLevel" in pre:
        return "bytelevel"
    if model == "WordPiece":
        return "wordpiece"
    if model == "Unigram" or "Metaspace" in pre:
        return "spacemark"
    return "plain"


_PIECE_BYTES = {
    "bytelevel": bytelevel_piece_bytes,
    "spacemark": spacemark_piece_bytes,
    "wordpiece": wordpiece_piece_bytes,
    "endsuffix": endsuffix_piece_bytes,
    "plain": lambda p: p.encode("utf-8"),
}


class TokenizerAdapter:
    """Base class. Subclasses set ``_scheme`` and implement ``encode``, ``decode``, ``_piece``."""

    kind = "base"
    _scheme = "plain"

    def __init__(
        self,
        name: str,
        source: str,
        vocab_size: int,
        revision: str | None = None,
        unk_id: int | None = None,
    ):
        self.name = name
        self.source = source
        self.vocab_size = int(vocab_size)
        self.revision = revision
        self.unk_id = unk_id
        self._bytes_cache: dict[int, bytes] = {}

    def encode(self, text: str) -> list[int]:
        raise NotImplementedError

    def encode_many(self, texts: Sequence[str]) -> list[list[int]]:
        return [self.encode(t) for t in texts]

    def decode(self, ids: Sequence[int]) -> str:
        raise NotImplementedError

    def decode_many(self, seqs: Sequence[Sequence[int]]) -> list[str]:
        return [self.decode(s) for s in seqs]

    def _piece(self, token_id: int) -> str:
        raise NotImplementedError

    def _piece_bytes(self, token_id: int) -> bytes:
        piece = self._piece(token_id)
        return _PIECE_BYTES[self._scheme](piece) if piece is not None else b""

    def token_bytes(self, ids: Sequence[int]) -> list[bytes]:
        cache = self._bytes_cache
        out = []
        for i in ids:
            b = cache.get(i)
            if b is None:
                b = cache[i] = self._piece_bytes(i)
            out.append(b)
        return out

    def token_strings(self, ids: Sequence[int]) -> list[str]:
        return [b.decode("utf-8", errors="backslashreplace") for b in self.token_bytes(ids)]

    def describe(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "revision": self.revision,
            "vocab_size": self.vocab_size,
            "unk_id": self.unk_id,
            "piece_scheme": self._scheme,
        }


class TiktokenAdapter(TokenizerAdapter):
    kind = "tiktoken"
    _scheme = "bytes"

    def __init__(self, name: str, encoding: str):
        import importlib.metadata

        import tiktoken

        self._enc = tiktoken.get_encoding(encoding)
        version = importlib.metadata.version("tiktoken")
        super().__init__(name, f"tiktoken:{encoding}", self._enc.n_vocab, f"tiktoken=={version}")

    def encode(self, text: str) -> list[int]:
        return self._enc.encode_ordinary(text)

    def encode_many(self, texts: Sequence[str]) -> list[list[int]]:
        return self._enc.encode_ordinary_batch(list(texts), num_threads=4)

    def decode(self, ids: Sequence[int]) -> str:
        return self._enc.decode_bytes(list(ids)).decode("utf-8", errors="replace")

    def _piece_bytes(self, token_id: int) -> bytes:
        return self._enc.decode_single_token_bytes(token_id)


def _unk_from_vocab(token_to_id) -> int | None:
    for name in _UNK_NAMES:
        tid = token_to_id(name)
        if tid is not None:
            return tid
    return None


def _default_decoders() -> dict:
    from tokenizers import decoders

    return {
        "wordpiece": lambda: decoders.WordPiece(prefix="##"),
        "spacemark": decoders.Metaspace,
        "bytelevel": decoders.ByteLevel,
    }


_DEFAULT_DECODERS = _default_decoders()


class HFJsonAdapter(TokenizerAdapter):
    """A raw ``tokenizer.json`` loaded with the Rust ``tokenizers`` library."""

    kind = "hf_json"

    def __init__(
        self, name: str, path: str | Path, revision: str | None = None, source: str | None = None
    ):
        from tokenizers import Tokenizer

        self._tok = Tokenizer.from_file(str(path))
        self._scheme = detect_scheme(self._tok)
        self.decoder_added = None
        if self._tok.decoder is None and self._scheme in _DEFAULT_DECODERS:
            # A tokenizer.json without a decoder (IndicBERTv2) would decode WordPiece as
            # "नेपाल ##मा". Attach the standard decoder of its family; encoding is unchanged.
            self._tok.decoder = _DEFAULT_DECODERS[self._scheme]()
            self.decoder_added = self._scheme
        unk = getattr(self._tok.model, "unk_token", None)
        unk_id = self._tok.token_to_id(unk) if unk else _unk_from_vocab(self._tok.token_to_id)
        super().__init__(
            name,
            source or str(path),
            self._tok.get_vocab_size(with_added_tokens=True),
            revision,
            unk_id,
        )
        self._fast_batch = hasattr(self._tok, "encode_batch_fast")

    def describe(self) -> dict:
        return super().describe() | {"decoder_added": self.decoder_added}

    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text, add_special_tokens=False).ids

    def encode_many(self, texts: Sequence[str]) -> list[list[int]]:
        batch = self._tok.encode_batch_fast if self._fast_batch else self._tok.encode_batch
        return [e.ids for e in batch(list(texts), add_special_tokens=False)]

    def decode(self, ids: Sequence[int]) -> str:
        return self._tok.decode(list(ids), skip_special_tokens=False)

    def decode_many(self, seqs: Sequence[Sequence[int]]) -> list[str]:
        return self._tok.decode_batch([list(s) for s in seqs], skip_special_tokens=False)

    def _piece(self, token_id: int) -> str | None:
        return self._tok.id_to_token(token_id)


class TransformersAdapter(TokenizerAdapter):
    """``transformers.AutoTokenizer`` (used for repos without a ``tokenizer.json``)."""

    kind = "transformers"

    def __init__(
        self,
        name: str,
        path: str | Path,
        revision: str | None = None,
        source: str | None = None,
        **kwargs,
    ):
        import transformers
        from transformers import AutoTokenizer

        transformers.logging.set_verbosity_error()  # silences max-length warnings on long texts
        self._tok = AutoTokenizer.from_pretrained(str(path), trust_remote_code=False, **kwargs)
        try:
            backend = self._tok.backend_tokenizer
        except (AttributeError, ValueError, NotImplementedError):
            backend = None
        if backend is not None:
            self._scheme = detect_scheme(backend)
        else:
            sample = self._tok.convert_ids_to_tokens(list(range(min(len(self._tok), 2000))))
            if sum(1 for p in sample if p and p.startswith("##")) > 50:
                self._scheme = "wordpiece"
            elif sum(1 for p in sample if p and SPACE_MARK in p) > 50:
                self._scheme = "spacemark"
            else:
                self._scheme = "plain"
        super().__init__(
            name,
            source or str(path),
            len(self._tok),
            revision,
            getattr(self._tok, "unk_token_id", None),
        )

    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text, add_special_tokens=False)

    def decode(self, ids: Sequence[int]) -> str:
        return self._tok.decode(
            list(ids), skip_special_tokens=False, clean_up_tokenization_spaces=False
        )

    def _piece(self, token_id: int) -> str | None:
        return self._tok.convert_ids_to_tokens(token_id)


class SentencePieceAdapter(TokenizerAdapter):
    """A raw SentencePiece ``.model`` file. ``encode`` never adds BOS/EOS."""

    kind = "sentencepiece"
    _scheme = "spacemark"

    def __init__(
        self, name: str, path: str | Path, revision: str | None = None, source: str | None = None
    ):
        import sentencepiece as spm

        self._sp = spm.SentencePieceProcessor(model_file=str(path))
        unk = self._sp.unk_id()
        super().__init__(
            name,
            source or str(path),
            self._sp.get_piece_size(),
            revision,
            unk if unk >= 0 else None,
        )

    def encode(self, text: str) -> list[int]:
        return self._sp.encode(text, out_type=int)

    def encode_many(self, texts: Sequence[str]) -> list[list[int]]:
        return self._sp.encode(list(texts), out_type=int, num_threads=4)

    def decode(self, ids: Sequence[int]) -> str:
        return self._sp.decode(list(ids))

    def _piece_bytes(self, token_id: int) -> bytes:
        piece = self._sp.id_to_piece(token_id)
        if self._sp.is_byte(token_id):
            return spacemark_piece_bytes(piece)
        return piece.replace(SPACE_MARK, " ").encode("utf-8")


# ---------------------------------------------------------------------------------------------
# Building adapters from panel specs


def hub_snapshot(repo: str, patterns: list[str], revision: str | None = None) -> tuple[Path, str]:
    """Download only tokenizer files of ``repo``. Returns ``(local_dir, resolved_commit)``.

    Retries once on a network error, then falls back to the local HF cache, so a re-run works
    offline for every repo that was fetched before.
    """
    import time

    from huggingface_hub import snapshot_download

    error: Exception | None = None
    for attempt in range(2):
        try:
            local = Path(snapshot_download(repo, revision=revision, allow_patterns=patterns))
            return local, local.name
        except Exception as exc:  # noqa: BLE001 - network errors come in many types
            error = exc
            time.sleep(5 * (attempt + 1))
    try:
        local = Path(
            snapshot_download(
                repo, revision=revision, allow_patterns=patterns, local_files_only=True
            )
        )
        return local, local.name
    except Exception:  # noqa: BLE001
        raise error from None


def _pick_model_file(folder: Path, wanted: str | None) -> Path:
    if wanted:
        return folder / wanted
    models = sorted(folder.glob("*.model"))
    if not models:
        raise FileNotFoundError(f"no SentencePiece .model file in {folder}")
    return models[0]


def build_adapter(spec: dict) -> TokenizerAdapter:
    """Create an adapter from a panel entry (see ``configs/eval_panel.yaml``)."""
    name, kind = spec["name"], spec.get("kind", "auto")
    if kind == "tiktoken":
        return TiktokenAdapter(name, spec["encoding"])

    repo, path = spec.get("repo"), spec.get("path")
    revision, source = None, path
    if repo:
        if kind == "auto":
            kind = _auto_kind_for_repo(repo, spec.get("revision"))
        folder, revision = hub_snapshot(repo, _patterns_for(kind, spec), spec.get("revision"))
        source = repo
    else:
        folder = Path(path)
        if kind == "auto":
            kind = _auto_kind_for_path(folder)
    kwargs = spec.get("kwargs") or {}

    if kind == "hf_json":
        file = folder / spec.get("file", "tokenizer.json") if folder.is_dir() else folder
        return HFJsonAdapter(name, file, revision, source)
    if kind == "sentencepiece":
        file = _pick_model_file(folder, spec.get("file")) if folder.is_dir() else folder
        return SentencePieceAdapter(name, file, revision, source)
    if kind == "transformers":
        return TransformersAdapter(name, folder, revision, source, **kwargs)
    raise ValueError(f"{name}: unknown tokenizer kind {kind!r}")


def _patterns_for(kind: str, spec: dict) -> list[str]:
    if spec.get("file"):
        return [spec["file"]]
    if kind == "hf_json":
        return ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]
    if kind == "sentencepiece":
        return ["*.model"]
    return list(TOKENIZER_FILES)


def _auto_kind_for_path(path: Path) -> str:
    if path.is_file():
        if path.suffix == ".json":
            return "hf_json"
        if path.suffix == ".model":
            return "sentencepiece"
        raise ValueError(f"cannot tell the tokenizer kind of {path}")
    if (path / "tokenizer.json").exists():
        return "hf_json"
    return "transformers"


def _auto_kind_for_repo(repo: str, revision: str | None) -> str:
    from huggingface_hub import HfApi

    files = set(HfApi().list_repo_files(repo, revision=revision))
    if "tokenizer.json" in files:
        return "hf_json"
    if any(f.endswith((".txt", "tokenizer_config.json")) for f in files):
        return "transformers"
    if any(f.endswith(".model") for f in files):
        return "sentencepiece"
    return "transformers"


def parse_extra(arg: str) -> dict:
    """Parse ``--add`` values: ``name=path``, ``name=hf:repo``, ``name=tiktoken:encoding``,
    ``name=sp:path/to.model``. Paths may be a ``tokenizer.json``, a ``.model`` or a directory."""
    if "=" not in arg:
        raise ValueError(f"--add expects name=source, got {arg!r}")
    name, src = arg.split("=", 1)
    spec: dict = {"name": name.strip(), "group": "added"}
    if src.startswith("tiktoken:"):
        spec |= {"kind": "tiktoken", "encoding": src.split(":", 1)[1]}
    elif src.startswith("hf:"):
        spec |= {"kind": "auto", "repo": src.split(":", 1)[1]}
    elif src.startswith("sp:"):
        spec |= {"kind": "sentencepiece", "path": src.split(":", 1)[1]}
    else:
        spec |= {"kind": "auto", "path": src}
    return spec
