# Yak Tokenizer

**Open, lossless, Nepali-first tokenizers for the languages of Nepal**, and the benchmark that measures them.

The tokenizers are on Hugging Face: **[ampixa/yak-tokenizer](https://huggingface.co/ampixa/yak-tokenizer)**.
This repository holds the guide, the full results and the benchmark harness, so you can check every
number below and measure your own tokenizer the same way.

> **Coming soon:** Ampixa Labs is developing a new large language model. Release details will be shared on [ampixa.com](https://ampixa.com) and [Hugging Face](https://huggingface.co/ampixa).

**We measured 19 languages of Nepal:** 14 from held-out translation data (Athpariya, Dhimal, Gurung, Kulung,
Kayort, Lohorung, Limbu, Magar, Newar, Sampang, Sunuwar, Tamang, Tharu Dangaura, Tharu Rana) and 5 on FLORES+.
Yak v2.0 is the lowest-fertility lossless tokenizer on **18 of 19**.

- **2.7× fewer tokens than Llama-3 on Nepali**, and 40% fewer than GPT-4o (1.38 vs 3.76 and 2.32 tokens per word).
- **#1 lossless tokenizer on Nepali** of 42 measured: `v1.0/128k-phrase`, 1.267 tokens per word.
- **Small vocab, big result:** `v1.0/32k` (1.586) beats Arkios at twice the vocab (1.688) and every frontier LLM tokenizer, and comes within 1% of IndicBERT v2 (1.578) at 1/8 of its vocab.
- **Good on English too:** `v1.0/128k-phrase` (1.232) needs fewer English tokens than Llama-3 (1.241); the other builds stay within a few percent of it.
- **Languages of Nepal:** v2.0 uses 38% fewer tokens than the best other tokenizer on the 14-language average.
- **Every Nepali character is a whole token:** every size has a token for all 73 characters of everyday Nepali and all 128 assigned Devanagari code points.
- **Lossless by design:** 100% round-trip, zero unknown tokens, no normalizer, so your text is never altered.

```
नेपालको राजधानी काठमाडौं हो ।        "Kathmandu is the capital of Nepal."
Llama-3   17 tokens   न|ेप|ालक|ो| र|ाज|ध|ान|ी| क|ाठ|म|ाड|ौं| ह|ो| ।
Yak v2.0   5 tokens   नेपालको| राजधानी| काठमाडौं| हो| ।
```

## Pick one

| Folder | Vocab | Nepali | English | Hindi | Languages of Nepal |
|---|---:|---:|---:|---:|---:|
| [`v2.0/128k`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v2.0/128k) | 131,072 | 1.382 | 1.313 | 1.298 | 1.629 |
| [`v2.0/64k`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v2.0/64k) | 65,536 | 1.470 | 1.420 | 1.385 | 1.843 |
| [`v1.0/128k`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v1.0/128k) | 131,072 | 1.370 | 1.291 | 1.290 | 2.505 |
| [`v1.0/64k`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v1.0/64k) | 65,536 | 1.457 | 1.388 | 1.376 | 2.743 |
| [`v1.0/32k`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v1.0/32k) | 32,768 | 1.586 | 1.538 | 1.505 | 3.005 |
| [`v1.0/128k-phrase`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v1.0/128k-phrase) | 131,072 | 1.267 | 1.232 | 1.247 | 2.532 |
| [`v1.0/64k-phrase`](https://huggingface.co/ampixa/yak-tokenizer/tree/main/v1.0/64k-phrase) | 65,536 | 1.374 | 1.350 | 1.367 | 2.751 |

Tokens per word (fertility) on FLORES+ devtest, the whole file encoded at once; lower is better.
*Languages of Nepal* is the mean over the 14 held-out languages listed above.

- **Building a model for Nepal (Nepali plus other languages of Nepal):** `v2.0/128k`, or `v2.0/64k` for a small model.
- **Nepali and English only:** `v1.0/128k` or `v1.0/64k`.
- **Smallest footprint:** `v1.0/32k`.
- **Best compression, experimental:** `v1.0/128k-phrase` / `v1.0/64k-phrase`. Tokens may span up to 4 words; no llama.cpp support yet.

## Use

```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("ampixa/yak-tokenizer", subfolder="v2.0/128k")
ids = tok("नेपालको राजधानी काठमाडौं हो ।")["input_ids"]          # starts with <|bos|>
```

```python
# tokenizers only (Tokenizer.from_pretrained has no subfolder argument, so download the file)
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
tok = Tokenizer.from_file(hf_hub_download("ampixa/yak-tokenizer", "v2.0/128k/tokenizer.json"))
```

```python
# or this package: pip install git+https://github.com/Ampixa/yak-tokenizer
import yak_tokenizer
tok = yak_tokenizer.load("v2.0/128k")   # "v1.0/32k", ...; a bare size such as "32k" picks the newest version with it
```

Each folder on Hugging Face also has `tiktoken/` (`yak.tiktoken` ranks plus `tiktoken.json` with the
split pattern and special tokens). Special tokens: `<|pad|>`, `<|bos|>`, `<|eos|>`, `<|start_turn|>`, `<|end_turn|>`, `<|think|>`, `<|/think|>`, `<|tool_call|>`, `<|/tool_call|>`, `<|tool_result|>`, `<|/tool_result|>`, `<|fill_prefix|>`, `<|fill_suffix|>`, `<|fill_middle|>`, `<|mask|>`, `<|sep|>`. Chat format:
`<|start_turn|>role\n...<|end_turn|>`. 1,024 IDs at the end of every vocabulary are reserved for later
additions, so existing IDs never move.

## Results

Full leaderboard, every metric and its definition: **[docs/RESULTS.md](docs/RESULTS.md)**.
It lists 42 tokenizers: the 35 public ones in the panel and the seven released Yak builds.

### Nepali, English and Hindi (FLORES+ devtest, tokens per word)

| Tokenizer | Nepali | English | Hindi |
|---|---:|---:|---:|
| **Yak v2.0/128k** | 1.382 | 1.313 | 1.298 |
| **Yak v2.0/64k** | 1.470 | 1.420 | 1.385 |
| **Yak v1.0/128k** | 1.370 | 1.291 | 1.290 |
| **Yak v1.0/64k** | 1.457 | 1.388 | 1.376 |
| **Yak v1.0/32k** | 1.586 | 1.538 | 1.505 |
| **Yak v1.0/128k-phrase** | 1.267 | 1.232 | 1.247 |
| IndicBERT v2 (250k) | 1.578 | 1.236 | 1.235 |
| Arkios (65k) | 1.688 | 1.297 | 2.012 |
| sidskarki 64k, Nepali-only | 1.445 | 2.409 | 1.656 |
| GPT-4o / o200k (200k) | 2.321 | 1.227 | 1.648 |
| Gemma 3 (262k) | 2.270 | 1.284 | 1.424 |
| Llama-3 (128k) | 3.764 | 1.241 | 2.676 |

### Languages of Nepal (held-out text, 14 languages)

| Tokenizer | Mean fertility, 14 languages | Worst parity vs Nepali |
|---|---:|---:|
| **Yak v2.0 128k** | 1.629 | 1.34x (aph) |
| **Yak v2.0 64k** | 1.843 | 1.48x (aph) |
| Yak v1.0 128k | 2.505 | 2.81x (lif) |
| IndicBERT v2 | 2.639 | 2.79x (lif) |
| sidskarki 64k | 3.131 | 3.59x (lif) |
| GPT-4o (o200k) | 3.592 | 2.59x (lif) |
| Llama-3 | 4.175 | 2.13x (lif) |

## Rerun the benchmark

The harness measures 35 public tokenizers plus every Yak build, on the same text, the same way.
Before it reports anything about Yak, it reproduces 14 published fertility numbers of other
tokenizers within ±0.03 (the validity gate in [docs/RESULTS.md](docs/RESULTS.md)). Tokenizers that do
not round-trip a text exactly are marked † in the results.

```bash
git clone https://github.com/Ampixa/yak-tokenizer && cd yak-tokenizer
uv sync --extra eval
uv run python scripts/eval_panel.py fetch      # FLORES+ is gated: accept its terms on Hugging Face first
uv run python scripts/eval_panel.py run        # the full panel, Yak included; writes docs/RESULTS.md
```

Code and math are optional: add `--code-math` to both `fetch` and `run` to also measure HumanEval,
MBPP, GSM8K and MATH.

Add your own tokenizer to the comparison:

```bash
uv run python scripts/eval_panel.py run --add mine=path/to/tokenizer.json
# also: --add mine=path/to/folder, --add mine=sp:path/to/model.model, --add mine=hf:org/repo
uv run python scripts/eval_panel.py run --only none --add mine=path/to/tokenizer.json   # just yours
```

What it measures: fertility on FLORES+ (Nepali, English, Hindi, Maithili, Bhojpuri, Sanskrit, Awadhi,
Magahi, Santali, Tibetan), parity against English, everyday Nepali (Aya), Romanized and Devanagari
word lists, robustness probes (joiners, vowel-length typos, pipe for danda, non-NFC Hindi), round-trip,
unknown tokens, split vowel signs, byte pieces, script coverage and Rényi efficiency. Each tokenizer
runs in its own process and results are cached in `artifacts/eval/`.

Two things cannot be rerun from this repository:

- **The 14 languages-of-Nepal held-out sets.** Their text cannot be redistributed, so a public run skips
  them; docs/RESULTS.md reports the numbers we measured.
- **Training.** Only the tokenizers are released, not the training data.

## Repository layout

```
configs/eval_panel.yaml     the tokenizers in the panel, and the validity-gate targets
configs/eval_sets.yaml      the evaluation texts
data/eval/                  the evaluation texts we may redistribute (FLORES+, code and math are fetched, never committed)
docs/RESULTS.md             the full leaderboard
scripts/eval_panel.py       fetch | run | report
src/yak_tokenizer/          load() helper and the eval harness (yak_tokenizer.eval)
tests/                      uv run pytest
```

## What is released

The tokenizers, on Hugging Face: `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json` and
a tiktoken export for each version and size. **The training data is not released.** v1.0 was trained on
public web, news, Wikipedia, government and education text in Nepali plus English, Hindi, Romanized
Nepali, code and math. v2.0 adds monolingual text for the other languages of Nepal.

## v1.0 and v2.0

| | v1.0 | v2.0 |
|---|---|---|
| Focus | Nepali and English | most languages of Nepal |
| Other languages of Nepal in the mix | 3%, one shared bucket | about 15%, 22 languages with their own share |
| Tokens starting on a split vowel sign | 6.7–12.8% | 0.1–0.2% |
| Native scripts reserved | Devanagari, Limbu, Tibetan, Newa, Ol Chiki | + Kirat Rai, Sunuwar, Gurung Khema, Tirhuta, Lepcha |
| Sizes | 32k, 64k, 128k, 64k-phrase, 128k-phrase | 64k, 128k |

## Limitations

- No downstream language-model test yet: these are tokenizer-level measurements.
- On Sanskrit, IndicBERT v2 is slightly ahead of v2.0 (2.07 vs 2.13 tokens per word).
- Code is 5% and math 2.5% of the v2.0 training mix, and every digit is its own token. On code and math Yak needs about 3–19% more tokens than Llama-3.
- llama.cpp / GGUF needs a Yak pre-tokenizer patch that is not upstream yet; it is tested for the v1.0 word-level sizes only.

## License

- **Tokenizer files** (Hugging Face): [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Free to use, share and adapt for non-commercial purposes with attribution. For commercial use, contact Ampixa Labs (https://ampixa.com).
- **Code in this repository**: MIT, see [LICENSE](LICENSE).
- **Evaluation texts** in `data/eval/` keep their own licenses; see [data/eval/SOURCES.md](data/eval/SOURCES.md).

Built by Ampixa Labs (https://ampixa.com).
