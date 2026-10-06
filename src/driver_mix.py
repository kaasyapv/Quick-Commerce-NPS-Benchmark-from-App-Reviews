"""Complaint driver mix per app and quarter, in share of tagged detractors and in NPS points lost.

Writes outputs/driver_mix_quarterly.csv, outputs/driver_mix_monthly.csv and two charts.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px

from drivers import DRIVERS
from nps import COLORS, nps
from sample import detractors

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
NAMED = [d for d in DRIVERS if d not in ("other", "no_complaint")]  # the 8 complaint drivers


def mix() -> pd.DataFrame:
    """One row per app, quarter and driver: share of tagged detractors and NPS points lost.

    Points lost to a driver = 100 x tagged share x (detractors with 4+ words) / all reviews.
    The sample is only 1,000 reviews per app and quarter, so its shares are scaled up to
    every detractor long enough to tag. Detractors under 4 words get their own row, so
    the rows of one app and quarter add up to exactly 100 x D.
    """
    q = nps("quarter")
    q["quarter"] = pd.to_datetime(q["period"]).dt.to_period("Q").astype(str)
    q = q.set_index(["app", "quarter"])
    taggable = detractors().groupby(["app", "quarter"]).size()
    tags = pd.read_parquet(DATA / "tags.parquet")
    counts = tags.pivot_table(index=["app", "quarter"], columns="primary", values="reviewId",
                              aggfunc="count", fill_value=0).reindex(columns=list(DRIVERS), fill_value=0)
    share = counts.div(counts.sum(axis=1), axis=0)
    lost = share.mul(100 * taggable / q["n"], axis=0)
    lost["too_short_to_tell"] = 100 * (q["n_detractors"] - taggable) / q["n"]
    assert ((lost.sum(axis=1) - 100 * q["n_detractors"] / q["n"]).abs() < 1e-9).all()
    return pd.concat([(100 * share).stack().rename("share_pct"), lost.stack().rename("points_lost")],
                     axis=1).rename_axis(["app", "quarter", "driver"]).reset_index()


def monthly() -> pd.DataFrame:
    """Tagged detractor counts per app, month and driver, for the dashboard's month filter."""
    tags = pd.read_parquet(DATA / "tags.parquet")
    at = pd.read_parquet(DATA / "sample.parquet", columns=["reviewId", "at"])
    df = tags.merge(at, on="reviewId")
    df["month"] = df["at"].dt.to_period("M").dt.to_timestamp().dt.date
    return df.groupby(["app", "month", "primary"]).size().rename("tagged").reset_index().rename(columns={"primary": "driver"})


def charts(m: pd.DataFrame):
    labels = {d: d.replace("_", " ") for d in DRIVERS}
    latest = m["quarter"].max()
    last = m[(m["quarter"] == latest) & m["share_pct"].notna()].assign(driver=lambda d: d["driver"].map(labels))
    order = last.groupby("driver")["share_pct"].mean().sort_values().index.tolist()
    fig = px.bar(last, x="share_pct", y="driver", color="app", barmode="group", color_discrete_map=COLORS,
                 category_orders={"driver": order}, template="simple_white", width=1100, height=650,
                 labels={"share_pct": f"share of tagged detractor reviews, {latest} (%)", "driver": ""})
    fig.update_layout(font_size=16, legend_title_text="", legend=dict(orientation="h", y=-0.15))
    fig.write_image(OUT / "driver_mix_latest.png", scale=2)

    allq = m[m["driver"].isin(NAMED)].assign(driver=lambda d: d["driver"].map(labels))
    fig = px.bar(allq, x="quarter", y="points_lost", color="driver", facet_col="app", template="simple_white",
                 width=1400, height=600, labels={"points_lost": "NPS points lost", "quarter": ""})
    fig.update_layout(font_size=14, legend_title_text="")
    fig.write_image(OUT / "driver_mix_quarterly.png", scale=2)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    m = mix()
    m.round(3).to_csv(OUT / "driver_mix_quarterly.csv", index=False)
    monthly().to_csv(OUT / "driver_mix_monthly.csv", index=False)
    charts(m)
    latest = m[m["quarter"] == m["quarter"].max()]
    print(latest.pivot(index="driver", columns="app", values="share_pct").round(1).to_string())
    print("\nNPS points lost per driver, latest quarter")
    print(latest.pivot(index="driver", columns="app", values="points_lost").round(2).to_string())
