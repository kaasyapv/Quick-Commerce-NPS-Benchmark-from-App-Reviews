"""Monthly NPS per app from the raw reviews, plus the 3 star as passive robustness version.

Writes outputs/nps_monthly.csv, outputs/nps_monthly_3star_passive.csv and outputs/nps_trend.png.
"""
from pathlib import Path

import duckdb
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
COLORS = {"blinkit": "#2e7d32", "zepto": "#6a1b9a", "instamart": "#ef6c00"}


def nps(detractor_max: int = 3):
    """Run sql/nps.sql. detractor_max=3 is the main definition, 2 makes 3 stars passive."""
    sql = (ROOT / "sql" / "nps.sql").read_text()
    params = {"raw": str(ROOT / "data" / "raw" / "*.parquet"), "detractor_max": detractor_max}
    return duckdb.execute(sql, params).df()


def chart(df, path):
    """NPS line per app with a shaded 95% band."""
    fig = go.Figure()
    for app, g in df.groupby("app"):
        color = COLORS[app]
        band = g["month"].tolist() + g["month"].tolist()[::-1]
        fig.add_scatter(x=band, y=(g["nps"] + g["moe"]).tolist() + (g["nps"] - g["moe"]).tolist()[::-1],
                        fill="toself", fillcolor=color, opacity=0.18, line_width=0,
                        hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=g["month"], y=g["nps"], name=app.capitalize(), line=dict(color=color, width=3))
    fig.update_layout(template="simple_white", width=1100, height=550, font_size=16,
                      title="Monthly NPS proxy from Google Play reviews (95% margin of error shaded)",
                      yaxis_title="NPS (points)", legend=dict(orientation="h", y=-0.12))
    fig.write_image(path, scale=2)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main, robust = nps(3), nps(2)
    main.to_csv(OUT / "nps_monthly.csv", index=False)
    robust.to_csv(OUT / "nps_monthly_3star_passive.csv", index=False)
    chart(main, OUT / "nps_trend.png")

    print(main.pivot(index="month", columns="app", values="nps").to_string())
    print("\nmargin of error, points (min / median / max):")
    print(main.groupby("app")["moe"].describe()[["min", "50%", "max"]].round(2).to_string())
    # instamart's first month starts on 9 Jan 2025, so it is a partial month
    small = main[main["n"] < 1000]
    print("\nmonths under 1,000 reviews:", small[["app", "month", "n"]].to_dict("records") or "none")
