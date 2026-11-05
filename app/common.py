"""Shared by every dashboard page: data loading, the metro picker, chart style and the
page footer."""

import json
import os
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import streamlit as st

LOCAL = Path(__file__).resolve().parent.parent / "data" / "export"
# the monthly pipeline publishes data/export to GitHub Pages; DATA_URL may also be a
# folder, such as the two-metro demo in sample/
REMOTE = os.environ.get(
    "DATA_URL", "https://yearningasian.github.io/metro-housing-affordability/data"
)

# Reference palette (dataviz skill), as in notebooks/common.py: one highlight hue over gray
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#c3c2b7", "#e8e7e3"
BLUE, ORANGE, RED, AQUA = "#2a78d6", "#eb6834", "#e34948", "#1baf7a"
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# lower bounds of the ACS B19001 income brackets (households_by_income)
BRACKETS = (
    np.array([0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100, 125, 150, 200]) * 1000
)


@st.cache_data(ttl="1d", show_spinner="Loading data")
def load(name, columns=None):
    """One export (only `columns`, if given): the local copy when the pipeline ran on
    this machine, else the published one."""
    path = LOCAL / name
    src = path if path.exists() else f"{REMOTE}/{name}"
    if name.endswith(".geojson"):
        with urlopen(src) if str(src).startswith("http") else open(src) as f:
            return json.load(f)
    df = pd.read_parquet(src, columns=columns)
    if "month" in df:
        df["month"] = pd.to_datetime(df["month"])
    return df


def metro_month():
    """The metro mart plus mortgage_share: monthly principal, interest and property tax on
    the typical home (10% down, 30-year fixed at that month's rate, tax at the ACS
    effective rate) over median household income / 12, as in notebooks/common.py.
    Leaves out insurance and HOA fees."""
    m = load("mart_metro_month.parquet").copy()
    m["payment"] = payment(
        m.zhvi_usd, 0.1 * m.zhvi_usd, m.mortgage_rate_pct, m.property_tax_rate
    )
    m["mortgage_share"] = m.payment / (m.median_household_income_usd / 12)
    return m


def payment(price, down, rate_pct, tax_rate):
    """Monthly principal and interest on price - down (30-year fixed at rate_pct), plus
    property tax at tax_rate a year. A down payment above the price leaves no loan."""
    r = rate_pct / 1200
    loan = np.maximum(price - down, 0)
    return loan * r / (1 - (1 + r) ** -360) + price * tax_rate / 12


def metro_names():
    """cbsa_code -> short name ("Dallas-Fort Worth"), sorted by name."""
    m = load("dim_metro.parquet")
    return m.set_index("cbsa_code").metro_name.str.split(",").str[0].sort_values()


def latest_month():
    m = metro_month()
    return m.month[m.price_to_income.notna()].max()


def change(col="price_to_income", start_year=2015):
    """Per metro: the start year's average of col against the latest 12 months' (the
    Phase 9 question 1 metric for price to income), largest rise first."""
    m = metro_month()
    recent = m.month > latest_month() - pd.DateOffset(months=12)
    d = pd.DataFrame(
        {
            "start": m[m.month.dt.year == start_year].groupby("cbsa_code")[col].mean(),
            "latest": m[recent].groupby("cbsa_code")[col].mean(),
        }
    )
    d["change"] = d.latest - d.start
    return d.sort_values("change", ascending=False)


def affordable_share(start_year=2015, burden=0.30):
    """Per metro: the share of households whose income covers the typical home's payment
    at `burden`, as in notebooks/common.py. The start year uses its own ACS brackets and
    average payment; the latest 12 months use the latest vintage's brackets."""
    m = metro_month()
    recent = m.month > latest_month() - pd.DateOffset(months=12)
    h = load("metro_income_brackets.parquet")
    h = h[h.acs_vintage <= latest_month().year]
    h = h.set_index(["acs_vintage", "cbsa_code"]).households_by_income
    newest = h.index.get_level_values("acs_vintage").max()

    def shares(rows, vintage):
        needed = rows.groupby("cbsa_code").payment.mean() * 12 / burden
        return pd.Series(
            {c: share_above(v, h[vintage, c]) for c, v in needed.items()}, dtype=float
        )

    d = pd.DataFrame(
        {
            "start": shares(m[m.month.dt.year == start_year], start_year),
            "latest": shares(m[recent], newest),
        }
    )
    d.attrs["vintage"] = newest
    return d.sort_values("latest")


def share_above(income, households):
    """Share of households with income at or above `income`, linear within a bracket.
    shortcut: above $200k (the open top bracket) it returns the top bracket's share, an
    upper bound; fit a Pareto tail if a needed income ever passes $200k."""
    households = np.asarray(households, dtype=float)
    below = np.concatenate([[0], np.cumsum(households[:-1])]) / households.sum()
    return 1 - np.interp(income, BRACKETS, below)


def pick_metro():
    """The metro selectbox. Its choice is kept in _metro so it survives page changes
    (Streamlit drops a widget's state on pages that don't draw it)."""
    names = metro_names()
    if "_metro" not in st.session_state:
        st.session_state._metro = change().index[0]
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


def footer(keys, extra=None):
    """Sources by key, each with how recent its data is, plus any extra text."""
    m = metro_month()

    def last(col):
        return f"{m.month[m[col].notna()].max():%b %Y}"

    acs = m[m.month == latest_month()].iloc[0]
    wages = m.wages_quarter[m.wages_is_carried_forward.eq(False)].max()
    asof = {
        "zillow": f"Zillow ZHVI and ZORI (home values, rents) to {last('zhvi_usd')}",
        "acs": f"Census ACS {acs.income_acs_survey[-1]}-year {acs.income_acs_vintage} "
        "(household income, population)",
        "qcew": f"BLS QCEW (wages) to {wages}",
        "bps": f"Census Building Permits Survey to {last('permit_units')}",
        "fred": f"Freddie Mac via FRED (mortgage rate) to {last('mortgage_rate_pct')}",
        "irs": f"IRS SOI migration, tax year {m.migration_tax_year.max()}",
        "redfin": f"Redfin (home sales) to {last('homes_sold')}",
    }
    st.divider()
    st.caption(
        "Sources: "
        + "; ".join([asof[k] for k in keys] + ([extra] if extra else []))
        + "."
    )
