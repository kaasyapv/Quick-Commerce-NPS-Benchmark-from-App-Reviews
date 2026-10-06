"""Pick two short example quotes per driver from the latest quarter, 20 in all.

This is the only review text that goes into the repo, so the draw skips anything that
looks like contact details or an address. Writes outputs/example_quotes.csv.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

if __name__ == "__main__":
    df = pd.read_parquet(DATA / "sample.parquet").merge(pd.read_parquet(DATA / "tags.parquet")[["reviewId", "primary"]])
    df["quote"] = df["content"].str.split().str.join(" ")
    df = df[(df["quarter"] == df["quarter"].max()) & df["quote"].str.len().between(40, 140)]
    # no phone numbers, emails, links or anything that reads like a street address
    df = df[~df["quote"].str.contains(r"\d{6,}|@|http|apartment|nagar|colony|sector|society|road|street", case=False, regex=True)]
    out = df.sample(frac=1, random_state=42).groupby("primary").head(2).sort_values("primary")
    out = out.rename(columns={"primary": "driver"})[["driver", "app", "quarter", "quote"]]
    out.to_csv(ROOT / "outputs" / "example_quotes.csv", index=False)
    print(out.to_string(index=False, max_colwidth=150))
