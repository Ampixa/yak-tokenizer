# Yak tokenizer results

> Generated on 2026-11-03 by `uv run python scripts/eval_panel.py run` from `artifacts/eval/*.json`.
> Do not edit by hand: the template is `src/yak_tokenizer/eval/report.py`.

## Definitions

Every tokenizer is fed the same NFC text and never adds special tokens (no BOS/EOS).
Exact formulas are in `src/yak_tokenizer/eval/metrics.py`.

- **Fertility** = tokens / whitespace words, where words = `len(text.split())` (Python `str.split()`). On FLORES the token count comes from encoding the **whole file as one string**, sentences joined by `\n` (no trailing newline). This is the definition that reproduces the published numbers (see the gate below). Sets of words or documents are encoded one segment at a time and summed.
- **Parity** = total tokens of a language / total tokens of English on the 1,012 line-aligned FLORES+ devtest sentences, each sentence encoded on its own.
- **Bytes/tok** and **chars/tok** = UTF-8 bytes or code points of the counted text / tokens (higher is better).
- **Orphan marks** = share of tokens whose first character is a combining mark (Unicode Mn/Mc/Me: matras, virama, nukta, anusvara, chandrabindu, visarga), i.e. tokens cut off their consonant. **Mid-char** = share of tokens that start inside a UTF-8 character (byte fragments).
- **Round-trip** = share of all eval segments (every panel text) where `decode(encode(x)) == x`, shown as *exact · content*. *Content* compares the strings with all whitespace removed, so decoders that only add a prefix space or put spaces around punctuation (WordPiece) pass, while lost characters (unknown tokens, normalisation) fail. **unk** = share of tokens that are the unknown token.
- **Vocab used** = distinct token ids in the text / vocab size. **Rényi eff.** = Rényi entropy (α = 2.5) of the token distribution / log(vocab size).
- **Nepali chars without a token** = characters of everyday Nepali (independent vowels, consonants, vowel signs, ँ ं ः ़ ् ऽ, । ॥, digits, ॐ; `NEPALI_CORE` in `metrics.py`) that no vocabulary token contains whole. Such a character is still encoded, as unknown or as byte-fallback pieces, but never inside a learned word: with byte fallback, ऊ alone costs 3 tokens and still round-trips, so unk and round-trip do not show it. **Devanagari block without a token** is the same check over every assigned code point U+0900-U+097F (Vedic and Sindhi letters included). **Byte pieces** = share of tokens that are not whole UTF-8 characters.
- **Vocab** counts every id, including added and special tokens.

## Validity gate

Text: `flores_devtest/npi_Deva` (FLORES+ devtest, 1012 sentences, 18701 words, 127914 chars, 340483 bytes with the joining newlines). Target: within ±0.03 of Arkios paper (arXiv 2608.26449), main table; FLORES-200 devtest.

**Result: 5/5 reproduced.**

| Tokenizer | Published | **Ours: whole file** | Δ | Pass | Per-line sum | Per-line mean | Per-line sum + 1 BOS/line |
|---|---:|---:|---:|:---:|---:|---:|---:|
| gpt2 | 10.97 | **10.973** | +0.003 | ✓ | 10.919 (-0.051 ✗) | 11.005 (+0.035 ✗) | 10.973 (+0.003) |
| cl100k | 6.98 | **6.979** | -0.001 | ✓ | 6.926 (-0.054 ✗) | 6.979 (-0.001) | 6.980 (-0.000) |
| o200k | 2.32 | **2.321** | +0.001 | ✓ | 2.320 (-0.000) | 2.345 (+0.025) | 2.374 (+0.054 ✗) |
| llama3 | 3.76 | **3.764** | +0.004 | ✓ | 3.753 (-0.007) | 3.781 (+0.021) | 3.807 (+0.047 ✗) |
| arkios | 1.69 | **1.688** | -0.002 | ✓ | 1.634 (-0.056 ✗) | 1.655 (-0.035 ✗) | 1.688 (-0.002) |

**Definition that matches:** tokens of the whole devtest file encoded in one call (sentences joined by `\n`, so line breaks are tokenized too), divided by `str.split()` words, no special tokens. It is the corpus ratio of the file, not a mean over sentences. Alternatives miss:

- Encoding each sentence separately and summing drops the ~1,011 newline tokens. It reproduces only 2/5 numbers (GPT-2 and cl100k fall about 0.05 low). This is the variant behind the quick check gpt2 10.919 / cl100k 6.926 / o200k 2.320.
- A mean of per-sentence ratios over-weights short sentences and misses GPT-2 by +0.035.
- Adding one BOS per sentence (the HF default for Llama-3) gives the whole-file count only for tokenizers that spend exactly one token per newline (GPT-2, cl100k, Arkios). It misses o200k and Llama-3, which merge `।` with the newline, by about +0.05.
- FLORES+ vs FLORES-200 does not matter here. FLORES+ `npi_Deva` devtest has exactly the word, char and byte counts the Arkios harness logged for FLORES-200 (18,701 / 127,914 / 340,483), and NFC is a no-op on it. NFC does change `hin_Deva`, which is one reason we always NFC first.

Cross-checks against other numbers in the same paper (not part of the gate):

| Tokenizer | Published | **Ours: whole file** | Δ | Pass | Per-line sum | Per-line mean | Per-line sum + 1 BOS/line |
|---|---:|---:|---:|:---:|---:|---:|---:|
| qwen2.5 | 6.57 | **6.575** | +0.005 | ✓ | 6.521 (-0.049 ✗) | 6.561 (-0.009) | 6.576 (+0.006) |
| deepseek-v3 | 4.29 | **4.291** | +0.001 | ✓ | 4.291 (+0.001) | 4.326 (+0.036 ✗) | 4.345 (+0.055 ✗) |
| gemma2 | 3.13 | **3.133** | +0.003 | ✓ | 3.079 (-0.051 ✗) | 3.102 (-0.028) | 3.133 (+0.003) |
| mistral-nemo | 3.17 | **3.169** | -0.001 | ✓ | 3.168 (-0.002) | 3.196 (+0.026) | 3.222 (+0.052 ✗) |
| sarvam-1 | 2.66 | **2.659** | -0.001 | ✓ | 2.589 (-0.071 ✗) | 2.608 (-0.052 ✗) | 2.643 (-0.017) |
| mt5 | 2.64 | **2.638** | -0.002 | ✓ | 2.638 (-0.002) | 2.655 (+0.015) | 2.693 (+0.053 ✗) |
| nllb-200 | 1.92 | **1.920** | +0.000 | ✓ | 1.920 (+0.000) | 1.940 (+0.020) | 1.974 (+0.054 ✗) |
| indicbert-v2 | 1.58 | **1.578** | -0.002 | ✓ | 1.578 (-0.002) | 1.595 (+0.015) | 1.632 (+0.052 ✗) |
| bloom | 1.72 | **1.724** | +0.004 | ✓ | 1.723 (+0.003) | 1.744 (+0.024) | 1.777 (+0.057 ✗) |

## Leaderboard: Nepali FLORES+ devtest

Sorted by Nepali fertility (lower is better). Fertility columns are FLORES+ devtest, whole-file definition. *npi per line* encodes each sentence on its own and sums, so newlines are not counted; tokenizers that spend a token per newline gain ~0.05 there. Parity is vs English. Round-trip covers every panel text.

| # | Tokenizer | Vocab | npi | npi per line | eng | hin | mai | npi parity | npi bytes/tok | orphan marks (npi) | unk (npi) | round-trip exact · content | Nepali chars without a token |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **yak-128k-v1-phrase** | 131,072 | **1.267** | 1.267 | 1.232 | 1.247 | 1.362 | 0.88 | 14.37 | 7.8% | 0.00% | 100.0% · 100.0% | 0 |
| 2 | sai-nep-128k | 128,000 | **1.321** † | 1.321 | 3.716 † | 1.527 † | 1.688 † | 0.30 | 13.78 | 1.3% | 2.78% | 32.6% · 37.6% | 4: ◌़ ऽ ॥ ॐ |
| 3 | **yak-128k-v1** | 131,072 | **1.370** | 1.370 | 1.291 | 1.290 | 1.356 | 0.91 | 13.29 | 6.7% | 0.00% | 100.0% · 100.0% | 0 |
| 4 | **yak-64k-v1-phrase** | 65,536 | **1.374** | 1.374 | 1.350 | 1.367 | 1.467 | 0.87 | 13.25 | 10.4% | 0.00% | 100.0% · 100.0% | 0 |
| 5 | **yak-128k-v2.0** | 131,072 | **1.382** | 1.382 | 1.313 | 1.298 | 1.334 | 0.90 | 13.17 | 0.1% | 0.00% | 100.0% · 100.0% | 0 |
| 6 | nepali-bpe | 50,006 | **1.433** † | 1.433 | 5.018 † | 1.766 † | 1.917 † | 0.24 | 12.71 | 0.5% | 6.88% | 12.9% · 44.3% | 0 |
| 7 | sidskarki-64k | 64,000 | **1.445** | 1.370 | 2.409 | 1.656 | 1.797 | 0.50 | 12.60 | 1.7% | 0.00% | 99.1% · 100.0% | 0 |
| 8 | **yak-64k-v1** | 65,536 | **1.457** | 1.457 | 1.388 | 1.376 | 1.449 | 0.90 | 12.50 | 9.2% | 0.00% | 100.0% · 100.0% | 0 |
| 9 | himalaya-128k | 128,000 | **1.462** † | 1.385 | 1.298 † | 1.518 † | 1.747 † | 0.95 | 12.46 | 1.9% | 0.00% | 99.0% · 99.9% | 8: ऊ ऋ ऐ ◌ः ◌़ ऽ ॥ ॐ |
| 10 | **yak-64k-v2.0** | 65,536 | **1.470** | 1.470 | 1.420 | 1.385 | 1.419 | 0.88 | 12.38 | 0.2% | 0.00% | 100.0% · 100.0% | 0 |
| 11 | nepberta | 30,523 | **1.481** † | 1.481 | 4.074 † | 1.845 † | 1.902 † | 0.31 | 12.29 | 4.4% | 0.26% | 23.3% · 58.0% | 0 |
| 12 | muril | 197,258 | **1.490** † | 1.490 | 1.259 † | 1.245 † | 1.679 † | 1.01 | 12.22 | 5.4% | 0.01% | 28.6% · 67.0% | 0 |
| 13 | himalaya-100k | 100,000 | **1.494** † | 1.417 | 1.320 † | 1.545 † | 1.781 † | 0.96 | 12.18 | 2.1% | 0.00% | 99.0% · 99.9% | 8: ऊ ऋ ऐ ◌ः ◌़ ऽ ॥ ॐ |
| 14 | himalaya-64k | 64,000 | **1.576** † | 1.489 | 1.374 † | 1.608 † | 1.865 † | 0.97 | 11.55 | 2.6% | 0.00% | 99.0% · 99.9% | 8: ऊ ऋ ऐ ◌ः ◌़ ऽ ॥ ॐ |
| 15 | indicbert-v2 | 250,000 | **1.578** | 1.578 | 1.236 | 1.235 | 1.354 | 1.09 | 11.54 | 6.3% | 0.00% | 31.1% · 97.5% | 0 |
| 16 | **yak-32k-v1** | 32,768 | **1.586** | 1.585 | 1.538 | 1.505 | 1.610 | 0.88 | 11.48 | 12.8% | 0.00% | 100.0% · 100.0% | 0 |
| 17 | nyayalm-64k | 64,000 | **1.602** | 1.519 | 1.338 | 2.057 | 2.073 | 1.02 | 11.36 | 4.0% | 0.00% | 100.0% · 100.0% | 6: ऊ ऋ ◌़ ऽ ॥ ॐ |
| 18 | arkios | 65,536 | **1.688** | 1.634 | 1.297 | 2.012 | 2.064 | 1.12 | 10.79 | 14.6% | 0.00% | 100.0% · 100.0% | 1: ॐ |
| 19 | bloom | 250,680 | **1.724** | 1.723 | 1.253 | 1.367 | 1.733 | 1.18 | 10.56 | 16.7% | 0.00% | 100.0% · 100.0% | 0 |
| 20 | xlm-r | 250,002 | **1.844** † | 1.844 | 1.400 † | 1.491 † | 1.961 † | 1.12 | 9.87 | 7.2% | 0.00% | 60.7% · 67.1% | 0 |
| 21 | param-2 | 128,000 | **1.873** | 1.872 | 1.490 | 1.446 | 1.545 | 1.07 | 9.72 | 18.8% | 0.00% | 100.0% · 100.0% | 0 |
| 22 | nllb-200 | 256,204 | **1.920** † | 1.920 | 1.399 † | 1.448 † | 1.541 † | 1.17 | 9.48 | 6.5% | 0.46% | 63.4% · 69.5% | 0 |
| 23 | gemma3 | 262,145 | **2.270** | 2.216 | 1.284 | 1.424 | 1.846 | 1.53 | 8.02 | 9.0% | 0.00% | 100.0% · 100.0% | 0 |
| 24 | sarvam-30b | 262,144 | **2.271** | 2.217 | 1.285 | 1.424 | 1.846 | 1.53 | 8.02 | 9.0% | 0.00% | 100.0% · 100.0% | 0 |
| 25 | gpt-oss | 200,019 | **2.321** | 2.320 | 1.227 | 1.648 | 1.920 | 1.61 | 7.84 | 25.8% | 0.00% | 100.0% · 100.0% | 1: ॐ |
| 26 | o200k | 200,019 | **2.321** | 2.320 | 1.227 | 1.648 | 1.920 | 1.61 | 7.84 | 25.8% | 0.00% | 100.0% · 100.0% | 1: ॐ |
| 27 | brahmic-131k | 131,072 | **2.321** | 2.320 | 1.240 | 1.648 | 1.920 | 1.60 | 7.84 | 25.8% | 0.00% | 100.0% · 100.0% | 0 |
| 28 | mt5 | 250,100 | **2.638** † | 2.638 | 1.543 † | 2.086 † | 2.382 † | 1.46 | 6.90 | 10.9% | 0.00% | 63.7% · 70.0% | 0 |
| 29 | param-1 | 256,011 | **2.657** | 2.578 | 1.286 | 1.839 | 2.317 | 1.79 | 6.85 | 12.3% | 0.00% | 100.0% · 100.0% | 6: ऋ ◌ः ऽ ॥ ८ ॐ |
| 30 | sarvam-1 | 68,096 | **2.659** | 2.589 | 1.498 | 1.448 | 1.941 | 1.54 | 6.85 | 13.5% | 0.00% | 100.0% · 100.0% | 5: ऋ ङ ऽ ॥ ॐ |
| 31 | gemma2 | 256,000 | **3.133** | 3.079 | 1.281 | 2.002 | 2.542 | 2.13 | 5.81 | 18.9% | 0.00% | 100.0% · 100.0% | 0 |
| 32 | krutrim-2 | 131,072 | **3.169** | 3.168 | 1.271 | 1.949 | 2.556 | 2.13 | 5.75 | 32.7% | 0.00% | 100.0% · 100.0% | 3: ऋ ऽ ॐ |
| 33 | mistral-nemo | 131,072 | **3.169** | 3.168 | 1.271 | 1.949 | 2.556 | 2.13 | 5.75 | 32.7% | 0.00% | 100.0% · 100.0% | 3: ऋ ऽ ॐ |
| 34 | sarvam-m | 131,072 | **3.169** | 3.168 | 1.271 | 1.949 | 2.556 | 2.13 | 5.75 | 32.7% | 0.00% | 100.0% · 100.0% | 3: ऋ ऽ ॐ |
| 35 | airavata | 48,065 | **3.182** | 3.129 | 1.480 | 1.855 | 2.409 | 1.88 | 5.72 | 10.1% | 0.00% | 100.0% · 100.0% | 21: ऊ ऋ ऐ ङ झ ञ ◌ँ ◌ः ऽ ॥ ० १ २ ३ ४ ५ ६ ७ ८ ९ ॐ |
| 36 | llama3 | 128,256 | **3.764** | 3.753 | 1.241 | 2.676 | 2.858 | 2.58 | 4.84 | 55.3% | 0.00% | 100.0% · 100.0% | 4: ङ ऽ ॥ ॐ |
| 37 | deepseek-v3 | 128,815 | **4.291** | 4.291 | 1.235 | 2.944 | 3.428 | 2.97 | 4.24 | 37.8% | 0.00% | 100.0% · 100.0% | 7: ऊ ऋ ऐ ओ झ ढ ॐ |
| 38 | krutrim-1 | 70,212 | **4.802** | 4.745 | 1.386 | 3.351 | 3.454 | 3.07 | 3.79 | 43.3% | 0.00% | 0.0% · 100.0% | 0 |
| 39 | qwen2.5 | 151,665 | **6.575** | 6.521 | 1.261 | 4.768 | 4.962 | 4.42 | 2.77 | 31.7% | 0.00% | 100.0% · 100.0% | 19: ङ ◌ँ ◌ः ◌़ ऽ ◌ू ◌ृ ◌ै ◌ौ ० १ २ ३ ४ ५ ६ ७ ८ ९ |
| 40 | qwen3 | 151,669 | **6.575** | 6.521 | 1.261 | 4.768 | 4.962 | 4.42 | 2.77 | 31.7% | 0.00% | 100.0% · 100.0% | 19: ङ ◌ँ ◌ः ◌़ ऽ ◌ू ◌ृ ◌ै ◌ौ ० १ २ ३ ४ ५ ६ ७ ८ ९ |
| 41 | cl100k | 100,277 | **6.979** | 6.926 | 1.241 | 5.065 | 5.431 | 4.76 | 2.61 | 29.9% | 0.00% | 100.0% · 100.0% | 56: अ आ इ ई उ ऊ ऋ ए ऐ ओ औ ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण थ द ध फ ब भ य व श ष ◌ँ ◌ः ◌़ ऽ ◌ू ◌ृ ◌ै ◌ौ । ॥ ० १ २ ३ ४ ५ ६ ७ ८ ९ ॐ |
| 42 | gpt2 | 50,257 | **10.973** | 10.919 | 1.281 | 7.866 | 8.190 | 7.55 | 1.66 | 19.1% | 0.00% | 100.0% · 100.0% | 72: अ आ इ ई उ ऊ ऋ ए ऐ ओ औ क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह ◌ँ ◌ं ◌ः ◌़ ऽ ◌ि ◌ी ◌ु ◌ू ◌ृ ◌े ◌ै ◌ो ◌ौ ◌् । ॥ ० १ २ ३ ४ ५ ६ ७ ८ ९ ॐ |

† = not lossless on that text: the tokenizer emits unknown tokens or loses characters (content round-trip below 100%), which makes its numbers look better than they are.

## Other languages of Nepal and Nepali-specific diagnostics

FLORES+ devtest fertility for Bhojpuri, Sanskrit, Awadhi, Magahi and Santali (Ol Chiki). Tibetan has no spaces between words, so it gets chars/token instead.

| Tokenizer | bho | san | awa | mag | sat | bod chars/tok | hin parity | npi chars/tok | npi vocab used | npi mid-char | npi byte pieces | everyday npi byte pieces | Devanagari block without a token | npi Rényi eff. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| yak-128k-v1-phrase | 1.364 | 2.180 | 1.371 | 1.355 | 2.651 | 3.08 | 1.18 | 5.40 | 7.0% | 0.0% | 0.06% | 0.10% | 0 / 128 | 0.425 |
| sai-nep-128k | 1.614 † | 2.288 † | 1.569 † | 1.552 † | 2.078 † | 29.23 † | 0.48 | 5.18 | 5.7% | 0.0% | 0.00% | 0.00% | 59 / 128 | 0.397 |
| yak-128k-v1 | 1.361 | 2.143 | 1.383 | 1.359 | 2.561 | 3.12 | 1.17 | 4.99 | 6.2% | 0.0% | 0.04% | 0.09% | 0 / 128 | 0.424 |
| yak-64k-v1-phrase | 1.485 | 2.385 | 1.474 | 1.482 | 3.160 | 2.77 | 1.18 | 4.98 | 12.7% | 0.0% | 0.09% | 0.13% | 0 / 128 | 0.462 |
| yak-128k-v2.0 | 1.328 | 2.126 | 1.324 | 1.353 | 1.857 | 3.26 | 1.16 | 4.95 | 6.0% | 0.0% | 0.02% | 0.05% | 0 / 128 | 0.424 |
| nepali-bpe | 1.789 † | 2.706 † | 1.731 † | 1.774 † | 4.851 † | 1.01 † | 0.41 | 4.77 | 14.7% | 0.0% | 0.00% | 0.00% | 22 / 128 | 0.388 |
| sidskarki-64k | 1.719 | 2.586 | 1.669 | 1.705 | 15.380 | 0.92 | 0.80 | 4.73 | 12.3% | 0.4% | 0.60% | 0.75% | 26 / 128 | 0.427 |
| yak-64k-v1 | 1.467 | 2.347 | 1.465 | 1.443 | 3.038 | 2.84 | 1.16 | 4.70 | 11.6% | 0.0% | 0.07% | 0.12% | 0 / 128 | 0.458 |
| himalaya-128k | 1.679 † | 2.940 † | 1.625 † | 1.680 † | 15.382 † | 0.34 † | 1.38 | 4.68 | 6.2% | 2.1% | 3.21% | 2.42% | 63 / 128 | 0.401 |
| yak-64k-v2.0 | 1.422 | 2.329 | 1.415 | 1.430 | 2.133 | 3.04 | 1.14 | 4.65 | 11.2% | 0.0% | 0.02% | 0.06% | 0 / 128 | 0.458 |
| nepberta | 1.874 † | 2.701 † | 1.792 † | 1.851 † | 1.130 † | 1.96 † | 0.53 | 4.62 | 21.4% | 0.0% | 0.00% | 0.00% | 38 / 128 | 0.478 |
| muril | 1.504 † | 1.949 † | 1.396 † | 1.473 † | 1.128 † | 1.97 † | 1.16 | 4.59 | 3.2% | 0.0% | 0.00% | 0.00% | 36 / 128 | 0.402 |
| himalaya-100k | 1.711 † | 2.989 † | 1.660 † | 1.710 † | 15.382 † | 0.34 † | 1.38 | 4.58 | 7.8% | 2.1% | 3.14% | 2.37% | 63 / 128 | 0.413 |
| himalaya-64k | 1.793 † | 3.094 † | 1.731 † | 1.773 † | 15.383 † | 0.34 † | 1.38 | 4.34 | 11.3% | 2.0% | 2.98% | 2.27% | 63 / 128 | 0.436 |
| indicbert-v2 | 1.467 | 2.067 | 1.374 | 1.405 | 2.208 | 1.05 † | 1.17 | 4.33 | 2.4% | 0.0% | 0.00% | 0.00% | 3 / 128 | 0.397 |
| yak-32k-v1 | 1.626 | 2.589 | 1.612 | 1.635 | 3.778 | 2.46 | 1.15 | 4.31 | 20.2% | 0.1% | 0.13% | 0.20% | 0 / 128 | 0.498 |
| nyayalm-64k | 2.065 | 2.905 | 2.001 | 2.041 | 15.381 | 0.34 | 1.85 | 4.27 | 10.7% | 0.2% | 0.35% | 1.00% | 61 / 128 | 0.439 |
| arkios | 2.027 | 2.884 | 1.942 | 1.995 | 14.430 | 0.44 | 1.85 | 4.05 | 9.5% | 0.2% | 0.46% | 0.57% | 55 / 128 | 0.446 |
| bloom | 1.637 | 2.622 | 1.536 | 1.585 | 14.427 | 0.82 | 1.28 | 3.97 | 2.2% | 0.0% | 0.06% | 0.09% | 38 / 128 | 0.420 |
| xlm-r | 1.760 † | 2.561 † | 1.647 † | 1.725 † | 2.082 † | 6.93 † | 1.25 | 3.71 | 1.6% | 0.0% | 0.00% | 0.00% | 34 / 128 | 0.401 |
| param-2 | 1.688 | 2.308 | 1.593 | 1.636 | 2.361 | 0.44 | 1.14 | 3.65 | 3.9% | 0.2% | 0.35% | 4.63% | 0 / 128 | 0.450 |
| nllb-200 | 1.521 † | 2.518 † | 1.457 † | 1.493 † | 3.158 † | 3.41 † | 1.21 | 3.56 | 1.6% | 0.0% | 0.00% | 0.00% | 41 / 128 | 0.407 |
| gemma3 | 1.705 | 2.887 | 1.605 | 1.639 | 5.962 | 1.48 | 1.31 | 3.01 | 1.5% | 0.0% | 0.00% | 0.00% | 30 / 128 | 0.391 |
| sarvam-30b | 1.705 | 2.887 | 1.605 | 1.639 | 2.085 | 1.79 | 1.31 | 3.01 | 1.5% | 0.0% | 0.01% | 0.00% | 30 / 128 | 0.391 |
| gpt-oss | 1.858 | 3.302 | 1.803 | 1.842 | 15.347 | 0.68 | 1.57 | 2.95 | 1.4% | 0.3% | 0.67% | 0.59% | 44 / 128 | 0.436 |
| o200k | 1.858 | 3.302 | 1.803 | 1.842 | 15.347 | 0.68 | 1.57 | 2.95 | 1.4% | 0.3% | 0.67% | 0.59% | 44 / 128 | 0.436 |
| brahmic-131k | 1.858 | 3.299 | 1.803 | 1.842 | 15.347 | 0.51 | 1.56 | 2.95 | 2.2% | 0.3% | 0.66% | 0.59% | 0 / 128 | 0.452 |
| mt5 | 2.150 † | 3.252 † | 2.142 † | 2.171 † | 3.785 † | 1.20 † | 1.58 | 2.59 | 1.1% | 0.0% | 0.00% | 0.00% | 30 / 128 | 0.312 |
| param-1 | 2.094 | 3.852 | 2.024 | 2.098 | 15.376 | 0.34 | 1.69 | 2.57 | 0.8% | 0.2% | 0.33% | 0.58% | 58 / 128 | 0.401 |
| sarvam-1 | 1.749 | 3.048 | 1.637 | 1.681 | 15.380 | 0.34 | 1.13 | 2.57 | 5.6% | 1.1% | 1.65% | 1.44% | 55 / 128 | 0.426 |
| gemma2 | 2.271 | 3.694 | 2.210 | 2.259 | 5.845 | 1.50 | 1.86 | 2.18 | 0.6% | 0.0% | 0.00% | 0.00% | 27 / 128 | 0.398 |
| krutrim-2 | 2.261 | 3.744 | 2.226 | 2.270 | 14.436 | 0.44 | 1.80 | 2.16 | 1.1% | 1.4% | 2.72% | 2.72% | 49 / 128 | 0.431 |
| mistral-nemo | 2.261 | 3.744 | 2.226 | 2.270 | 14.436 | 0.44 | 1.80 | 2.16 | 1.1% | 1.4% | 2.72% | 2.72% | 49 / 128 | 0.431 |
| sarvam-m | 2.261 | 3.744 | 2.226 | 2.270 | 14.436 | 0.44 | 1.80 | 2.16 | 1.1% | 1.4% | 2.72% | 2.72% | 49 / 128 | 0.431 |
| airavata | 2.082 | 4.007 | 2.101 | 2.102 | 15.377 | 0.72 | 1.49 | 2.15 | 5.8% | 3.3% | 5.00% | 8.39% | 75 / 128 | 0.432 |
| llama3 | 2.759 | 4.218 | 2.713 | 2.778 | 14.435 | 0.49 | 2.52 | 1.82 | 1.0% | 0.8% | 1.52% | 1.43% | 53 / 128 | 0.379 |
| deepseek-v3 | 3.066 | 4.550 | 3.084 | 3.114 | 7.256 | 0.89 | 2.79 | 1.59 | 0.6% | 5.1% | 10.13% | 10.33% | 59 / 128 | 0.382 |
| krutrim-1 | 3.313 | 5.281 | 3.345 | 3.380 | 15.377 | 0.34 | 2.94 | 1.42 | 2.9% | 0.0% | 0.01% | 0.10% | 31 / 128 | 0.279 |
| qwen2.5 | 4.646 | 7.390 | 4.718 | 4.660 | 10.284 | 0.74 | 4.42 | 1.04 | 0.3% | 28.5% | 57.02% | 57.24% | 67 / 128 | 0.286 |
| qwen3 | 4.646 | 7.390 | 4.718 | 4.660 | 10.284 | 0.74 | 4.42 | 1.04 | 0.3% | 28.5% | 57.02% | 57.24% | 67 / 128 | 0.286 |
| cl100k | 4.991 | 7.967 | 5.125 | 5.126 | 14.436 | 0.49 | 4.77 | 0.98 | 0.5% | 33.0% | 65.98% | 66.04% | 111 / 128 | 0.295 |
| gpt2 | 7.630 | 12.577 | 7.658 | 7.817 | 14.430 | 0.37 | 7.42 | 0.62 | 1.1% | 46.8% | 93.62% | 93.01% | 127 / 128 | 0.190 |

## Languages of Nepal (held-out text)

Fertility on 500 held-out segments per language: Athpariya (aph), Dhimal (dhi), Gurung (gvr), Kulung (kle), Kayort (kyv), Lohorung (lbr), Limbu (lif), Magar (mgp), Newar (new), Sampang (rav), Sunuwar (suz), Tamang (taj), Tharu Dangaura (thl), Tharu Rana (thr). Parity is tokens of the same 300 line-aligned segments divided by Nepali tokens (1.00 = as cheap as Nepali). This text cannot be redistributed, so these sets are not in the repository and a public run skips them.

| Tokenizer | aph | dhi | gvr | kle | kyv | lbr | lif | mgp | new | rav | suz | taj | thl | thr | mean fertility | mean parity vs npi | worst parity vs npi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| yak-128k-v1-phrase | 3.75 | 2.11 | 2.72 | 3.03 | 1.91 | 3.57 | 2.86 | 2.06 | 2.20 | 3.01 | 2.30 | 2.28 | 1.96 | 1.70 | 2.532 | 1.90 | 2.92 (lif) |
| sai-nep-128k | 3.31 † | 2.41 † | 2.32 † | 2.93 † | 2.02 † | 3.23 † | 2.80 † | 1.95 † | 2.72 † | 3.16 † | 2.30 † | 2.03 † | 1.95 † | 1.82 † | 2.497 | 1.78 | 2.90 (lif) |
| yak-128k-v1 | 3.74 | 2.04 | 2.68 | 3.01 | 1.86 | 3.54 | 2.83 | 2.06 | 2.17 | 3.00 | 2.25 | 2.26 | 1.95 | 1.69 | 2.505 | 1.82 | 2.81 (lif) |
| yak-64k-v1-phrase | 4.03 | 2.53 | 2.86 | 3.20 | 2.03 | 3.91 | 3.12 | 2.18 | 2.47 | 3.29 | 2.55 | 2.47 | 2.08 | 1.80 | 2.751 | 1.93 | 3.05 (lif) |
| yak-128k-v2.0 | 1.79 | 1.46 | 1.48 | 1.78 | 1.39 | 1.75 | 1.88 | 1.77 | 1.77 | 1.83 | 1.49 | 1.70 | 1.43 | 1.28 | 1.629 | 1.19 | 1.34 (aph) |
| nepali-bpe | 3.33 † | 2.67 † | 2.88 † | 2.89 † | 2.28 † | 3.21 † | 3.00 † | 2.18 † | 2.74 † | 3.01 † | 2.41 † | 2.42 † | 2.25 † | 2.00 † | 2.662 | 2.06 | 3.03 (lif) |
| sidskarki-64k | 5.30 | 2.74 | 3.11 | 3.64 | 2.13 | 4.66 | 3.18 | 2.10 | 3.57 | 3.79 | 3.22 | 2.37 | 2.09 | 1.94 | 3.131 | 1.99 | 3.59 (lif) |
| yak-64k-v1 | 4.28 | 2.48 | 2.85 | 3.20 | 2.01 | 3.84 | 3.08 | 2.15 | 2.45 | 3.26 | 2.53 | 2.44 | 2.07 | 1.79 | 2.743 | 1.89 | 2.94 (lif) |
| himalaya-128k | 5.47 | 2.78 | 3.15 | 3.83 | 2.22 | 5.44 | 4.26 | 2.11 | 3.99 | 4.01 | 3.43 | 2.43 | 2.20 | 2.03 | 3.384 | 2.07 | 4.56 (lif) |
| yak-64k-v2.0 | 2.12 | 1.65 | 1.65 | 2.06 | 1.55 | 2.04 | 2.13 | 1.95 | 1.97 | 2.15 | 1.65 | 1.89 | 1.59 | 1.39 | 1.843 | 1.27 | 1.48 (aph) |
| nepberta | 3.34 † | 2.73 † | 2.92 † | 3.03 † | 2.39 | 3.26 † | 3.06 † | 2.24 † | 2.80 † | 3.14 † | 2.56 † | 2.50 | 2.28 | 2.10 † | 2.740 | 2.01 | 2.93 (lif) |
| muril | 3.24 † | 2.79 † | 2.85 † | 2.80 † | 2.16 | 3.00 † | 2.45 † | 2.20 † | 2.54 † | 2.96 † | 2.43 † | 2.52 | 2.16 | 1.87 † | 2.569 | 1.83 | 2.21 (aph) |
| himalaya-100k | 5.54 | 2.84 | 3.21 | 3.88 | 2.29 | 5.52 | 4.29 | 2.15 | 4.04 | 4.09 | 3.49 | 2.47 | 2.25 | 2.06 | 3.438 | 2.06 | 4.50 (lif) |
| himalaya-64k | 5.63 | 2.95 | 3.31 | 3.97 | 2.40 | 5.58 | 4.38 | 2.23 | 4.21 | 4.19 | 3.59 | 2.55 | 2.34 | 2.15 | 3.535 | 2.02 | 4.31 (lif) |
| indicbert-v2 | 3.68 | 2.72 | 2.71 | 2.87 | 1.94 | 3.57 | 3.04 | 2.15 | 2.57 | 3.01 | 2.41 | 2.43 | 2.05 | 1.81 | 2.639 | 1.74 | 2.79 (lif) |
| yak-32k-v1 | 4.56 | 2.87 | 3.12 | 3.41 | 2.19 | 4.24 | 3.39 | 2.32 | 2.70 | 3.51 | 2.84 | 2.72 | 2.26 | 1.94 | 3.005 | 1.89 | 3.03 (lif) |
| nyayalm-64k | 5.08 | 2.93 | 3.19 | 3.62 | 2.50 | 4.90 | 4.30 | 2.29 | 3.44 | 3.79 | 3.03 | 2.64 | 2.43 | 2.23 | 3.312 | 2.10 | 4.15 (lif) |
| arkios | 5.52 | 3.07 | 3.56 | 4.10 | 2.51 | 5.33 | 4.05 | 2.41 | 3.76 | 4.14 | 3.63 | 2.88 | 2.43 | 2.25 | 3.546 | 2.02 | 3.71 (lif) |
| bloom | 4.25 | 3.07 | 3.11 | 3.39 | 2.28 | 4.16 | 3.53 | 2.34 | 2.91 | 3.43 | 2.76 | 2.77 | 2.27 | 1.98 | 3.019 | 1.74 | 2.81 (lif) |
| xlm-r | 3.93 † | 3.12 † | 3.17 † | 3.34 † | 2.43 | 3.70 † | 3.29 † | 2.54 † | 3.06 † | 3.59 † | 2.81 † | 2.87 | 2.40 | 2.15 † | 3.029 | 1.64 | 2.39 (lif) |
| param-2 | 5.15 | 3.12 | 3.53 | 3.89 | 2.32 | 4.80 | 4.17 | 2.54 | 3.57 | 4.00 | 3.38 | 2.90 | 2.37 | 2.12 | 3.419 | 1.57 | 2.85 (lif) |
| nllb-200 | 3.85 † | 3.03 † | 2.97 † | 3.15 † | 2.06 † | 3.61 † | 3.24 † | 2.54 † | 2.86 † | 3.39 † | 2.70 † | 2.91 † | 2.22 † | 1.81 † | 2.880 | 1.67 | 2.52 (lif) |
| gemma3 | 4.22 | 3.06 | 3.14 | 3.28 | 2.38 | 4.33 | 3.62 | 2.51 | 3.07 | 3.43 | 2.71 | 2.85 | 2.37 | 2.06 | 3.074 | 1.41 | 2.26 (lif) |
| sarvam-30b | 4.22 | 3.06 | 3.14 | 3.28 | 2.38 | 4.33 | 3.62 | 2.51 | 3.07 | 3.43 | 2.71 | 2.85 | 2.37 | 2.06 | 3.074 | 1.41 | 2.26 (lif) |
| gpt-oss | 5.22 | 3.42 | 3.59 | 3.97 | 2.62 | 5.12 | 4.13 | 2.71 | 3.76 | 4.01 | 3.49 | 3.38 | 2.65 | 2.23 | 3.592 | 1.56 | 2.59 (lif) |
| o200k | 5.22 | 3.42 | 3.59 | 3.97 | 2.62 | 5.12 | 4.13 | 2.71 | 3.76 | 4.01 | 3.49 | 3.38 | 2.65 | 2.23 | 3.592 | 1.56 | 2.59 (lif) |
| brahmic-131k | 5.21 | 3.42 | 3.53 | 3.94 | 2.62 | 4.79 | 3.93 | 2.69 | 3.75 | 3.99 | 3.41 | 3.35 | 2.64 | 2.22 | 3.536 | 1.54 | 2.45 (lif) |
| mt5 | 4.03 † | 3.13 † | 3.37 † | 3.55 † | 2.81 | 3.82 † | 3.47 † | 2.78 † | 3.14 † | 3.69 † | 2.96 † | 3.15 | 2.76 | 2.36 † | 3.215 | 1.30 | 1.79 (lif) |
| param-1 | 4.99 | 3.47 | 3.59 | 3.80 | 2.78 | 5.18 | 4.11 | 2.86 | 3.92 | 3.96 | 3.24 | 3.27 | 2.73 | 2.31 | 3.586 | 1.49 | 2.48 (lif) |
| sarvam-1 | 6.27 | 3.64 | 3.41 | 3.99 | 2.45 | 5.95 | 4.50 | 2.95 | 3.47 | 3.86 | 3.09 | 3.24 | 2.47 | 2.14 | 3.673 | 1.46 | 2.64 (lif) |
| gemma2 | 5.13 | 3.65 | 3.80 | 3.94 | 3.02 | 4.77 | 4.08 | 3.03 | 3.83 | 4.23 | 3.41 | 3.52 | 2.93 | 2.43 | 3.698 | 1.31 | 2.00 (lif) |
| krutrim-2 | 5.84 | 3.89 | 3.86 | 4.36 | 2.99 | 5.61 | 4.70 | 3.16 | 4.01 | 4.41 | 3.79 | 3.82 | 2.94 | 2.45 | 3.988 | 1.36 | 2.34 (lif) |
| mistral-nemo | 5.84 | 3.89 | 3.86 | 4.36 | 2.99 | 5.61 | 4.70 | 3.16 | 4.01 | 4.41 | 3.79 | 3.82 | 2.94 | 2.45 | 3.988 | 1.36 | 2.34 (lif) |
| sarvam-m | 5.84 | 3.89 | 3.86 | 4.36 | 2.99 | 5.61 | 4.70 | 3.16 | 4.01 | 4.41 | 3.79 | 3.82 | 2.94 | 2.45 | 3.988 | 1.36 | 2.34 (lif) |
| airavata | 5.89 | 3.82 | 4.06 | 4.19 | 2.90 | 6.02 | 5.10 | 3.31 | 4.06 | 4.54 | 3.33 | 3.67 | 2.98 | 2.40 | 4.020 | 1.34 | 2.33 (lif) |
| llama3 | 6.00 | 4.22 | 3.99 | 4.57 | 3.29 | 5.57 | 4.97 | 3.39 | 4.02 | 4.64 | 3.67 | 4.09 | 3.26 | 2.78 | 4.175 | 1.27 | 2.13 (lif) |
| deepseek-v3 | 7.09 | 4.77 | 4.61 | 5.20 | 4.06 | 6.43 | 4.99 | 3.73 | 4.53 | 5.61 | 4.31 | 4.56 | 3.83 | 3.17 | 4.778 | 1.26 | 1.92 (lif) |
| krutrim-1 | 6.54 | 5.36 | 4.49 | 5.27 | 3.98 | 6.14 | 5.45 | 4.24 | 4.21 | 5.66 | 4.18 | 5.43 | 3.87 | 3.05 | 4.849 | 1.22 | 1.74 (lif) |
| qwen2.5 | 8.65 | 6.57 | 6.47 | 7.21 | 5.91 | 8.07 | 6.68 | 5.45 | 6.37 | 7.76 | 5.98 | 6.61 | 5.59 | 4.69 | 6.571 | 1.16 | 1.62 (lif) |
| qwen3 | 8.65 | 6.57 | 6.47 | 7.21 | 5.91 | 8.07 | 6.68 | 5.45 | 6.37 | 7.76 | 5.98 | 6.61 | 5.59 | 4.69 | 6.571 | 1.16 | 1.62 (lif) |
| cl100k | 9.25 | 6.88 | 7.06 | 7.72 | 6.35 | 8.54 | 7.00 | 5.81 | 7.04 | 8.27 | 6.49 | 7.02 | 5.98 | 5.11 | 7.037 | 1.16 | 1.61 (lif) |
| gpt2 | 13.86 | 10.82 | 10.49 | 11.41 | 9.64 | 12.54 | 10.90 | 8.71 | 10.10 | 11.64 | 9.71 | 10.97 | 9.37 | 7.47 | 10.545 | 1.15 | 1.65 (lif) |

## Domains: everyday and Romanized Nepali

Everyday Nepali is human-written prompts and answers from the Aya dataset. The word lists are 2,804 Nepali words in Romanized and Devanagari spelling (one word per segment).

| Tokenizer | everyday npi (Aya) fertility | Devanagari words fertility | Romanized words fertility | eng chars/tok |
|---|---:|---:|---:|---:|
| yak-128k-v1-phrase | 1.267 | 2.883 | 3.672 | 4.93 |
| sai-nep-128k | 1.308 † | 2.116 † | 6.976 † | 1.63 † |
| yak-128k-v1 | 1.360 | 2.833 | 3.609 | 4.70 |
| yak-64k-v1-phrase | 1.377 | 3.156 | 3.993 | 4.50 |
| yak-128k-v2.0 | 1.368 | 2.766 | 3.687 | 4.63 |
| nepali-bpe | 1.403 † | 2.453 | 10.377 † | 1.21 † |
| sidskarki-64k | 1.407 | 2.368 | 5.332 | 2.52 |
| yak-64k-v1 | 1.446 | 3.117 | 3.945 | 4.37 |
| himalaya-128k | 1.426 † | 2.386 | 3.114 | 4.68 † |
| yak-64k-v2.0 | 1.455 | 3.003 | 4.005 | 4.28 |
| nepberta | 1.447 † | 2.641 | 6.672 † | 1.49 † |
| muril | 1.450 † | 2.866 | 3.406 | 4.82 † |
| himalaya-100k | 1.457 † | 2.471 | 3.214 | 4.60 † |
| himalaya-64k | 1.525 † | 2.677 | 3.434 | 4.42 † |
| indicbert-v2 | 1.542 † | 2.817 | 3.140 | 4.91 |
| yak-32k-v1 | 1.569 | 3.432 | 4.289 | 3.95 |
| nyayalm-64k | 1.575 | 2.866 | 4.354 | 4.54 |
| arkios | 1.648 | 3.475 | 4.444 | 4.68 |
| bloom | 1.690 | 3.597 | 3.945 | 4.85 |
| xlm-r | 1.792 † | 3.432 | 3.556 | 4.34 † |
| param-2 | 1.911 | 3.808 | 4.577 | 4.07 |
| nllb-200 | 1.897 † | 3.660 | 3.526 | 4.34 † |
| gemma3 | 2.133 | 4.034 | 3.769 | 4.73 |
| sarvam-30b | 2.133 | 4.034 | 3.769 | 4.73 |
| gpt-oss | 2.270 | 4.652 | 3.888 | 4.95 |
| o200k | 2.270 | 4.652 | 3.888 | 4.95 |
| brahmic-131k | 2.270 | 4.638 | 3.962 | 4.90 |
| mt5 | 2.577 † | 3.810 | 3.477 | 3.94 † |
| param-1 | 2.567 | 4.431 | 3.714 | 4.72 |
| sarvam-1 | 2.483 | 4.153 | 5.007 | 4.05 |
| gemma2 | 2.973 | 5.206 | 3.699 | 4.74 |
| krutrim-2 | 3.039 | 5.405 | 4.179 | 4.78 |
| mistral-nemo | 3.039 | 5.405 | 4.179 | 4.78 |
| sarvam-m | 3.039 | 5.405 | 4.179 | 4.78 |
| airavata | 3.095 | 4.776 | 4.531 | 4.10 |
| llama3 | 3.620 | 5.881 | 4.230 | 4.89 |
| deepseek-v3 | 4.117 | 6.745 | 4.151 | 4.92 |
| krutrim-1 | 4.615 | 7.627 | 4.555 | 4.38 |
| qwen2.5 | 6.284 | 9.313 | 4.269 | 4.81 |
| qwen3 | 6.284 | 9.313 | 4.269 | 4.81 |
| cl100k | 6.691 | 10.536 | 4.269 | 4.89 |
| gpt2 | 10.536 | 17.400 | 4.440 | 4.74 |

## Robustness probes

Each cell is *token ratio · content round-trip* on FLORES+ devtest sentences rewritten the way Nepali text often arrives (`src/yak_tokenizer/eval/robustness.py`). A token ratio of 1.000 means the variant costs no extra tokens. *raw non-NFC hin* is the published Hindi file (precomposed nukta letters) against its NFC form; plain NFD is not used because it changes 1 character of the NFC Nepali devtest. The other probes rewrite the Nepali devtest: a ZWJ or ZWNJ after every virama before a consonant, short/long vowel-sign swaps in 20% of eligible words (fixed seed), and every danda typed as a pipe.

| Tokenizer | raw non-NFC hin | ZWJ after virama | ZWNJ after virama | ि/ी ु/ू typos | danda typed as pipe |
|---|---:|---:|---:|---:|---:|
| yak-128k-v1-phrase | 1.005 · 100% | 1.780 · 100% | 1.951 · 100% | 1.067 · 100% | 1.001 · 100% |
| sai-nep-128k | 1.000 · 31% | 1.911 · 0% | 1.600 · 0% | 1.043 · 70% | 1.000 · 0% |
| yak-128k-v1 | 1.005 · 100% | 1.683 · 100% | 1.848 · 100% | 1.053 · 100% | 1.001 · 100% |
| yak-64k-v1-phrase | 1.003 · 100% | 1.731 · 100% | 1.873 · 100% | 1.066 · 100% | 1.001 · 100% |
| yak-128k-v2.0 | 1.006 · 100% | 1.514 · 100% | 1.744 · 100% | 1.049 · 100% | 1.001 · 100% |
| nepali-bpe | 0.999 · 73% | 1.000 · 0% | 1.000 · 0% | 1.055 · 65% | 1.000 · 65% |
| sidskarki-64k | 1.007 · 100% | 2.560 · 100% | 2.560 · 100% | 1.051 · 100% | 1.001 · 100% |
| yak-64k-v1 | 1.004 · 100% | 1.661 · 100% | 1.965 · 100% | 1.055 · 100% | 1.001 · 100% |
| himalaya-128k | 1.000 · 91% | 2.531 · 100% | 2.531 · 100% | 1.050 · 100% | 1.000 · 100% |
| yak-64k-v2.0 | 1.004 · 100% | 1.504 · 100% | 1.691 · 100% | 1.051 · 100% | 1.001 · 100% |
| nepberta | 0.993 · 86% | 1.000 · 0% | 1.000 · 0% | 1.059 · 84% | 1.000 · 84% |
| muril | 1.002 · 100% | 1.000 · 1% | 1.000 · 1% | 1.052 · 95% | 1.000 · 95% |
| himalaya-100k | 1.000 · 91% | 2.504 · 100% | 2.504 · 100% | 1.051 · 100% | 1.000 · 100% |
| himalaya-64k | 1.000 · 91% | 2.440 · 100% | 2.440 · 100% | 1.053 · 100% | 1.000 · 100% |
| indicbert-v2 | 1.002 · 100% | 1.437 · 100% | 1.640 · 100% | 1.043 · 100% | 1.001 · 100% |
| yak-32k-v1 | 1.002 · 100% | 1.662 · 100% | 1.922 · 100% | 1.054 · 100% | 1.001 · 100% |
| nyayalm-64k | 0.999 · 100% | 1.733 · 100% | 2.434 · 100% | 1.066 · 100% | 1.000 · 100% |
| arkios | 1.000 · 91% | 2.206 · 100% | 2.206 · 100% | 1.053 · 100% | 1.000 · 100% |
| bloom | 1.003 · 100% | 1.494 · 100% | 1.611 · 100% | 1.044 · 100% | 1.000 · 100% |
| xlm-r | 1.000 · 91% | 1.459 · 1% | 1.459 · 1% | 1.044 · 95% | 1.001 · 95% |
| param-2 | 1.007 · 100% | 2.007 · 100% | 1.754 · 100% | 1.044 · 100% | 1.000 · 100% |
| nllb-200 | 1.000 · 84% | 1.340 · 0% | 1.340 · 0% | 1.035 · 88% | 1.000 · 88% |
| gemma3 | 1.001 · 100% | 1.326 · 100% | 1.458 · 100% | 1.026 · 100% | 1.000 · 100% |
| sarvam-30b | 1.001 · 100% | 1.326 · 100% | 1.458 · 100% | 1.025 · 100% | 1.000 · 100% |
| gpt-oss | 1.001 · 100% | 1.525 · 100% | 1.556 · 100% | 1.026 · 100% | 1.000 · 100% |
| o200k | 1.001 · 100% | 1.525 · 100% | 1.556 · 100% | 1.026 · 100% | 1.000 · 100% |
| brahmic-131k | 1.001 · 100% | 1.518 · 100% | 1.549 · 100% | 1.025 · 100% | 1.000 · 100% |
| mt5 | 1.000 · 91% | 1.246 · 1% | 1.246 · 1% | 1.011 · 95% | 1.000 · 95% |
| param-1 | 1.007 · 100% | 1.323 · 100% | 1.387 · 100% | 1.019 · 100% | 1.000 · 100% |
| sarvam-1 | 1.011 · 100% | 1.330 · 100% | 1.754 · 100% | 1.017 · 100% | 1.000 · 100% |
| gemma2 | 1.001 · 100% | 1.295 · 100% | 1.295 · 100% | 1.008 · 100% | 1.000 · 100% |
| krutrim-2 | 1.000 · 100% | 1.370 · 100% | 1.370 · 100% | 1.012 · 100% | 1.000 · 100% |
| mistral-nemo | 1.000 · 100% | 1.370 · 100% | 1.370 · 100% | 1.012 · 100% | 1.000 · 100% |
| sarvam-m | 1.000 · 100% | 1.370 · 100% | 1.370 · 100% | 1.012 · 100% | 1.000 · 100% |
| airavata | 1.008 · 100% | 1.250 · 100% | 1.250 · 100% | 1.010 · 100% | 1.000 · 100% |
| llama3 | 1.000 · 100% | 1.139 · 100% | 1.265 · 100% | 1.002 · 100% | 1.004 · 100% |
| deepseek-v3 | 1.001 · 100% | 1.246 · 100% | 1.356 · 100% | 1.004 · 100% | 1.000 · 100% |
| krutrim-1 | 0.999 · 100% | 1.000 · 100% | 1.000 · 100% | 1.000 · 100% | 1.003 · 100% |
| qwen2.5 | 1.000 · 91% | 1.158 · 100% | 1.085 · 100% | 1.001 · 100% | 1.000 · 100% |
| qwen3 | 1.000 · 91% | 1.158 · 100% | 1.085 · 100% | 1.001 · 100% | 1.000 · 100% |
| cl100k | 0.998 · 100% | 1.184 · 100% | 1.116 · 100% | 1.003 · 100% | 0.991 · 100% |
| gpt2 | 0.999 · 100% | 1.087 · 100% | 1.087 · 100% | 1.000 · 100% | 0.994 · 100% |

## Failed or skipped baselines

None.

Loading notes:

- `krutrim-1`: its `tokenizer.json` uses ByteLevel with `add_prefix_space=true`, so every decode gains a leading space. Exact round-trip is 0% for that reason alone; content round-trip is unaffected.
- `nepberta` ships only `vocab.txt`. AutoTokenizer's BERT defaults would also strip accents, deleting Devanagari vowel signs and the virama (नेपालमा -> नपालमा). Its vocab is full of those marks, so it is loaded with `strip_accents=false`.
- Sarvam-M and Krutrim-2 use Mistral's Tekken tokenizer, Qwen3 uses Qwen2.5's, sarvam-30b is very close to Gemma-3, and gpt-oss (o200k_harmony) tokenizes text like o200k, so their rows match.

## Eval sets

Built by `uv run python scripts/eval_panel.py fetch`. Licenses and attribution are in `data/eval/SOURCES.md` and checksums in `data/eval/MANIFEST.tsv`. FLORES+ text is kept out of git, because its gating terms forbid re-hosting it where crawlers can reach it.

| Text | Count mode | Segments | Words | Bytes | License | Source |
|---|---|---:|---:|---:|---|---|
| flores_devtest/npi_Deva | joined | 1012 | 18701 | 340483 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/eng_Latn | joined | 1012 | 21901 | 133107 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/hin_Deva | joined | 1012 | 25643 | 338450 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/mai_Deva | joined | 1012 | 24611 | 336610 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/bho_Deva | joined | 1012 | 25618 | 330213 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/san_Deva | joined | 1012 | 16975 | 347907 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/awa_Deva | joined | 1012 | 25403 | 331901 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/mag_Deva | joined | 1012 | 25044 | 327887 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/bod_Tibt | joined | 1012 | 2043 | 440060 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| flores_devtest/sat_Olck | joined | 1012 | 24053 | 370326 | CC-BY-SA-4.0 | openlanguagedata/flores_plus (devtest) |
| npi_latn_words | segments | 2804 | 2804 | 29186 | MIT | Saugatkafley/Nepali-Roman-Transliteration (validation; Romanized side, one word per line) |
| npi_latn_words_deva | segments | 2804 | 2804 | 77067 | MIT | Saugatkafley/Nepali-Roman-Transliteration (validation; Devanagari side of the same words) |
| npi_everyday_aya | segments | 1941 | 110440 | 1922920 | Apache-2.0 | CohereLabs/aya_dataset (train, language=Nepali; human-written prompt + answer, seeded sample) |
| nepal_langs/aph | segments | 500 | 10348 | 241265 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/dhi | segments | 500 | 7033 | 131137 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/gvr | segments | 500 | 7531 | 128258 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/kle | segments | 500 | 8903 | 168649 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/kyv | segments | 500 | 12109 | 192101 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/lbr | segments | 500 | 9331 | 196907 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/lif | segments | 500 | 2398 | 42650 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/mgp | segments | 500 | 4804 | 70611 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/new | segments | 500 | 9492 | 159602 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/rav | segments | 500 | 8814 | 176067 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/suz | segments | 500 | 11215 | 180577 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/taj | segments | 500 | 4834 | 90614 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/thl | segments | 500 | 11740 | 181461 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs/thr | segments | 500 | 12443 | 156378 | not redistributable | held-out segments, 500 per language (not public) |
| nepal_langs_aligned/npi | segments | 300 | 5824 | 98230 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/aph | segments | 300 | 6084 | 141440 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/dhi | segments | 300 | 6698 | 125277 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/gvr | segments | 300 | 5969 | 102332 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/kle | segments | 300 | 5354 | 101398 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/kyv | segments | 300 | 7428 | 117519 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/lbr | segments | 300 | 5656 | 118353 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/lif | segments | 300 | 5299 | 157762 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/mgp | segments | 300 | 6097 | 105442 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/new | segments | 300 | 5712 | 95634 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/rav | segments | 300 | 5056 | 101084 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/suz | segments | 300 | 6797 | 109090 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/taj | segments | 300 | 6240 | 118021 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/thl | segments | 300 | 7126 | 110602 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
| nepal_langs_aligned/thr | segments | 300 | 7488 | 94084 | not redistributable | the same 300 held-out segments in every language, line-aligned with Nepali (not public) |
