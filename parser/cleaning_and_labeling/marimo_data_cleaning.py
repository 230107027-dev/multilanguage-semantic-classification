

import marimo

__generated_with = "0.13.2"
app = marimo.App(width="medium")


@app.cell
def _():
    return


@app.cell
def _():
    import sqlite3
    import polars as pl

    # reading database
    conn = sqlite3.connect("reviews.db")
    df = pl.read_database("SELECT * FROM reviews", conn)

    # convert string to list[str]
    df = df.with_columns(pl.col("topics").map_elements(lambda x: eval(x), return_dtype=pl.List(pl.String)).alias("topics"))

    # remove wrong data
    # I don't know way, but topics as "ignorance of kazakh" and "ignorance of russian" was very badly labeled using Gemini API. So, just delete it.
    df = df.with_columns(
        pl.col("topics").list.eval(
            pl.element().filter(pl.element() != "ignorance of kazakh")
        ).alias("topics")
    )
    df = df.with_columns(
        pl.col("topics").list.eval(
            pl.element().filter(pl.element() != "ignorance of russian")
        ).alias("topics")
    )
    df
    return df, pl, sqlite3


@app.cell
def _(df, pl):
    # add separator for array
    rev = df.with_columns(pl.col("array").list.join("|"))

    # convert firm_rubrics column from str to list[str]
    rev = rev.with_columns(pl.col("firm_rubrics").map_elements(lambda x: eval(x), return_dtype=pl.List(pl.String)).alias("array1"))

    rev = rev.with_columns(pl.col("array1").list.join("|"))
    # delete unnecessary column
    rev = rev.select(pl.exclude("text", "user_id", "user_name", "is_hidden", "firm_rubrics", "topics"))
    rev = rev.rename({"array": "topics", "array1": "firm_rubrics"})
    rev = rev.with_columns(pl.col("date_created").str.to_datetime(time_unit="us", time_zone="UTC"))
    rev = rev.rename({
        "clean_text": "text"
    })

    rev 
    return


@app.cell
def _():
    return


@app.cell
def _(pl, rev1):
    rev2 = rev1.with_columns(
        pl.when((pl.col("rating") > 3) & (pl.col("topics").is_null() | (pl.col("topics").str == "")))
        .then(pl.lit("overall good"))
        .otherwise(pl.col("topics"))
        .alias("topics")
    )

    rev2 = rev2.with_columns(
        pl.when((pl.col("rating") < 4) & (pl.col("topics").is_null() | (pl.col("topics").str == "")))
        .then(pl.lit("overall bad"))
        .otherwise(pl.col("topics"))
        .alias("topics")
    )

    rev2
    return


@app.cell
def _(pl, sqlite3):
    conn1 = sqlite3.connect("2gis_data.db")
    df_firms = pl.read_database("SELECT * FROM firms", conn1)

    df_firms = df_firms.with_columns(pl.col("rubrics").map_elements(lambda x: eval(x), return_dtype=pl.List(pl.String)).alias("array"))
    df_firms = df_firms.with_columns(pl.col("array").list.join("|"))
    df_firms = df_firms.select(pl.exclude("data", "rubrics"))
    df_firms = df_firms.rename({"array": "rubrics"})
    df_firms

    # rev1 = rev.with_columns(pl.col("array1").list.join("|"))
    # rev1 = rev1.select(pl.exclude("text", "user_id", "user_name", "is_hidden", "firm_rubrics", "topics"))
    # rev1 = rev1.rename({"array": "topics", "array1": "firm_rubrics"})
    # rev1 = rev1.with_columns(pl.col("date_created").str.to_datetime(time_unit="us", time_zone="UTC"))
    # rev1 = rev1.rename({
    #     "clean_text": "text"
    # })

    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    import marimo as mo
    return


if __name__ == "__main__":
    app.run()
