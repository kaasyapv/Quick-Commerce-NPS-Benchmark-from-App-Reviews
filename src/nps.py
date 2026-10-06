"""NPS per app by month and by quarter from the raw reviews, plus the 3 star as passive version.

Writes outputs/nps_{monthly,quarterly}[_3star_passive].csv and outputs/nps_trend.png.
"""
from pathlib import Path

import duckdb
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
COLORS = {"blinkit": "#e8a600", "zepto": "#7b1fb8", "instamart": "#0b5fff"}  # the brands' own colours


def nps(grain: str = "month", detractor_max: int = 3):
    """Run sql/nps.sql. detractor_max=3 is the main definition, 2 makes 3 stars passive."""
    sql = (ROOT / "sql" / "nps.sql").read_text()
    params = {"raw": str(ROOT / "data" / "raw" / "*.parquet"), "grain": grain, "detractor_max": detractor_max}
    return duckdb.execute(sql, params).df()


def figure(df):
    """NPS line per app with a shaded 95% band."""
    fig = go.Figure()
    for app, g in df.groupby("app"):
        color = COLORS[app]
        band = g["period"].tolist() + g["period"].tolist()[::-1]
        fig.add_scatter(x=band, y=(g["nps"] + g["moe"]).tolist() + (g["nps"] - g["moe"]).tolist()[::-1],
                        fill="toself", fillcolor=color, opacity=0.18, line_width=0,
                        hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=g["period"], y=g["nps"], name=app.capitalize(), line=dict(color=color, width=3))
    fig.update_layout(template="simple_white", width=1100, height=550, font_size=16,
                      title="Monthly NPS proxy from Google Play reviews (95% margin of error shaded)",
                      yaxis_title="NPS (points)", legend=dict(orientation="h", y=-0.12))
    return fig


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for grain in ("month", "quarter"):
        for detractor_max, suffix in ((3, ""), (2, "_3star_passive")):
            nps(grain, detractor_max).to_csv(OUT / f"nps_{grain}ly{suffix}.csv", index=False)
    monthly = nps("month")
    figure(monthly).write_image(OUT / "nps_trend.png", scale=2)

    print(monthly.pivot(index="period", columns="app", values="nps").to_string())
    print("\nmargin of error, points (min / median / max):")
    print(monthly.groupby("app")["moe"].describe()[["min", "50%", "max"]].round(2).to_string())
    # instamart's first month starts on 9 Jan 2025, so it is a partial month
    small = monthly[monthly["n"] < 1000]
    print("\nmonths under 1,000 reviews:", small[["app", "period", "n"]].to_dict("records") or "none")
