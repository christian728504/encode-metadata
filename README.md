# encode-metadata

Pipelines for turning [ENCODE](https://www.encodeproject.org/) metadata reports into Parquet
tables and deriving BPNet / ChromBPNet model-annotation tables and download manifests. The work is
organized as [marimo](https://marimo.io/) notebooks driven by [Polars](https://pola.rs/).

## Overview

ENCODE exposes its catalog as tab-separated "report" exports (one per object type: `File`,
`Experiment`, `Annotation`, and ~110 others). This repo:

1. **Ingests** every report — downloads, cleans, and converts each to a column-normalized Parquet
   file (`notebooks/report_parquets.py`).
2. **Derives** per-experiment model annotations — joins the `File`, `Experiment`, and `Annotation`
   parquets, pivots model output files into one row per experiment, deduplicates to the oldest
   annotation, and emits TSV/Parquet tables plus aria2c download manifests for any model files not
   yet present on disk (`notebooks/annotation_manifests.py`).

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for environment and dependency management
- [`aria2c`](https://aria2.github.io/) — parallel downloader (report download + manifest fetch)
- [`qsv`](https://github.com/dathere/qsv) — CSV/TSV toolkit used to reformat reports

Python dependencies (`polars[all]`, `python-slugify`, `marimo`) are declared in `pyproject.toml`.

```sh
uv sync
```

## Usage

The two notebooks form a sequence — run the ingestion notebook first, since the annotation notebook
reads the Parquet files it produces.

```sh
# 1. Download ENCODE reports -> resources/reports, convert -> resources/parquets
uv run marimo edit notebooks/report_parquets.py

# 2. Build BPNet / ChromBPNet annotation tables + manifests -> output/
uv run marimo edit notebooks/annotation_manifests.py
```

Use `uv run marimo run <notebook>` for a read-only app, or `uv run <notebook>` to execute it as a
plain script.

### 1. Report ingestion — `report_parquets.py`

Reads the report URLs in `resources/encode-full-report-urls.txt` and, behind a run button:

- Downloads each report with `aria2c` into `resources/reports/`. ENCODE names downloads
  `{type}_report_{date}.tsv` via `Content-Disposition`.
- Cleans each file: strips the leading metadata line, reformats with `qsv fmt`, removes the date
  suffix from the name, deletes the raw download, and drops a `.<YYYY-MM-DD>` sentinel recording the
  download date.
- Converts each `{type}_report.tsv` to `resources/parquets/{type}_report.parquet` with Polars,
  normalizing column names to `snake_case` with `python-slugify`.

A summary table reports row/column counts and per-file status.

> [!NOTE]
> The download is gated behind a button because the full set is large (the `file_report` alone is
> several GB). `aria2c --continue` resumes partial downloads across runs.

### 2. Annotation tables — `annotation_manifests.py`

Consumes `resources/parquets/{file,experiment,annotation}_report.parquet` and produces, for both
the BPNet and ChromBPNet annotation types:

- `output/{BPNet,ChromBPNet}-model-annotations.tsv` and `.parquet` — one row per experiment with
  human-readable columns (accessions, biosample, assembly, and the local paths of each model output
  file).
- `output/{BPNet,ChromBPNet}-model-annotations.manifest` — an aria2c input file listing any model
  files not found on the local filesystem, so they can be fetched from ENCODE.

> [!IMPORTANT]
> The local model directories are hard-coded near the top of the notebook
> (`CHROMBPNET_DIR`, `BPNET_DIR`). Adjust them to match your environment before running.

## Project structure

```
notebooks/
  report_parquets.py        # ENCODE reports -> cleaned TSV + Parquet
  annotation_manifests.py   # Parquets -> BPNet/ChromBPNet tables + manifests
resources/                  # input URLs, downloaded reports, parquets (gitignored)
output/                     # derived annotation tables + manifests (gitignored)
pyproject.toml              # dependencies
```

> [!NOTE]
> `resources/` and `output/` hold generated data and are gitignored. Only the notebooks and project
> configuration are tracked.
