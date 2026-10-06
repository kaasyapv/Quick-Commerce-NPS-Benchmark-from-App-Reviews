"""Split the NPS gap between the leading and trailing app in the latest quarter into points per driver.

NPS = 100 (P - D), and D is the sum of the detractor shares of every driver. So

    NPS_A - NPS_B = 100 (P_A - P_B) + sum over drivers of (lost_B,d - lost_A,d)

where lost is the points each app loses to a driver (see driver_mix.py). A positive bar
means the trailing app loses more points there, so that driver explains part of the gap.
The bars add up to the gap exactly, and the script asserts it.

Writes outputs/bridge.csv and outputs/waterfall.png.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from driver_mix import mix
from nps import OUT, nps
from sample import PER_CELL

ACCENT, GREY = "#1f4e79", "#9e9e9e"
NAMES = {"promoters": "more 5 star reviews", "too_short_to_tell": "too short to tell"}


def bridge(q: pd.DataFrame, m: pd.DataFrame):
    """Return the leader, the laggard, the quarter and the bridge terms in NPS points."""
    quarter = m["quarter"].max()
    cur = q[pd.to_datetime(q["period"]).dt.to_period("Q").astype(str) == quarter].set_index("app")
    cur = cur.assign(score=100 * (cur["n_promoters"] - cur["n_detractors"]) / cur["n"])
    a, b = cur["score"].idxmax(), cur["score"].idxmin()
    lost = m[m["quarter"] == quarter].pivot(index="driver", columns="app", values="points_lost")
    terms = lost[b] - lost[a]
    terms["promoters"] = 100 * (cur.loc[a, "n_promoters"] / cur.loc[a, "n"] - cur.loc[b, "n_promoters"] / cur.loc[b, "n"])
    assert abs(terms.sum() - (cur.loc[a, "score"] - cur.loc[b, "score"])) < 1e-9, "bars do not add up to the gap"
    return a, b, quarter, cur["score"], terms, sampling_moe(lost, a, b)


def sampling_moe(lost: pd.DataFrame, a: str, b: str) -> pd.Series:
    """95% margin of error of each driver bar from tagging only PER_CELL reviews per app and quarter.

    A driver's points lost = c x t, where t is its share in the sample and c scales the sample up
    to every taggable detractor. The standard error of t is sqrt(t (1 - t) / PER_CELL). The
    promoter and too short bars are counted over all reviews, so they carry no sampling error.
    """
    se = {}
    for app in (a, b):
        c = lost[app].drop("too_short_to_tell").sum()
        t = lost[app] / c
        se[app] = c * np.sqrt(t * (1 - t) / PER_CELL)
    moe = 1.96 * np.sqrt(se[a] ** 2 + se[b] ** 2)
    moe["too_short_to_tell"] = 0.0
    moe["promoters"] = 0.0
    return moe


def waterfall(a, b, quarter, score, terms):
    terms = terms.sort_values(ascending=False)
    names = [b.capitalize()] + [NAMES.get(t, t.replace("_", " ")) for t in terms.index] + [a.capitalize()]
    fig = go.Figure(go.Waterfall(
        x=names, y=[score[b]] + terms.tolist() + [0], measure=["absolute"] + ["relative"] * len(terms) + ["total"],
        text=[f"{score[b]:.1f}"] + [f"{v:+.1f}" for v in terms] + [f"{score[a]:.1f}"], textposition="outside",
        increasing=dict(marker_color=ACCENT), decreasing=dict(marker_color=GREY), totals=dict(marker_color="#333333"),
        connector=dict(line_color=GREY)))
    fig.update_layout(template="simple_white", width=1400, height=650, font_size=15, showlegend=False,
                      title=f"{a.capitalize()} NPS {score[a]:.1f} vs {b.capitalize()} {score[b]:.1f}, {quarter}: "
                            "NPS points by source", yaxis_title="NPS (points)", xaxis_tickangle=-30)
    fig.write_image(OUT / "waterfall.png", scale=2)


if __name__ == "__main__":
    a, b, quarter, score, terms, moe = bridge(nps("quarter"), mix())
    rows = [("start", b, score[b], 0.0)] + [("term", t, v, moe[t]) for t, v in terms.items()] + [("end", a, score[a], 0.0)]
    pd.DataFrame(rows, columns=["kind", "term", "points", "moe"]).round(3).to_csv(OUT / "bridge.csv", index=False)
    waterfall(a, b, quarter, score, terms)
    print(f"{quarter}: leader {a} {score[a]:.2f}, laggard {b} {score[b]:.2f}, gap {score[a] - score[b]:.2f} points")
    print(pd.DataFrame({"points": terms, "moe_95": moe}).sort_values("points", ascending=False).round(2).to_string())
    print(f"sum of bars {terms.sum():.2f}")
