"""Hand the sample to taggers in chunks, then merge their labels into the cache.

    python src/tag_chunks.py export             # chunk files for every untagged review
    python src/tag_chunks.py export --limit 200 # only the first 200 (the pilot)
    python src/tag_chunks.py merge              # read data/processed/labels/*.txt into tags.parquet
    python src/tag_chunks.py status             # tagged count per app per quarter
    python src/tag_chunks.py check              # 100 untagged reviews for two independent taggers
    python src/tag_chunks.py agree              # how often the two taggers agree

A tagger reads data/processed/chunks/cNNN.txt (lines "position|review text") and writes
data/processed/labels/cNNN.txt (lines "position|driver"). Positions come from the fixed
order below, so reruns and resumes line up. The order goes rank by rank across every
app and quarter, so stopping early leaves each cell about equally filled.
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from drivers import DRIVERS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
CHUNK = 500
OUT = ROOT / "outputs"


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
    # the label files are the source of truth, so the cache is rebuilt from them every time
    cache = s.loc[list(labels), ["reviewId", "app", "quarter"]].assign(primary=pd.Series(labels))
    cache.to_parquet(DATA / "tags.parquet", index=False)
    print(f"{len(cache):,} reviews tagged in total")


def check():
    """Write 100 random untagged reviews to data/processed/check/check.txt."""
    s = ordered()
    pick = s[~s["reviewId"].isin(tagged()["reviewId"])].sample(100, random_state=42).sort_index()
    (DATA / "check").mkdir(exist_ok=True)
    lines = [f"{pos}|{' '.join(text.split())[:400]}" for pos, text in pick["content"].items()]
    (DATA / "check" / "check.txt").write_text("\n".join(lines) + "\n")


def agree():
    """Compare tagger a and b on the check reviews, and each against the main run."""
    s = ordered()
    read = lambda name: dict(line.split("|") for line in (DATA / "check" / name).read_text().split())
    a, b = read("a.txt"), read("b.txt")
    main = tagged().set_index("reviewId")["primary"]
    rows = []
    for name, x, y in [("a vs b", a, b), ("a vs main run", a, None), ("b vs main run", b, None)]:
        y = y or {p: main.get(s.loc[int(p), "reviewId"]) for p in x}
        pairs = [(x[p], y[p]) for p in x if p in y and y[p]]
        left, right = zip(*pairs)
        rows.append({"pair": name, "n": len(pairs), "agreement_pct": round(100 * sum(l == r for l, r in pairs) / len(pairs), 1),
                     "kappa": round(cohen_kappa_score(left, right), 3)})
    out = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / "tagger_consistency.csv", index=False)
    print(out.to_string(index=False))


def status():
    print(tagged().pivot_table(index="quarter", columns="app", values="reviewId", aggfunc="count", margins=True).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["export", "merge", "status", "check", "agree"])
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    if args.action == "export":
        export(args.limit)
    else:
        {"merge": merge, "status": status, "check": check, "agree": agree}[args.action]()
