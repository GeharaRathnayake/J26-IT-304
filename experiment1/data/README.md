# Data

Dataset: **JavaQuestionSynthFinal**

- Source: https://huggingface.co/datasets/nitinnovtech-ai-space/JavaQuestionSynthFinal
- Mirror: `Pragades/JavaQuestionSynthFinal` (resolves to the same commit and the same parquet file, sha256 `2c9c5b4a...de6f2`)
- Licence: none stated (the repo has a metadata-only README with no licence field), appears
  synthetic. It is therefore not redistributed: `data/raw/` and `data/processed/` are gitignored.
- Revision: `e29cfdd4ec4179f54b2ea0409329207104de8bed` (resolved 2026-10-13, last modified upstream 2024-11-11)
- Format: one parquet file, `data/train-00000-of-00001.parquet`, 1,078 rows
- Fetch command: `conda run -n exp1-confusion python scripts/fetch_data.py`
  (downloads to `data/raw/JavaQuestionSynthFinal/`)
