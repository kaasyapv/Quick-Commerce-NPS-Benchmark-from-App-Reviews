"""Charts for the deck slides, drawn from the saved CSVs in outputs/. Writes outputs/deck_*.png."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from driver_mix import NAMED
from nps import COLORS, OUT, figure

NAVY, PALE, GREY = "#1f4e79", "#a9c1d9", "#b9c0c8"
read = lambda name: pd.read_csv(OUT / f"{name}.csv")
label = lambda d: d.replace("_", " ")


def save(fig, name, w, h, size=15, **layout):
    layout.setdefault("margin", dict(l=70, r=30, t=50, b=60))
    fig.update_layout(template="simple_white", width=w, height=h, font=dict(family="Arial", size=size), **layout)
    fig.write_image(OUT / f"deck_{name}.png", scale=2)


def trend():
    save(figure(read("nps_monthly")), "trend", 800, 460, size=14, title=None, margin=dict(l=60, r=20, t=20, b=60))


def latest():
    """Latest quarter NPS per app with 95% error bars, under both definitions of a detractor."""
    main, alt = read("nps_quarterly"), read("nps_quarterly_3star_passive")
    m = main[main["period"] == main["period"].max()].set_index("app").sort_values("nps", ascending=False)
    a = alt[alt["period"] == alt["period"].max()].set_index("app").loc[m.index]
    bars = [go.Bar(name=name, x=[i.capitalize() for i in d.index], y=d["nps"], marker_color=color, text=[f"{v:.1f}" for v in d["nps"]],
                   textposition="inside", insidetextanchor="start", textfont=dict(color=font, size=15),
                   error_y=dict(type="data", array=d["moe"], color="#444444"))
            for name, d, color, font in (("3 stars count as detractor", m, NAVY, "white"), ("3 stars count as passive", a, PALE, "#222222"))]
    save(go.Figure(bars), "latest", 640, 380, yaxis_title="NPS (points)", barmode="group",
         legend=dict(orientation="h", y=-0.18), margin=dict(l=70, r=20, t=20, b=70))


def gap():
    """Gap between the best and worst app in every quarter."""
    g = read("robustness").set_index("period")["top_minus_bottom_main"]
    names = [f"Q{(t.month - 1) // 3 + 1} {t:%y}" for t in pd.to_datetime(g.index)]
    fig = go.Figure(go.Bar(x=names, y=g.values, text=g.round(1), textposition="outside",
                           marker_color=[GREY] * (len(g) - 1) + [NAVY]))
    save(fig, "gap", 420, 460, yaxis_title="best minus worst NPS (points)", yaxis_range=[0, g.max() * 1.15],
         margin=dict(l=70, r=10, t=20, b=60))


def mix_and_heat():
    m = read("driver_mix_quarterly")
    m = m[m["quarter"] == m["quarter"].max()].assign(driver=lambda d: d["driver"].map(label))
    share = m[m["share_pct"].notna()]
    order = share.groupby("driver")["share_pct"].mean().sort_values().index.tolist()
    fig = px.bar(share, x="share_pct", y="driver", color="app", barmode="group", color_discrete_map=COLORS,
                 category_orders={"driver": order}, labels={"share_pct": "", "driver": ""})
    save(fig, "mix", 620, 430, legend_title_text="", legend=dict(orientation="h", y=-0.15), margin=dict(l=170, r=20, t=20, b=70))
    lost = m.pivot(index="driver", columns="app", values="points_lost")
    lost = lost.loc[lost.mean(axis=1).sort_values().index]
    fig = go.Figure(go.Heatmap(z=lost.values, x=[a.capitalize() for a in lost.columns], y=lost.index, showscale=False,
                               colorscale=[[0, "#ffffff"], [1, "#6f9bc4"]], texttemplate="%{z:.1f}",
                               textfont=dict(size=15, color="#222222")))
    save(fig, "heat", 540, 430, margin=dict(l=170, r=20, t=20, b=70), xaxis_side="bottom")


def stakes():
    """Points at stake per driver in the waterfall, with the sampling error. The top three are the recommendations."""
    t = read("bridge").query("kind == 'term'").set_index("term").loc[NAMED].sort_values("points")
    top = set(t.nlargest(3, "points").index)
    names = [label(d) for d in t.index]
    fig = go.Figure(go.Bar(x=t["points"], y=names, orientation="h", marker_color=[NAVY if d in top else GREY for d in t.index],
                           error_x=dict(type="data", array=t["moe"], color="#444444")))
    fig.add_trace(go.Scatter(x=[t["points"].max() * 1.5] * len(t), y=names, mode="text", showlegend=False,
                             text=[f"{p:.1f}" for p in t["points"]], textfont=dict(size=15)))
    save(fig, "stakes", 560, 460, xaxis_title="NPS points explained (Zepto vs Blinkit)", showlegend=False,
         xaxis_range=[0, t["points"].max() * 1.65], margin=dict(l=170, r=20, t=20, b=70))


def validation():
    c = read("tagger_consistency").set_index("pair")["agreement_pct"]
    kw = read("keyword_vs_tags").set_index("driver").loc["overall", "agreement_pct"]
    rows = [("Pass A vs pass B", c["a vs b"], NAVY), ("Pass A vs main run", c["a vs main run"], NAVY),
            ("Pass B vs main run", c["b vs main run"], NAVY), ("Keyword list vs model tags", kw, GREY)][::-1]
    fig = go.Figure(go.Bar(x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h", marker_color=[r[2] for r in rows],
                           text=[f"{r[1]:.0f}%" for r in rows], textposition="outside"))
    save(fig, "validation", 560, 240, xaxis_title="agreement (%)", xaxis_range=[0, 112], margin=dict(l=190, r=20, t=10, b=55))


if __name__ == "__main__":
    for chart in (trend, latest, gap, mix_and_heat, stakes, validation):
        chart()
    print(*sorted(p.name for p in OUT.glob("deck_*.png")), sep="\n")
