# Eval data: sources, licenses and attribution

Every file under `data/eval/` is listed here. `MANIFEST.tsv` records the path, segment/word/char/byte
counts, sha256, source repo, resolved source revision and license of each one. Rebuild everything
with `uv run python scripts/eval_panel.py fetch` (FLORES+ needs a Hugging Face account that has
accepted its terms). All builders are deterministic: they use a fixed order or a fixed seed.

These sets are evaluation-only: Yak's training text drops any document that shares a word 13-gram
with them.

## FLORES+ dev and devtest (`flores_plus/{dev,devtest}/<lang>.txt`): local only, not committed

- **Source:** [`openlanguagedata/flores_plus`](https://huggingface.co/datasets/openlanguagedata/flores_plus),
  revision `e707e62e762a9e2faca3933aa315f4665cc3cd8f` (FLORES+ v4.6), files `{split}/{lang}.jsonl`.
- **License:** CC BY-SA 4.0.
- **Attribution:** FLORES+ is maintained by the [Open Language Data Initiative](https://oldi.org/).
  It is based on FLORES-200 from the NLLB project at Meta AI: NLLB Team, "Scaling neural machine
  translation to 200 languages", *Nature* 630, 841–846 (2024); Goyal et al., "The Flores-101
  Evaluation Benchmark for Low-Resource and Multilingual Machine Translation", *TACL* (2022);
  Guzmán et al., "The FLORES Evaluation Datasets for Low-Resource Machine Translation", EMNLP 2019.
  Cite the papers in the dataset's `bibliography.bib` when publishing results.
- **Gating terms:** access requires agreeing *"not to re-host FLORES+ in places where it could be
  picked up by web crawlers"*. So `flores_plus/.gitignore` keeps the text out of git. Only its
  checksums in `MANIFEST.tsv` are committed. Publishing the text in a public repo would break that
  agreement, even though CC BY-SA 4.0 would allow it.
- **Languages:** `npi_Deva` Nepali, `eng_Latn`, `hin_Deva`, `mai_Deva` Maithili, `bho_Deva`
  Bhojpuri, `san_Deva` Sanskrit, `awa_Deva` Awadhi, `mag_Deva` Magahi, `bod_Tibt` Tibetan,
  `sat_Olck` Santali (Ol Chiki). FLORES+ has no Newar (`new_Deva`), Tharu or Tamang.
- **Format:** one sentence per line, ordered by FLORES `id` and line-aligned across languages
  (dev: 997 lines, devtest: 1,012). The text is unchanged; the harness NFC-normalises it in memory.
- **Check:** `npi_Deva` devtest has exactly the word, char and byte counts that the Arkios harness
  logged for the FLORES-200 tarball (18,701 / 127,914 / 340,483 with joining newlines).

The code and math sets below are optional. They are not committed: build them with
`uv run python scripts/eval_panel.py fetch --code-math` and measure them with `run --code-math`.
`MANIFEST.tsv` keeps their checksums.

## HumanEval (`code/humaneval.jsonl`): optional, not committed

- **Source:** [`openai/openai_humaneval`](https://huggingface.co/datasets/openai/openai_humaneval), test split (164 tasks).
- **License:** MIT, © 2021 OpenAI.
- **Attribution:** Chen et al., "Evaluating Large Language Models Trained on Code", arXiv:2107.03374 (2021).
- **Content:** `prompt + canonical_solution` per task.

## MBPP (`code/mbpp.jsonl`): optional, not committed

- **Source:** [`google-research-datasets/mbpp`](https://huggingface.co/datasets/google-research-datasets/mbpp), `full` test split (500 tasks).
- **License:** CC BY 4.0.
- **Attribution:** Austin et al., "Program Synthesis with Large Language Models", arXiv:2108.07732 (2021).
- **Changes:** the task text is prefixed as a Python comment (`# ...`), followed by the reference code
  (its original CRLF line endings are kept).

## GSM8K (`math/gsm8k.jsonl`): optional, not committed

- **Source:** [`openai/gsm8k`](https://huggingface.co/datasets/openai/gsm8k), `main` test split (1,319 problems).
- **License:** MIT, © 2021 OpenAI.
- **Attribution:** Cobbe et al., "Training Verifiers to Solve Math Word Problems", arXiv:2110.14168 (2021).
- **Content:** `question + "\n" + answer`.

## MATH with LaTeX (`math/math_latex.jsonl`): optional, not committed

- **Source:** [`EleutherAI/hendrycks_math`](https://huggingface.co/datasets/EleutherAI/hendrycks_math), test split.
  It is a sample of 100 problems from each of the 7 subjects (700 total), drawn with seed `yak-math-<subject>`.
- **License:** MIT.
- **Attribution:** Hendrycks et al., "Measuring Mathematical Problem Solving With the MATH Dataset",
  NeurIPS Datasets and Benchmarks (2021), arXiv:2103.03874.
- **Content:** `problem + "\n" + solution`.

## Romanized Nepali words (`npi_latn/roman_words.txt`, `npi_latn/roman_words_deva.txt`)

- **Source:** [`Saugatkafley/Nepali-Roman-Transliteration`](https://huggingface.co/datasets/Saugatkafley/Nepali-Roman-Transliteration),
  validation split (2,804 word pairs).
- **License:** MIT (as declared on the dataset card).
- **Content:** two line-aligned word lists: the Romanized spelling and its Devanagari original. The
  set is word-level. No permissively licensed sentence-level Romanized Nepali set was found.

## Everyday Nepali (`npi_everyday/aya_npi.jsonl`)

- **Source:** [`CohereLabs/aya_dataset`](https://huggingface.co/datasets/CohereLabs/aya_dataset),
  train split, `language == "Nepali"` (4,002 rows). This is a seeded shuffle (`yak-aya-npi`), capped
  at 2 MB (1,941 rows).
- **License:** Apache-2.0.
- **Attribution:** Singh et al., "Aya Dataset: An Open-Access Collection for Multilingual Instruction
  Tuning", arXiv:2402.06619 (2024).
- **Content:** `inputs + "\n" + targets`: prompts and answers written by native speakers. The
  register is everyday, instructional and conversational, not social media.
- **Why not social media:** the social Nepali sets found on the Hub (`Shushant/NepaliSentiment`,
  `raygx/NepaliTweets`, `Titung/nepali-sentiment`, `Safal08/nepali-tourism-comments*`) declare no
  license, so they cannot be redistributed. `IRIIS-RESEARCH/Sentiment-Analysis-Nepali` is MIT, but
  it is mostly news headlines and machine-translated reviews.
