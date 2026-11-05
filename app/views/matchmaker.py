import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    GRID,
    INK2,
    chart,
    footer,
    load,
    metro_names,
    payment,
    pick_metro,
    style,
)


@st.cache_data(ttl="1d")
def latest_zips():
    """Each ZIP's typical home value, rent and property tax rate in the latest Zillow
    month, with the forecast when the export has one."""
    z = load(
        "mart_zip_month.parquet",
        columns=[
            "zip",
            "cbsa_code",
            "month",
            "zhvi_usd",
            "zori_usd",
            "property_tax_rate",
            "mortgage_rate_pct",
        ],
    )
    z = z[z.month == z.month[z.zhvi_usd.notna()].max()].dropna(subset=["zhvi_usd"])
    # a ZIP without its own ACS tax rate takes its metro's median
    z["property_tax_rate"] = z.property_tax_rate.fillna(
        z.groupby("cbsa_code").property_tax_rate.transform("median")
    )
    try:
        f = load(
            "mart_zip_forecast.parquet",
            columns=["zip", "month", "growth_pred", "hot_flag"],
        )
        f = f[f.month == f.month.max()].drop(columns="month")
    except OSError:  # the published exports predate the forecast mart
        f = pd.DataFrame(columns=["zip", "growth_pred", "hot_flag"])
    return z.merge(f, on="zip", how="left")


st.title("Matchmaker")
st.caption(
    "Enter your household's income and savings to see which metros and ZIPs fit, at the "
    "typical home value or the typical rent in each ZIP."
)

z = latest_zips().copy()
month = z.month.max()
rate = z.mortgage_rate_pct.dropna()
rate = rate.iloc[0] if len(rate) else np.nan

c1, c2, c3, c4 = st.columns([1, 1, 1, 1], vertical_alignment="bottom")
income = c1.number_input(
    "Household income, per year", min_value=0, value=90_000, step=5_000, format="%d"
)
mode = c2.segmented_control(
    "Looking to", ["Buy", "Rent"], default="Buy", required=True, key="match_mode"
)
down = c3.number_input(
    "Savings for a down payment",
    min_value=0,
    value=40_000,
    step=5_000,
    format="%d",
    disabled=mode == "Rent",
)
burden = c4.slider("Housing costs up to", 20, 40, 30, format="%d%% of income") / 100
budget = income / 12 * burden

if mode == "Buy":
    z["cost"] = payment(z.zhvi_usd, down, rate, z.property_tax_rate)
    how = (
        f"principal, interest and property tax on the typical home, 30-year fixed at "
        f"{rate:.2f}% ({month:%B %Y}), after a ${down:,.0f} down payment"
    )
else:
    z = z.dropna(subset=["zori_usd"])
    z["cost"] = z.zori_usd
    how = f"the typical rent (Zillow ZORI, {month:%B %Y})"
z["fits"] = z.cost <= budget
names = metro_names()

st.subheader(f"{z.fits.sum():,} of {len(z):,} ZIPs fit ${budget:,.0f} a month")
by_metro = (
    z.groupby("cbsa_code")
    .agg(fit=("fits", "sum"), n=("fits", "size"))
    .assign(share=lambda d: d.fit / d.n, name=lambda d: d.index.map(names))
    .sort_values(["share", "fit"])
)
if z.fits.any():
    top = by_metro.iloc[-1]
    st.caption(  # escape $ so Streamlit doesn't read a pair of them as LaTeX
        f"Monthly cost: {how}. Most room in {top['name']}: {top.fit:,.0f} of its "
        f"{top.n:,.0f} ZIPs fit. Leaves out insurance, HOA fees and closing costs.".replace(
            "$", r"\$"
        )
    )
else:
    cheapest = z.loc[z.cost.idxmin()]
    st.caption(
        f"Monthly cost: {how}. None fit. The cheapest, {cheapest.zip} in "
        f"{names.get(cheapest.cbsa_code, cheapest.cbsa_code)}, costs "
        f"${cheapest.cost:,.0f} a month, which takes an income of "
        f"${cheapest.cost * 12 / burden:,.0f} at {burden:.0%}.".replace("$", r"\$")
    )

fig = go.Figure(
    go.Bar(
        x=100 * by_metro.share,
        y=by_metro.name,
        orientation="h",
        marker_color=BLUE,
        text=[
            f"{f:,.0f} of {n:,.0f}"
            for f, n in zip(by_metro.fit, by_metro.n, strict=True)
        ],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.0f}% of ZIPs fit<extra></extra>",
    )
)
chart(
    style(
        fig,
        height=36 * len(by_metro) + 60,
        barcornerradius=4,
        bargap=0.3,
        xaxis_range=[0, 118],  # room for the "x of y" labels past a full bar
        xaxis_tickvals=[0, 25, 50, 75, 100],
        xaxis_ticktext=["0%", "25%", "50%", "75%", "100%"],
        xaxis_title="Share of the metro's ZIPs that fit",
        yaxis_showgrid=False,
        xaxis_gridcolor=GRID,
    )
)

code, name = pick_metro()
fits = z[(z.cbsa_code == code) & z.fits].sort_values("cost", ascending=False)
st.subheader(f"ZIPs that fit in {name}")
if fits.empty:
    m = z[z.cbsa_code == code]
    st.info(
        f"None of {name}'s {len(m):,} ZIPs fit. The cheapest costs "
        f"${m.cost.min():,.0f} a month."
        if len(m)
        else f"No {name} ZIPs have a typical {'rent' if mode == 'Rent' else 'home value'}."
    )
else:
    st.caption(
        "Most expensive first: the top rows use the most of your budget. The forecast is the "
        "[Forecasts](/forecasts) page's 12-month growth; hot marks a ZIP flagged to grow "
        "fastest in its metro."
    )
    fits = fits.assign(left=budget - fits.cost, growth=100 * fits.growth_pred)
    st.dataframe(
        fits[["zip", "zhvi_usd", "zori_usd", "cost", "left", "growth", "hot_flag"]],
        hide_index=True,
        width="stretch",
        column_config={
            "zip": "ZIP",
            "zhvi_usd": st.column_config.NumberColumn("Typical home", format="$%,.0f"),
            "zori_usd": st.column_config.NumberColumn("Typical rent", format="$%,.0f"),
            "cost": st.column_config.NumberColumn("Monthly cost", format="$%,.0f"),
            "left": st.column_config.NumberColumn("Left each month", format="$%,.0f"),
            "growth": st.column_config.NumberColumn(
                "Forecast, 12 months", format="%+.1f%%"
            ),
            "hot_flag": st.column_config.CheckboxColumn("Hot"),
        },
    )

st.markdown(
    f"<span style='color:{INK2}'>A rule of thumb, not a loan offer: lenders also weigh debts, "
    "credit and the full monthly cost.</span>",
    unsafe_allow_html=True,
)
footer(["zillow", "acs", "fred"], "the project's monthly model")
