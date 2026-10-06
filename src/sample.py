"""Draw the detractor sample to tag: 1,000 reviews per app per quarter, 4+ words only.

Writes data/processed/sample.parquet. Reviews under 4 words are left out here and
counted later as too_short_to_tell.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "sample.parquet"
PER_CELL = 1000


def detractors() -> pd.DataFrame:
    """All 1 to 3 star reviews with at least 4 words, with app and quarter columns."""
    df = pd.concat([pd.read_parquet(f).assign(app=f.stem) for f in sorted(RAW.glob("*.parquet"))],
                   ignore_index=True)
    df = df[df["score"] <= 3]
    df = df[df["content"].fillna("").str.split().str.len() >= 4]
    df["quarter"] = df["at"].dt.to_period("Q").astype(str)
    return df[["reviewId", "app", "quarter", "score", "content", "at"]]


if __name__ == "__main__":
    df = detractors()
    # shuffle once, then take the first 1,000 per cell, so the sample never depends on file order
    sample = df.sample(frac=1, random_state=42).groupby(["app", "quarter"]).head(PER_CELL)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_parquet(OUT, index=False)
    print(sample.pivot_table(index="quarter", columns="app", values="reviewId", aggfunc="count").to_string())
    print(f"\n{len(sample):,} reviews sampled from {len(df):,} eligible detractors")
