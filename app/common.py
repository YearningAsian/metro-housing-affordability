"""Shared by every dashboard page: data loading, the metro picker, chart style and the
page footer."""

import json
import os
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import streamlit as st

LOCAL = Path(__file__).resolve().parent.parent / "data" / "export"
# the monthly pipeline publishes data/export to GitHub Pages
REMOTE = os.environ.get(
    "DATA_URL", "https://yearningasian.github.io/metro-housing-affordability/data"
)

# Reference palette (dataviz skill), as in notebooks/common.py: one highlight hue over gray
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#c3c2b7", "#e8e7e3"
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]


@st.cache_data(ttl="1d", show_spinner="Loading data")
def load(name):
    """One export: the local copy when the pipeline ran on this machine, else the
    published one."""
    path = LOCAL / name
    if name.endswith(".geojson"):
        with path.open() if path.exists() else urlopen(f"{REMOTE}/{name}") as f:
            return json.load(f)
    df = pd.read_parquet(path if path.exists() else f"{REMOTE}/{name}")
    if "month" in df:
        df["month"] = pd.to_datetime(df["month"])
    return df


def metro_month():
    return load("mart_metro_month.parquet")


def metro_names():
    """cbsa_code -> short name ("Dallas-Fort Worth"), sorted by name."""
    m = load("dim_metro.parquet")
    return m.set_index("cbsa_code").metro_name.str.split(",").str[0].sort_values()


def latest_month():
    m = metro_month()
    return m.month[m.price_to_income.notna()].max()


def p2i_change(start_year=2015):
    """Per metro: the start year's average price-to-income against the latest 12
    months' (the Phase 9 question 1 metric), largest rise first."""
    m = metro_month()
    recent = m.month > latest_month() - pd.DateOffset(months=12)
    d = pd.DataFrame(
        {
            "start": m[m.month.dt.year == start_year]
            .groupby("cbsa_code")
            .price_to_income.mean(),
            "latest": m[recent].groupby("cbsa_code").price_to_income.mean(),
        }
    )
    d["change"] = d.latest - d.start
    return d.sort_values("change", ascending=False)


def pick_metro():
    """The metro selectbox. Its choice is kept in _metro so it survives page changes
    (Streamlit drops a widget's state on pages that don't draw it)."""
    names = metro_names()
    if "_metro" not in st.session_state:
        st.session_state._metro = p2i_change().index[0]
    st.session_state.metro = st.session_state._metro
    st.selectbox(
        "Metro",
        names.index,
        format_func=names.get,
        key="metro",
        width=320,
        on_change=lambda: st.session_state.update(_metro=st.session_state.metro),
    )
    return st.session_state.metro, names[st.session_state.metro]


def style(fig, height=380, **layout):
    """The house chart look: light surface, recessive grid, ink-colored text."""
    axis = {
        "gridcolor": GRID,
        "linecolor": MUTED,
        "zeroline": False,
        "tickfont": {"color": INK2},
        "automargin": True,
    }
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": INK, "size": 13},
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        hoverlabel={"bgcolor": "white", "bordercolor": MUTED, "font_color": INK},
        showlegend=False,
        xaxis=axis,
        yaxis=axis,
    )
    fig.update_layout(**layout)
    return fig


def chart(fig):
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def footer(sources):
    st.divider()
    st.caption(f"Data as of {latest_month():%B %Y}. Sources: {sources}.")
