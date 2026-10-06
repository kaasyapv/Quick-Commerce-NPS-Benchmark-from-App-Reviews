"""Dashboard: NPS trend, complaint driver mix and sample reviews by driver.

Run: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nps import COLORS, figure

OUT, DATA = ROOT / "outputs", ROOT / "data" / "processed"
st.set_page_config(page_title="Quick commerce NPS", layout="wide")


@st.cache_data
def reviews() -> tuple[pd.DataFrame, bool]:
    """Tagged reviews if the local data exists, else the 20 example quotes that are in the repo."""
    if (DATA / "tags.parquet").exists():
        df = pd.read_parquet(DATA / "sample.parquet").merge(pd.read_parquet(DATA / "tags.parquet")[["reviewId", "primary"]])
        df["month"] = df["at"].dt.to_period("M").dt.to_timestamp().dt.date.astype(str)
        return df.rename(columns={"primary": "driver", "content": "text"})[["app", "month", "score", "text", "driver"]], True
    return pd.read_csv(OUT / "example_quotes.csv").rename(columns={"quote": "text"}), False


nps = pd.read_csv(OUT / "nps_monthly.csv")
mix = pd.read_csv(OUT / "driver_mix_monthly.csv")
months = sorted(nps["period"].unique())

apps = st.sidebar.multiselect("Apps", sorted(COLORS), default=sorted(COLORS))
lo, hi = st.sidebar.select_slider("Months", options=months, value=(months[0], months[-1]), format_func=lambda m: m[:7])
st.title("Quick commerce NPS proxy from Google Play reviews")
st.caption("A review based proxy: 5 stars promoter, 4 passive, 1 to 3 detractor. Not survey NPS.")

picked = nps[nps["app"].isin(apps) & nps["period"].between(lo, hi)]
st.plotly_chart(figure(picked), width="stretch")

st.subheader("Complaint driver mix")
m = mix[mix["app"].isin(apps) & mix["month"].between(lo, hi)].groupby(["app", "driver"], as_index=False)["tagged"].sum()
m["share_pct"] = 100 * m["tagged"] / m.groupby("app")["tagged"].transform("sum")
fig = px.bar(m, x="share_pct", y="driver", color="app", barmode="group", color_discrete_map=COLORS,
             template="simple_white", labels={"share_pct": "share of tagged detractor reviews (%)", "driver": ""})
st.plotly_chart(fig, width="stretch")

st.subheader("Sample reviews by driver")
data, local = reviews()
driver = st.selectbox("Driver", sorted(data["driver"].unique()))
rows = data[(data["driver"] == driver) & data["app"].isin(apps)]
if local:
    rows = rows[rows["month"].between(lo, hi)]
    rows = rows.sample(min(5, len(rows)), random_state=0)
else:
    st.caption("Only 20 example quotes are published, so each driver shows at most 2. Run the app locally for 5 per driver.")
for _, r in rows.iterrows():
    st.markdown(f"**{r['app'].capitalize()}**  \n{r['text']}")
