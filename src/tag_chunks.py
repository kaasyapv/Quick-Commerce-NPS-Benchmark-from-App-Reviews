"""Hand the sample to taggers in chunks, then merge their labels into the cache.

    python src/tag_chunks.py export             # chunk files for every untagged review
    python src/tag_chunks.py export --limit 200 # only the first 200 (the pilot)
    python src/tag_chunks.py merge              # read data/processed/labels/*.txt into tags.parquet
    python src/tag_chunks.py status             # tagged count per app per quarter

A tagger reads data/processed/chunks/cNNN.txt (lines "position|review text") and writes
data/processed/labels/cNNN.txt (lines "position|driver"). Positions come from the fixed
order below, so reruns and resumes line up. The order goes rank by rank across every
app and quarter, so stopping early leaves each cell about equally filled.
"""
import argparse
from pathlib import Path

import pandas as pd

from drivers import DRIVERS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
CHUNK = 500


def ordered() -> pd.DataFrame:
    """The sample in tagging order, indexed by position."""
    s = pd.read_parquet(DATA / "sample.parquet")
    s["rank"] = s.groupby(["app", "quarter"]).cumcount()
    return s.sort_values(["rank", "app", "quarter"], kind="stable").reset_index(drop=True)


def tagged() -> pd.DataFrame:
    path = DATA / "tags.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=["reviewId", "app", "quarter", "primary"])


def export(limit):
    s = ordered().head(limit)
    todo = s[~s["reviewId"].isin(tagged()["reviewId"])]
    out = DATA / "chunks"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.txt"):
        old.unlink()
    for k, part in todo.groupby(todo.index // CHUNK):
        lines = [f"{pos}|{' '.join(text.split())[:400]}" for pos, text in part["content"].items()]
        (out / f"c{k:03d}.txt").write_text("\n".join(lines) + "\n")
    print(f"{len(todo):,} untagged reviews in {todo.index.map(lambda p: p // CHUNK).nunique()} chunk files")


def merge():
    s = ordered()
    labels = {}
    for f in sorted((DATA / "labels").glob("*.txt")):
        for line in f.read_text().splitlines():
            pos, _, driver = line.partition("|")
            if pos.strip().isdigit() and int(pos) < len(s):
                # a label outside the list becomes "other"
                labels[int(pos)] = driver.strip() if driver.strip() in DRIVERS else "other"
    new = s.loc[list(labels), ["reviewId", "app", "quarter"]].assign(primary=pd.Series(labels))
    cache = pd.concat([tagged(), new]).drop_duplicates("reviewId", keep="first")
    cache.to_parquet(DATA / "tags.parquet", index=False)
    print(f"{len(cache):,} reviews tagged in total ({len(new):,} read from label files)")


def status():
    print(tagged().pivot_table(index="quarter", columns="app", values="reviewId", aggfunc="count", margins=True).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["export", "merge", "status"])
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    export(args.limit) if args.action == "export" else merge() if args.action == "merge" else status()
