import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")


@app.cell
def _():
    import functools
    import os
    import re
    import subprocess
    from datetime import date
    from pathlib import Path

    import marimo as mo
    import polars as pl
    from slugify import slugify

    mo.ui.table = functools.partial(mo.ui.table, max_columns=None)
    return Path, date, mo, os, pl, re, slugify, subprocess


@app.cell
def _(Path, os):
    ROOT = Path(os.getcwd())
    RESOURCES = ROOT / "resources"
    URLS = RESOURCES / "encode-full-report-urls.txt"
    REPORTS = RESOURCES / "reports"
    PARQUETS = RESOURCES / "parquets"
    REPORTS.mkdir(parents=True, exist_ok=True)
    PARQUETS.mkdir(parents=True, exist_ok=True)
    return PARQUETS, REPORTS, URLS


@app.cell
def _(mo):
    download_button = mo.ui.run_button(label="Download + clean reports")
    download_button
    return (download_button,)


@app.cell
def _(REPORTS, URLS, download_button, mo, subprocess):
    mo.stop(
        not download_button.value, mo.md("Click the button to download reports.")
    )

    # ENCODE serves each report.tsv with a Content-Disposition name of
    # {type_snake}_report_{date}.tsv, so aria2c writes date-stamped files here.
    aria2c = subprocess.run(
        [
            "aria2c",
            f"--save-session={REPORTS / 'aria2.session'}",
            f"--input-file={URLS}",
            "--continue=true",
            "--optimize-concurrent-downloads=true",
            "--max-concurrent-downloads=2",
            "-k",
            "1M",
            f"--dir={REPORTS}",
        ],
        capture_output=True,
        text=True,
    )
    print(aria2c.stdout)
    print(aria2c.stderr)
    aria2c.check_returncode()
    return


@app.cell
def _(REPORTS, date, re, subprocess):
    def clean_report(raw):
        """Strip date suffix + first line, reformat with qsv into {stem}.tsv; remove raw."""
        stem = re.sub(
            r"_\d{4}_\d{1,2}_\d{1,2}_\d{1,2}h_\d{1,2}m(?=\.tsv$)", "", raw.name
        )
        clean = raw.with_name(stem)
        with clean.open("w") as out:
            tail = subprocess.Popen(
                ["tail", "-n", "+2", str(raw)], stdout=subprocess.PIPE
            )
            qsv = subprocess.run(
                ["qsv", "fmt", "--delimiter", "\t", "--out-delimiter", "\t"],
                stdin=tail.stdout,
                stdout=out,
            )
            tail.stdout.close()
            tail.wait()
        if tail.returncode or qsv.returncode:
            raise RuntimeError(f"clean failed for {raw.name}")
        raw.unlink()
        return clean


    cleaned = [clean_report(raw) for raw in sorted(REPORTS.glob("*_report_*.tsv"))]
    (REPORTS / f".{date.today().isoformat()}").touch()

    for _c in cleaned:
        print(_c.name)
    return (cleaned,)


@app.cell
def _(PARQUETS, REPORTS, cleaned, pl, slugify):
    _ = cleaned  # rerun after a fresh clean

    summary = []
    for _path in sorted(REPORTS.glob("*_report.tsv")):
        try:
            _df = pl.read_csv(
                _path, separator="\t", infer_schema_length=2**21
            ).rename(lambda c: slugify(c, separator="_"))
        except pl.exceptions.DuplicateError:
            summary.append(
                {
                    "report": _path.stem,
                    "rows": None,
                    "columns": None,
                    "status": "failed",
                }
            )
            continue
        _df.write_parquet(PARQUETS / f"{_path.stem}.parquet")
        summary.append(
            {
                "report": _path.stem,
                "rows": _df.height,
                "columns": _df.width,
                "status": "success",
            }
        )
    return (summary,)


@app.cell
def _(mo, pl, summary):
    mo.ui.table(pl.DataFrame(summary), page_size=25)
    return


if __name__ == "__main__":
    app.run()
