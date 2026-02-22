import requests
import json
import polars as pl
import pandas as pd
import numpy as np
import os

pl.Config.set_verbose(False)

def write_csv_compat(df: pl.DataFrame, **kwargs):
    df.with_columns(
        pl.selectors.list().map_elements(lambda x: str(x.to_list()), return_dtype=pl.Utf8), # type: ignore
        pl.selectors.array().map_elements(lambda x: str(x.to_list()), return_dtype=pl.Utf8), # type: ignore
        pl.selectors.struct().struct.json_encode(),
    ).write_csv(**kwargs)

def print_schema(schema, indent=0, file=None):
    """Pretty print a Polars schema with nested types in tree format."""
    for name, dtype in schema.items():
        prefix = " |" * indent + "-- " if indent else ""
        
        # Handle Struct
        if dtype.base_type() == pl.Struct:
            print(f"{prefix}{name}: Struct", file=file)
            nested = {f.name: f.dtype for f in dtype.fields}
            print_schema(nested, indent + 1, file=file)
        
        # Handle List containing Struct
        elif dtype.base_type() == pl.List and dtype.inner.base_type() == pl.Struct:
            print(f"{prefix}{name}: List[Struct]", file=file)
            nested = {f.name: f.dtype for f in dtype.inner.fields}
            print_schema(nested, indent + 1, file=file)
        
        # Handle Array containing Struct  
        elif dtype.base_type() == pl.Array and dtype.inner.base_type() == pl.Struct:
            print(f"{prefix}{name}: Array[Struct, {dtype.size}]", file=file)
            nested = {f.name: f.dtype for f in dtype.inner.fields}
            print_schema(nested, indent + 1, file=file)
        
        else:
            print(f"{prefix}{name}: {dtype}", file=file)

def write_schema_files(files):
    for file in files:
        schema_file = file + ".schema"
        if not os.path.exists(schema_file):
            schema_f = open(schema_file, "w")
            print_schema(pl.read_parquet(file).schema, file=schema_f)

def etl_files_table(path):
    df = pl.read_parquet(path)
    return (
        df
        .select(
            "ID",
            "Download URL",
            "Output type",
        )
        .rename({"Download URL": "File accession"})
        .with_columns(pl.col("File accession").str.split("/").list.last())
    )

def etl_experiments_table(path):
    df = pl.read_parquet(path)
    return (
        df
        .select(
            "ID",
            "Accession",
            "Status",
            "Description",
            "Biosample summary",
            "Biosample term name",
            "Biosample classification",
            "Assay name",
            "Perturbed"
        )
        .rename(
            {
                "Accession": "Experiment accession",
                "Status": "Experiment status",
            }
        )
    )

def etl_annotations_table(path):
    df = pl.read_parquet(path)
    return (
        df
        .select(
            "Accession",
            "Status",
            "Annotation type",
            "Genome assembly",
            pl.col("Experimental input").str.split(","),
            pl.concat_list(
                pl.col("Files").str.split(","),
                pl.col("Contributing files").str.split(","),
            ).alias("Files")
        )
        .rename(
            {
                "Accession": "Annotation accession",
                "Status": "Annotation status",
            }
        )
        .explode("Experimental input")
        .explode("Files")
    )

def etl_chrombpnet_model_table(df: pl.DataFrame):
    return (
        df
        .filter(pl.col("Annotation type") == "ChromBPNet-model")
        .pivot(
            "Output type",
            values="File accession",
            aggregate_function=pl.element().implode()
        )
    )

def etl_bpnet_model_table(df: pl.DataFrame):
    return (
        df
        .filter(pl.col("Annotation type") == "BPNet-model")
        .filter(pl.col("Output type").is_not_null())
        .pivot(
            "Output type",
            values="File accession",
            aggregate_function=pl.element().implode()
        )
    )

def write_download_manifest(df: pl.DataFrame, path: str, download_dest: str):
    url_fmt = "https://www.encodeproject.org{}"
    files = (
        df
        .select(
            pl.concat_list(pl.selectors.list()).explode().alias("hrefs")
        )
        ["hrefs"]
        .drop_nulls()
        .to_numpy()
    )
    with open(path, "w") as f:
        for file in files:
            file_accession = file.split(".")[0]
            href = f"/{file_accession}/@@download/{file}"
            url = url_fmt.format(href)
            f.write(url + "\n")
            f.write(f"\tdir={download_dest}" + "\n")
            f.write(f"\tout={file}" + "\n")

def main():
    write_schema_files(["resources/Files.parquet", "resources/Annotations.parquet", "resources/Experiments.parquet"])
    files_df = etl_files_table(os.path.join("resources", "Files.parquet"))
    experiments_df = etl_experiments_table(os.path.join("resources", "Experiments.parquet"))
    annotations_df = etl_annotations_table(os.path.join("resources", "Annotations.parquet"))

    join_df = annotations_df.join(experiments_df, how="left", left_on="Experimental input", right_on="ID").drop("Experimental input")
    join_df = join_df.join(files_df, how="left", left_on="Files", right_on="ID").drop("Files")
    
    chrombpnet_models_df = etl_chrombpnet_model_table(join_df).drop("null", strict=False)
    chrombpnet_models_df.write_parquet("output/ChromBPNet-model.parquet")
    write_csv_compat(chrombpnet_models_df, file="output/ChromBPNet-model.tsv", separator="\t")
    write_download_manifest(chrombpnet_models_df, path="output/ChromBPNet-model.manifest", download_dest="/data/zusers/ramirezc/all_chrombpnet_files")

    bpnet_models_df = etl_bpnet_model_table(join_df).drop("null", strict=False)
    bpnet_models_df.write_parquet("output/BPNet-model.parquet")
    write_csv_compat(bpnet_models_df, file="output/BPNet-model.tsv", separator="\t")
    write_download_manifest(bpnet_models_df, path="output/BPNet-model.manifest", download_dest="/data/zusers/ramirezc/all_bpnet_files")


if __name__ == "__main__":
    main()
