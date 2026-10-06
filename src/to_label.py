"""Draw the 400 reviews you label by hand. The file has no model labels, so you label blind.

Writes data/processed/to_label.csv (reviewId, app, content, my_label) and refuses to
overwrite it, so labels you already entered are never lost.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "to_label.csv"
PER_APP = {"blinkit": 134, "instamart": 133, "zepto": 133}


if __name__ == "__main__":
    if OUT.exists():
        raise SystemExit(f"{OUT.name} already exists. Delete it first if you really want a new draw.")
    s = pd.read_parquet(ROOT / "data" / "processed" / "sample.parquet")
    # first 500 per app and quarter, because those get tagged first even if the run stops early
    pool = s[s.groupby(["app", "quarter"]).cumcount() < 500]
    picks = pd.concat(pool[pool["app"] == a].sample(n, random_state=42) for a, n in PER_APP.items())
    picks = picks.sample(frac=1, random_state=42)  # mix the apps
    out = picks[["reviewId", "app", "content"]].assign(my_label="")
    out.to_csv(OUT, index=False)
    print(f"{len(out)} reviews written to {OUT.relative_to(ROOT)}")
    print(picks.groupby("app").size().to_string())
    print(picks.groupby("quarter").size().to_string())
