"""Keyword baseline against the model's tags on the sampled detractors.

The model's tags are the reference here, so this measures how far a plain keyword list gets
toward them, not how right either is. Writes outputs/keyword_vs_tags.csv.
"""
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support

from drivers import DRIVERS
from keywords import guess

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

if __name__ == "__main__":
    df = pd.read_parquet(DATA / "sample.parquet").merge(pd.read_parquet(DATA / "tags.parquet")[["reviewId", "primary"]])
    df["keyword"] = df["content"].map(guess)
    labels = list(DRIVERS)
    p, r, _, support = precision_recall_fscore_support(df["primary"], df["keyword"], labels=labels, zero_division=0)
    out = pd.DataFrame({"driver": labels, "precision": p, "recall": r, "reviews": support})
    overall = {"driver": "overall", "reviews": len(df),
               "agreement_pct": 100 * (df["primary"] == df["keyword"]).mean(),
               "kappa": cohen_kappa_score(df["primary"], df["keyword"])}
    out = pd.concat([pd.DataFrame([overall]), out], ignore_index=True)
    out.round(3).to_csv(ROOT / "outputs" / "keyword_vs_tags.csv", index=False)
    print(out.round(3).to_string(index=False))
