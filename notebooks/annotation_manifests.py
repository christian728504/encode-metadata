import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    import re
    from pathlib import Path

    import marimo as mo
    import polars as pl
    import functools
    from typing import Literal

    mo.ui.table = functools.partial(mo.ui.table, max_columns=None)
    _ = pl.Config.set_verbose(False)
    return Literal, Path, mo, os, pl, re


@app.cell
def _(re):
    def to_snake_case(text):
        # Split camelCase / PascalCase boundaries
        s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        # Replace non-alphanumeric characters with underscores
        s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
        # Lowercase and clean up trailing/duplicate underscores
        return s.strip("_").lower()

    return (to_snake_case,)


@app.cell
def _(Path, os):
    ROOT = Path(os.getcwd())
    RESOURCES = ROOT / "resources"
    OUTPUT = ROOT / "output"
    CHROMBPNET_DIR = "/data/zusers/ramirezc/all_chrombpnet_files"
    BPNET_DIR = "/data/zusers/ramirezc/all_bpnet_files"
    MANIFEST_ENTRY_FORMAT = "{url}\n\tdir={dir}\n\tout={out}\n"
    return BPNET_DIR, CHROMBPNET_DIR, MANIFEST_ENTRY_FORMAT, OUTPUT, RESOURCES


@app.cell
def _(BPNET_DIR, CHROMBPNET_DIR, Literal, pl):
    def file_path(
        list_col: str, model: Literal["CHROMBPNET", "BPNET"] = "CHROMBPNET"
    ):
        """List[str] of filenames -> comma-joined {CHROMBPNET_DIR}/{filename} paths."""
        if model == "CHROMBPNET":
            _dir = CHROMBPNET_DIR
        else:
            _dir = BPNET_DIR

        return (
            pl.col(list_col)
            .list.eval(pl.lit(_dir + "/") + pl.element())
            .list.join(",")
        )

    return (file_path,)


@app.cell
def _(pl):
    def live(df):
        """Drop rows retracted by ENCODE (deleted/revoked status)."""
        return df.filter(
            pl.col("status").is_in(["deleted", "revoked"]).not_().fill_null(False)
        )

    return (live,)


@app.cell
def _(live, pl, to_snake_case):
    def etl_files_table(path):
        df = live(pl.read_parquet(path).rename(to_snake_case))
        return (
            df.select(
                "id",
                "download_url",
                "output_type",
            )
            .rename({"download_url": "file_accession"})
            .with_columns(pl.col("file_accession").str.split("/").list.last())
        )

    return (etl_files_table,)


@app.cell
def _(live, pl, to_snake_case):
    def etl_experiments_table(path):
        df = live(pl.read_parquet(path).rename(to_snake_case))
        return df.select(
            "id",
            "accession",
            "status",
            "perturbed",
            "assay_name",
            "organism",
            "genome_assembly",
            "biosample_classification",
            "biosample_term_name",
            "biosample_ontology",
            "simple_biosample_summary",
            "description",
        ).rename(
            {
                "accession": "experiment_accession",
                "status": "experiment_status",
            }
        )

    return (etl_experiments_table,)


@app.cell
def _(live, pl, to_snake_case):
    def etl_annotations_table(path):
        df = live(pl.read_parquet(path).rename(to_snake_case))
        return (
            df.select(
                "accession",
                "status",
                "annotation_type",
                "genome_assembly",
                "date_created",
                pl.col("experimental_input").str.split(","),
                pl.concat_list(
                    pl.col("files").str.split(","),
                    pl.col("contributing_files").str.split(","),
                ).alias("files"),
            )
            .rename(
                {
                    "accession": "annotation_accession",
                    "status": "annotation_status",
                }
            )
            .explode("experimental_input")
            .explode("files")
        )

    return (etl_annotations_table,)


@app.cell
def _(pl):
    def dedup_oldest(df):
        return (
            df.filter(pl.col("experiment_accession").is_not_null())
            .with_columns(
                pl.col("date_created")
                .str.slice(0, 10)
                .str.to_date("%Y-%m-%d", strict=False)
                .alias("annotation_date")
            )
            .sort(
                ["annotation_date", "annotation_accession"],
                descending=[False, True],
                nulls_last=True,
            )
            .unique(
                subset="experiment_accession", keep="first", maintain_order=True
            )
        )

    return (dedup_oldest,)


@app.cell
def _(
    RESOURCES,
    etl_annotations_table,
    etl_experiments_table,
    etl_files_table,
    mo,
):
    # files_df = etl_files_table(RESOURCES / "Files.parquet")
    # experiments_df = etl_experiments_table(RESOURCES / "Experiments.parquet")
    # annotations_df = etl_annotations_table(RESOURCES / "Annotations.parquet")

    files_df = etl_files_table(RESOURCES / "parquets" / "file_report.parquet")
    experiments_df = etl_experiments_table(
        RESOURCES / "parquets" / "experiment_report.parquet"
    )
    annotations_df = etl_annotations_table(
        RESOURCES / "parquets" / "annotation_report.parquet"
    )

    mo.vstack(
        [
            mo.ui.table(files_df),
            mo.ui.table(experiments_df),
            mo.ui.table(annotations_df),
        ]
    )
    return annotations_df, experiments_df, files_df


@app.cell
def _(annotations_df, experiments_df, files_df):
    join_df = (
        annotations_df.join(
            experiments_df, how="left", left_on="experimental_input", right_on="id"
        )
        .drop("experimental_input")
        .join(files_df, how="left", left_on="files", right_on="id")
        .drop("files")
    )
    return (join_df,)


@app.cell
def _(join_df, pl, to_snake_case):
    chrombpnet_pivot = (
        join_df.filter(
            pl.col("annotation_type") == "ChromBPNet-model",
            (
                pl.col("output_type").eq("predicted signal profile")
                & pl.col("file_accession").str.ends_with(".bigWig")
            ).not_(),
        )
        .pivot(
            "output_type",
            values="file_accession",
            aggregate_function=pl.element().implode(),
        )
        .rename(to_snake_case)
        .drop("null", strict=False)
    )

    chrombpnet_pivot
    return (chrombpnet_pivot,)


@app.cell
def _(chrombpnet_pivot, dedup_oldest):
    chrombpnet_deduped = dedup_oldest(chrombpnet_pivot)
    return (chrombpnet_deduped,)


@app.cell
def _(chrombpnet_deduped, file_path, pl):
    chrombpnet_derived = chrombpnet_deduped.with_columns(
        pl.col("biosample_ontology")
        .str.extract(r"([A-Za-z]+_\d+)/?$", 1)
        .str.replace("_", ":")
        .alias("biosample_term_id"),
        file_path("models"),
        file_path("observed_signal_profile"),
        file_path("predicted_signal_profile"),
        file_path("training_and_test_regions"),
        pl.col("alignments")
        .list.eval(pl.element().str.split(".").list.first())
        .list.join(","),
        pl.col("unfiltered_alignments")
        .list.eval(pl.element().str.split(".").list.first())
        .list.join(","),
    )
    return (chrombpnet_derived,)


@app.cell
def _(MANIFEST_ENTRY_FORMAT, OUTPUT, Path, chrombpnet_derived, os):
    _df = chrombpnet_derived

    with (OUTPUT / "ChromBPNet-model-annotations.manifest").open("w") as _f:
        for _path in (
            _df["models"].to_list()
            + _df["observed_signal_profile"].to_list()
            + _df["predicted_signal_profile"].to_list()
            + _df["training_and_test_regions"].to_list()
        ):
            _path = Path(_path)
            if not _path.exists():
                print(f"{_path} does not exist")
                _dir = _path.parent
                _base = _path.name
                _acc = _path.name.split(os.extsep)[0]
                _url = f"https://encodeproject.org/{_acc}/@@download/{_base}"
                _f.write(
                    MANIFEST_ENTRY_FORMAT.format(url=_url, dir=_dir, out=_base)
                )
    return


@app.cell
def _(OUTPUT, chrombpnet_derived, mo, pl):
    chrombpnet_df = chrombpnet_derived.select(
        pl.col("annotation_accession").alias("Annotation accession"),
        pl.col("annotation_status").alias("Annotation status"),
        pl.col("experiment_accession").alias("Experiment accession"),
        pl.col("experiment_status").alias("Experiment status"),
        pl.col("perturbed").alias("Experiment peturbed"),
        pl.col("simple_biosample_summary").alias("Biosample simple summary"),
        pl.col("description").alias("Experiment description"),
        pl.col("biosample_term_id").alias("Biosample term id"),
        pl.col("biosample_classification").alias("Biosample classification"),
        pl.col("genome_assembly").alias("Assembly"),
        pl.col("organism").alias("Organism"),
        pl.col("assay_name").alias("Assay term name"),
        pl.col("models").alias("Annotation models file"),
        pl.col("observed_signal_profile").alias(
            "Annotation observed signal profile"
        ),
        pl.col("predicted_signal_profile").alias(
            "Annotation predicted signal profile"
        ),
        pl.col("training_and_test_regions").alias(
            "Annotation test and training regions"
        ),
        pl.col("alignments").alias("Annotation alignments file accessions"),
        pl.col("unfiltered_alignments").alias(
            "Annotation unfiltered alignments file accessions"
        ),
    ).sort("Annotation accession")

    chrombpnet_df.write_parquet(OUTPUT / "ChromBPNet-model-annotations.parquet")
    chrombpnet_df.write_csv(
        OUTPUT / "ChromBPNet-model-annotations.tsv", separator="\t"
    )

    mo.ui.table(chrombpnet_df, page_size=25)
    return


@app.cell
def _():
    return


@app.cell
def _(join_df, pl, to_snake_case):
    bpnet_pivot = (
        join_df.filter(
            pl.col("annotation_type") == "BPNet-model",
            (
                pl.col("output_type").eq("predicted signal profile")
                & pl.col("file_accession").str.ends_with(".bigWig")
            ).not_(),
        )
        .pivot(
            "output_type",
            values="file_accession",
            aggregate_function=pl.element().implode(),
        )
        .rename(to_snake_case)
        .drop("null", strict=False)
    )

    bpnet_pivot
    return (bpnet_pivot,)


@app.cell
def _(bpnet_pivot, dedup_oldest):
    bpnet_deduped = dedup_oldest(bpnet_pivot)
    return (bpnet_deduped,)


@app.cell
def _(bpnet_deduped, file_path, pl):
    bpnet_derived = bpnet_deduped.with_columns(
        pl.col("biosample_ontology")
        .str.extract(r"([A-Za-z]+_\d+)/?$", 1)
        .str.replace("_", ":")
        .alias("biosample_term_id"),
        file_path("observed_signal_profile_plus_strand", model="BPNET"),
        file_path("observed_signal_profile_minus_strand", model="BPNET"),
        file_path("models", model="BPNET"),
        file_path("training_and_test_regions", model="BPNET"),
        file_path("observed_control_profile_plus_strand", model="BPNET"),
        file_path("observed_control_profile_minus_strand", model="BPNET"),
        pl.col("alignments")
        .list.eval(pl.element().str.split(".").list.first())
        .list.join(","),
        pl.col("unfiltered_alignments")
        .list.eval(pl.element().str.split(".").list.first())
        .list.join(","),
    )
    return (bpnet_derived,)


@app.cell
def _(MANIFEST_ENTRY_FORMAT, OUTPUT, Path, bpnet_derived, os):
    _df = bpnet_derived

    with (OUTPUT / "BPNet-model-annotations.manifest").open("w") as _f:
        for _path in (
            _df["models"].to_list()
            + _df["observed_control_profile_plus_strand"].to_list()
            + _df["observed_control_profile_minus_strand"].to_list()
            + _df["observed_control_profile_plus_strand"].to_list()
            + _df["observed_control_profile_minus_strand"].to_list()
            + _df["training_and_test_regions"].to_list()
        ):
            _path = Path(_path)
            if not _path.exists():
                print(f"{_path} does not exist")
                _dir = _path.parent
                _base = _path.name
                _acc = _path.name.split(os.extsep)[0]
                _url = f"https://encodeproject.org/{_acc}/@@download/{_base}"
                _f.write(
                    MANIFEST_ENTRY_FORMAT.format(url=_url, dir=_dir, out=_base)
                )
    return


@app.cell
def _(OUTPUT, bpnet_derived, mo, pl):
    bpnet_df = bpnet_derived.select(
        pl.col("annotation_accession").alias("Annotation accession"),
        pl.col("annotation_status").alias("Annotation status"),
        pl.col("experiment_accession").alias("Experiment accession"),
        pl.col("experiment_status").alias("Experiment status"),
        pl.col("perturbed").alias("Experiment peturbed"),
        pl.col("simple_biosample_summary").alias("Biosample simple summary"),
        pl.col("description").alias("Experiment description"),
        pl.col("biosample_term_id").alias("Biosample term id"),
        pl.col("biosample_classification").alias("Biosample classification"),
        pl.col("genome_assembly").alias("Assembly"),
        pl.col("organism").alias("Organism"),
        pl.col("assay_name").alias("Assay term name"),
        pl.col("models").alias("Annotation models file"),
        pl.col("observed_signal_profile_plus_strand").alias(
            "Annotation observed signal profile file (plus strand)"
        ),
        pl.col("observed_signal_profile_minus_strand").alias(
            "Annotation observed signal profile file (minus strand)"
        ),
        pl.col("observed_control_profile_plus_strand").alias(
            "Annotation observed control profile file (plus strand)"
        ),
        pl.col("observed_control_profile_minus_strand").alias(
            "Annotation observed control profile file (minus strand)"
        ),
        pl.col("training_and_test_regions").alias(
            "Annotation training and test regions file"
        ),
        pl.col("alignments").alias("Annotation alignments file accessions"),
        pl.col("unfiltered_alignments").alias(
            "Annotation unfiltered alignments file accessions"
        ),
    ).sort("Annotation accession")

    bpnet_df.write_parquet(OUTPUT / "BPNet-model-annotations.parquet")
    bpnet_df.write_csv(OUTPUT / "BPNet-model-annotations.tsv", separator="\t")

    mo.ui.table(bpnet_df, page_size=25)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
