"""Pull Google Play reviews (English, India) for the three apps, 1 Jan 2025 to 30 Sep 2026.

Usage:
    python src/pull_reviews.py                     # all apps, one newest-first stream each
    python src/pull_reviews.py blinkit --by-star   # one stream per star rating (reaches further back)
    python src/pull_reviews.py --max 2000          # quick test: stop each stream after ~2,000 rows, save nothing

Pages newest first until a page goes older than START, or until Google stops returning
pages, which means we hit its depth limit. Every 50,000 rows the rows and continuation token are checkpointed
to data/raw/_ckpt/, so a crashed run picks up where it stopped.
"""
import argparse, pickle, time
from datetime import datetime
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews

APPS = {"blinkit": "com.grofers.customerapp",
        "zepto": "com.zeptoconsumerapp",
        "instamart": "in.swiggy.android.instamart"}
START, END = datetime(2025, 1, 1), datetime(2026, 10, 1)
KEEP = ["reviewId", "score", "content", "at", "thumbsUpCount", "appVersion", "replyContent", "repliedAt"]  # no usernames/avatars
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
CKPT = RAW / "_ckpt"
BACKOFF = [0, 5, 20, 60]  # seconds


def fetch_page(app_id, score, token):
    """One page of 200 reviews."""
    # google sometimes returns an empty page or errors when throttling, so retry
    for wait in BACKOFF:
        time.sleep(wait)
        try:
            batch, new_token = reviews(app_id, lang="en", country="in", sort=Sort.NEWEST, count=200,
                                       filter_score_with=score, continuation_token=token)
        except Exception as e:
            print(f"  error: {e!r}")
            continue
        if batch:
            return batch, new_token
    return [], token


def pull_stream(name, score=None, max_rows=None):
    """Page one stream (all stars, or a single star) back to START. Returns its rows."""
    tag = f"{name}_{score or 'all'}"
    rows_f, token_f = CKPT / f"{tag}.parquet", CKPT / f"{tag}.token"
    rows, token = [], None
    if token_f.exists() and not max_rows:
        rows = pd.read_parquet(rows_f).to_dict("records")
        token = pickle.loads(token_f.read_bytes())
        print(f"  resuming {tag} from checkpoint at {len(rows):,} rows")
    last_ckpt, t0 = len(rows), time.time()

    while True:
        batch, token = fetch_page(APPS[name], score, token)
        if not batch:
            stop = "google stopped returning pages"
            break
        rows += [{k: r[k] for k in KEEP} for r in batch]
        if len(rows) - last_ckpt >= 50_000:
            CKPT.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_parquet(rows_f)
            token_f.write_bytes(pickle.dumps(token))
            last_ckpt = len(rows)
            print(f"  checkpoint {tag}: {len(rows):,} rows, back to {batch[-1]['at']:%Y-%m-%d}")
        if batch[-1]["at"] < START:
            stop = "reached 1 Jan 2025"
            break
        if max_rows and len(rows) >= max_rows:
            stop = f"--max {max_rows}"
            break
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    print(f"{tag:14} rows={len(df):>9,}  oldest={df['at'].min():%Y-%m-%d}  "
          f"{time.time() - t0:6.0f}s  stop: {stop}")
    if not max_rows:
        rows_f.unlink(missing_ok=True)
        token_f.unlink(missing_ok=True)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*", default=list(APPS))
    ap.add_argument("--by-star", action="store_true")
    ap.add_argument("--max", type=int)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    for name in args.apps:
        streams = [1, 2, 3, 4, 5] if args.by_star else [None]
        df = pd.concat([pull_stream(name, s, args.max) for s in streams])
        df = df[(df["at"] >= START) & (df["at"] < END)].drop_duplicates("reviewId")
        if not args.max:
            df.to_parquet(RAW / f"{name}.parquet")
        print(f"{name}: {len(df):,} reviews in window\n")

    # review counts per app per month, from whatever has been pulled so far
    files = sorted(RAW.glob("*.parquet"))
    if files:
        all_df = pd.concat(pd.read_parquet(f).assign(app=f.stem) for f in files)
        print(pd.crosstab(all_df["at"].dt.to_period("M"), all_df["app"], margins=True).to_string())


if __name__ == "__main__":
    main()
