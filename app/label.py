"""Hand labelling page: one review at a time, saved to to_label.csv after every click.

Run: streamlit run app/label.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from drivers import DRIVERS, RULES

CSV = ROOT / "data" / "processed" / "to_label.csv"


def load() -> pd.DataFrame:
    return pd.read_csv(CSV, dtype=str, keep_default_na=False)


def save(i: int, driver: str):
    df = load()
    df.loc[i, "my_label"] = driver
    df.to_csv(CSV, index=False)
    st.session_state.i = i + 1


df = load()
if "i" not in st.session_state:  # resume at the first review without a label
    todo = df.index[df["my_label"] == ""]
    st.session_state.i = int(todo[0]) if len(todo) else len(df)
i = st.session_state.i

st.sidebar.markdown(RULES.read_text())
st.progress((df["my_label"] != "").mean())
if i >= len(df):
    st.success(f"All {len(df)} labelled. You can close this page.")
    st.stop()

st.subheader(f"{i + 1} of {len(df)}")
st.caption(f"{df.loc[i, 'app']}, {(df['my_label'] != '').sum()} labelled so far")
st.write(df.loc[i, "content"])
if df.loc[i, "my_label"]:
    st.info(f"current label: {df.loc[i, 'my_label']}")

for driver, definition in DRIVERS.items():
    button, text = st.columns([2, 5])
    button.button(driver, key=driver, on_click=save, args=(i, driver), use_container_width=True)
    text.caption(definition)

if i > 0:
    st.button("Back", on_click=lambda: st.session_state.update(i=i - 1))
