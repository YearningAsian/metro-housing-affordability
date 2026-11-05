import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import (
    AQUA,
    BLUE,
    INK,
    INK2,
    MUTED,
    ORANGE,
    RED,
    SURFACE,
    affordable_share,
    chart,
    footer,
    latest_month,
    load,
    metro_month,
    metro_names,
    style,
)

names = metro_names()
m = metro_month()
st.title("Findings")
st.caption(
    "Six of the project's questions, answered across all the metros. The full "
    "write-up is in docs/findings.md."
)

# ---- Q2: did metros that built more see slower price growth?
# December rows hold each calendar year's trailing-12-month permit total
dec = m[(m.month.dt.month == 12) & m.zhvi_usd.notna()]
end = dec.month.dt.year.max()
dec = dec.assign(year=dec.month.dt.year)
zhvi = dec.pivot(index="cbsa_code", columns="year", values="zhvi_usd")
permits = dec[dec.year.between(2016, end)].groupby("cbsa_code").permits_per_1000.mean()
d = pd.DataFrame({"permits": permits, "growth": zhvi[end] / zhvi[2015] - 1}).dropna()
d["name"] = d.index.map(names)

st.subheader("Did metros that built more see slower price growth?")
st.caption(
    f"Building permits per 1,000 residents, yearly average 2016 to {end}, against "
    f"growth in the typical home value from December 2015 to December {end}."
)
fig = go.Figure()
fig.add_scatter(
    x=d.permits,
    y=d.growth,
    mode="markers+text",
    text=d.name,
    # alternate above and below by growth, so neighbors' labels don't collide
    textposition=[
        "top center" if i % 2 else "bottom center"
        for i in d.growth.rank(method="first").astype(int)
    ],
    textfont={"color": INK2, "size": 12},
    marker={"color": BLUE, "size": 11, "line": {"color": "white", "width": 2}},
    hovertemplate="%{text}: %{x:.1f} permits per 1,000 a year, "
    "home values %{y:+.0%}<extra></extra>",
)
if len(d) >= 3:
    slope, intercept = np.polyfit(d.permits, d.growth, 1)
    x = np.array([d.permits.min(), d.permits.max()])
    fig.add_scatter(
        x=x,
        y=intercept + slope * x,
        mode="lines",
        line={"color": MUTED, "width": 2, "dash": "dot"},
        hoverinfo="skip",
    )
    top = d.permits.idxmax()  # Austin, which built by far the most
    rest = d.drop(top)
    r = d.permits.corr(d.growth)
    st.markdown(
        f"Correlation across the {len(d)} metros: **r = {r:+.2f}**, or "
        f"{rest.permits.corr(rest.growth):+.2f} without {names[top]}, which built the "
        f"most. More building went with {'slower' if r < 0 else 'faster'} price growth."
    )
chart(
    style(
        fig,
        height=440,
        xaxis_title="Permits per 1,000 residents a year",
        yaxis_title="Home value growth",
        yaxis_tickformat="+.0%",
    )
)

# ---- Q4: did rents grow faster than wages?
# QCEW wages peak each fourth quarter, so both ends are the same quarter of the year
q = (
    m[m.wages_is_carried_forward.eq(False)]
    .groupby(["cbsa_code", "wages_quarter"])
    .agg(rent=("zori_usd", "mean"), wage=("avg_weekly_wage_usd", "first"))
    .reset_index()
)
last_q = q.wages_quarter.max()
first_q = "2015Q" + last_q[-1]
w = q[q.wages_quarter.isin([first_q, last_q])].pivot(
    index="cbsa_code", columns="wages_quarter"
)
gap = (
    ((w.rent[last_q] / w.rent[first_q]) - (w.wage[last_q] / w.wage[first_q]))
    .dropna()
    .sort_values()
)

st.subheader("Did rents grow faster than wages?")
st.caption(
    f"Growth in the typical rent (Zillow ZORI) minus growth in the average weekly "
    f"wage (BLS QCEW), {first_q} to {last_q}, in percentage points. Red: rents "
    "outgrew wages. Blue: wages grew faster."
)
fig = go.Figure(
    go.Bar(
        x=100 * gap.values,
        y=gap.index.map(names),
        orientation="h",
        marker_color=[RED if v > 0 else BLUE for v in gap.values],
        text=[f"{100 * v:+.0f}" for v in gap.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: rents %{x:+.0f} points against wages<extra></extra>",
    )
)
fig.add_vline(x=0, line_color=INK2, line_width=1)
chart(
    style(
        fig,
        height=max(160, 36 * len(gap) + 40),
        barcornerradius=4,
        bargap=0.3,
        xaxis_showgrid=False,
        xaxis_showticklabels=False,
        xaxis_range=[min(0, 120 * gap.min()), max(0, 120 * gap.max())],  # labels fit
    )
)

# ---- Q7: who can afford the typical home?
a = affordable_share()
labels = a.index.map(names)
st.subheader("Who can afford the typical home?")
st.caption(
    "Share of households whose income covers the monthly payment at 30%: principal, "
    "interest and property tax, with 10% down. 2015 against the latest 12 months, whose "
    f"incomes are the {a.attrs['vintage']} ACS. Counts all households, renters included, "
    "and ignores savings and debts."
)
fig = go.Figure()
fig.add_scatter(
    # one line per metro; None breaks the line between them
    x=[v for s, e in zip(a.start, a.latest, strict=True) for v in (s, e, None)],
    y=[v for n in labels for v in (n, n, None)],
    mode="lines",
    line={"color": MUTED, "width": 2},
    hoverinfo="skip",
    showlegend=False,
)
for col, year, color, side in [
    ("start", "2015", MUTED, "middle right"),
    ("latest", "Latest 12 months", BLUE, "middle left"),
]:
    fig.add_scatter(
        x=a[col],
        y=labels,
        name=year,
        mode="markers+text",
        text=[f"{v:.0%}" for v in a[col]],
        textposition=side,
        textfont={"color": INK2, "size": 12},
        marker={"color": color, "size": 11, "line": {"color": SURFACE, "width": 2}},
        hovertemplate="%{y}, " + year + ": %{x:.0%}<extra></extra>",
    )
chart(
    style(
        fig,
        height=max(200, 36 * len(a) + 70),
        showlegend=True,
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
        xaxis_showticklabels=False,
        xaxis_showgrid=False,
        # room for the labels outside the two ends
        xaxis_range=[a.latest.min() - 0.07, a.start.max() + 0.07],
    )
)

# ---- Q8: what drove the rise in the mortgage share?
# log share = log price + log financing cost per dollar - log monthly income, so the
# three parts add up exactly; as in mortgage_share_split() in notebooks/common.py
latest = latest_month()
recent = m.month.between(latest - pd.DateOffset(months=11), latest)
r = m.mortgage_rate_pct / 1200
logs = pd.DataFrame(
    {
        "cbsa_code": m.cbsa_code,
        "Home prices": np.log(m.zhvi_usd),
        "Rates and tax": np.log(
            0.9 * r / (1 - (1 + r) ** -360) + m.property_tax_rate / 12
        ),
        "Income": -np.log(m.median_household_income_usd / 12),
    }
)
period = {
    "2015": logs[m.month.dt.year == 2015].groupby("cbsa_code").mean(),
    "2021": logs[m.month.dt.year == 2021].groupby("cbsa_code").mean(),
    "latest": logs[recent].groupby("cbsa_code").mean(),
}
windows = {
    "2015 to 2021": ("2015", "2021"),
    "2021 to latest 12 months": ("2021", "latest"),
    "2015 to latest 12 months": ("2015", "latest"),
}
PARTS = {"Home prices": BLUE, "Rates and tax": ORANGE, "Income": AQUA}

st.subheader("What drove the rise in the mortgage share?")
st.caption(
    "The change in the mortgage share (the monthly payment on the typical home over "
    "income), split into home prices, the cost per dollar borrowed (mortgage rate and "
    "property tax) and income. In log points: 0.10 is a share about 10% higher. The "
    "parts add up to the net change (black tick); rising income pulls the share down."
)
window = st.segmented_control(
    "Period", list(windows), default="2021 to latest 12 months", required=True
)
start, end = windows[window]
s = (period[end] - period[start]).dropna()
s["net"] = s.sum(axis=1)
s = s.sort_values("net")
labels = s.index.map(names)
med = s.median()
st.markdown(
    f"Across the {len(s)} metros, at the median: net **{med.net:+.2f}** = home prices "
    f"{med['Home prices']:+.2f}, rates and tax {med['Rates and tax']:+.2f}, income "
    f"{med.Income:+.2f}."
)
fig = go.Figure()
for col, color in PARTS.items():
    fig.add_bar(
        x=s[col],
        y=labels,
        name=col,
        orientation="h",
        marker={"color": color, "line": {"color": SURFACE, "width": 2}},
        hovertemplate="%{y}, " + col.lower() + ": %{x:+.2f}<extra></extra>",
    )
fig.add_scatter(
    x=s.net,
    y=labels,
    name="Net change",
    mode="markers",
    marker={"symbol": "line-ns", "size": 20, "line": {"color": INK, "width": 3}},
    hovertemplate="%{y}, net: %{x:+.2f}<extra></extra>",
)
fig.add_vline(x=0, line_color=INK2, line_width=1)
chart(
    style(
        fig,
        height=max(200, 36 * len(s) + 70),
        barmode="relative",
        bargap=0.3,
        showlegend=True,
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
        xaxis_title="Log points",
        xaxis_tickformat="+.1f",
    )
)

# ---- Q9: did fast price growth land on lower-income ZIPs?
zm = load(
    "mart_zip_month.parquet",
    columns=["zip", "cbsa_code", "month", "zhvi_usd", "median_household_income_usd"],
)
y2015 = zm[zm.month.dt.year == 2015].groupby(["zip", "cbsa_code"])
now = (
    zm[zm.month.between(latest - pd.DateOffset(months=11), latest)]
    .groupby(["zip", "cbsa_code"])
    .zhvi_usd.mean()
)
z = pd.DataFrame(
    {
        "v0": y2015.zhvi_usd.mean(),
        "v1": now,
        "y0": y2015.median_household_income_usd.mean(),
    }
).dropna()
z = z.reset_index()
z["growth"] = z.v1 / z.v0 - 1
g = z.groupby("cbsa_code")
# percent_rank, as in the notebook: the top fifth of the metro's ZIPs for growth
z["top"] = (g.growth.rank(method="min") - 1) / (g.growth.transform("size") - 1) >= 0.8
z["low"] = z.y0 < g.y0.transform("median")
top = z[z.top]
share = top.groupby("cbsa_code").low.agg(["mean", "sum", "size"]).sort_values("mean")


def listed(codes):
    """Metro names as "A", "A and B" or "A, B and C"."""
    n = [names[c] for c in codes]
    return ", ".join(n[:-1]) + " and " + n[-1] if len(n) > 1 else n[0]


st.subheader("Did fast price growth land on lower-income ZIPs?")
st.caption(
    "Of each metro's top fifth of ZIPs for growth in the typical home value, 2015 to the "
    "latest 12 months: the share whose 2015 median household income (ACS 5-year) was "
    "below the median of the metro's ZIPs. If growth ignored income, it would be about "
    "half. An association, not displacement: it says nothing about who moved."
)
st.markdown(
    f"**{top.low.mean():.0%}** of the top-fifth growth ZIPs were lower-income, from "
    f"{share['mean'].min():.0%} in {listed(share.index[share['mean'].eq(share['mean'].min())])}"
    f" to {share['mean'].max():.0%} in "
    f"{listed(share.index[share['mean'].eq(share['mean'].max())])}. That makes "
    f"{int(share['sum'].sum()):,} of {len(z):,} ZIPs lower-income ZIPs with top-fifth "
    "growth."
)
fig = go.Figure(
    go.Bar(
        x=share["mean"],
        y=share.index.map(names),
        orientation="h",
        marker_color=BLUE,
        text=[f"{v:.0%}" for v in share["mean"]],
        textposition="outside",
        cliponaxis=False,
        customdata=share[["sum", "size"]],
        hovertemplate="%{y}: %{customdata[0]} of %{customdata[1]} top-fifth growth "
        "ZIPs were lower-income<extra></extra>",
    )
)
fig.add_vline(
    x=0.5,
    line_color=INK2,
    line_width=1,
    line_dash="dot",
    annotation_text="Half",
    annotation_position="top",
    annotation_font_color=INK2,
)
chart(
    style(
        fig,
        height=max(160, 36 * len(share) + 60),
        margin={"l": 8, "r": 8, "t": 28, "b": 8},  # room for "Half"
        barcornerradius=4,
        bargap=0.3,
        xaxis_showgrid=False,
        xaxis_showticklabels=False,
        xaxis_range=[0, 1.12],  # room for the labels
    )
)
fastest = (
    z[z.top & z.low]
    .sort_values("growth", ascending=False)
    .groupby("cbsa_code")
    .head(3)
    .assign(metro=lambda d: d.cbsa_code.map(names), growth=lambda d: 100 * d.growth)
    .sort_values(["metro", "growth"], ascending=[True, False])
)
with st.expander("The three fastest-growing lower-income ZIPs in each metro"):
    st.dataframe(
        fastest[["metro", "zip", "y0", "v0", "v1", "growth"]],
        hide_index=True,
        column_config={
            "metro": "Metro",
            "zip": "ZIP",
            "y0": st.column_config.NumberColumn("2015 income", format="dollar"),
            "v0": st.column_config.NumberColumn("2015 home value", format="dollar"),
            "v1": st.column_config.NumberColumn("Latest home value", format="dollar"),
            "growth": st.column_config.NumberColumn("Growth", format="%+.0f%%"),
        },
    )

# ---- Q10: does climate risk explain the Florida declines?
try:
    risk = load(
        "dim_zip.parquet",
        columns=["zip", "building_loss_rate", "hurricane_loss_rate"],
    )
except OSError:  # the published exports predate dim_zip
    risk = None

st.subheader("Does climate risk explain the Tampa and Orlando declines?")
if risk is None:
    st.info("This chart appears here after the next monthly pipeline run.")
elif not names.isin(["Tampa", "Orlando"]).any():
    st.info("This chart needs Tampa and Orlando, which the demo data leaves out.")
else:
    since = zm[zm.month.dt.year == 2024].groupby(["zip", "cbsa_code"]).zhvi_usd.mean()
    c = (
        (now / since - 1)
        .dropna()
        .rename("change")
        .reset_index()
        .merge(risk.dropna(), on="zip")
    )
    c["metro"] = c.cbsa_code.map(names)
    by = c.groupby("metro")[["change", "building_loss_rate", "hurricane_loss_rate"]]
    by = by.median()
    fl = c[c.metro.isin(["Tampa", "Orlando"])]
    dm = fl[["hurricane_loss_rate", "change"]] - fl.groupby("metro")[
        ["hurricane_loss_rate", "change"]
    ].transform("mean")
    st.caption(
        "Expected annual building loss over building value (FEMA National Risk Index, "
        "by county, weighted to ZIPs) against the change in the typical home value from "
        "the 2024 average to the latest 12 months, at the median ZIP. Tampa and Orlando "
        "carry the highest hurricane risk."
    )
    other = by.change.drop(["Tampa", "Orlando"], errors="ignore")
    st.markdown(
        f"At the median ZIP, Tampa changed {by.change.get('Tampa', np.nan):+.1%} and "
        f"Orlando {by.change.get('Orlando', np.nan):+.1%}, against "
        f"{other.min():+.1%} in {other.idxmin()}, which has almost no hurricane risk. "
        "Within the two Florida metros, higher hurricane risk does "
        f"not go with larger falls: r = **{dm.hurricane_loss_rate.corr(dm.change):+.2f}**"
        " (each metro's mean removed). The index is fixed by county, so it misses "
        "Hurricane Helene's 2024 storm surge, and it measures physical risk, not "
        "insurance premiums."
    )
    left, right = st.columns(2)
    florida = by.index.isin(["Tampa", "Orlando"])
    fig = go.Figure(
        go.Scatter(
            x=by.building_loss_rate,
            y=by.change,
            mode="markers+text",
            text=by.index,
            # left of the dot where a neighbor on the right, or the edge, would collide
            textposition=[
                {"Seattle": "middle left", "Denver": "middle left"}.get(
                    n, "bottom center" if n == "Dallas-Fort Worth" else "middle right"
                )
                for n in by.index
            ],
            textfont={"color": INK2, "size": 12},
            marker={
                "color": np.where(florida, BLUE, MUTED),
                "size": 11,
                "line": {"color": SURFACE, "width": 2},
            },
            hovertemplate="%{text}: loss rate %{x:.3%} a year, home values "
            "%{y:+.1%}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color=INK2, line_width=1)
    with left:
        st.markdown("**Metro medians, all hazards**")
        chart(
            style(
                fig,
                height=360,
                xaxis_title="Expected annual building loss",
                xaxis_tickformat=".2%",
                yaxis_title="Home value change since 2024",
                yaxis_tickformat="+.0%",
            )
        )
    fig = go.Figure()
    for metro, color in (("Tampa", BLUE), ("Orlando", ORANGE)):
        d = fl[fl.metro == metro]
        fig.add_scatter(
            x=d.hurricane_loss_rate,
            y=d.change,
            name=metro,
            mode="markers",
            customdata=d.zip,
            marker={"color": color, "size": 8, "line": {"color": SURFACE, "width": 1}},
            hovertemplate=metro + " %{customdata}: hurricane loss %{x:.3%} a year, "
            "home value %{y:+.1%}<extra></extra>",
        )
    fig.add_hline(y=0, line_color=INK2, line_width=1)
    with right:
        st.markdown("**Tampa and Orlando ZIPs, hurricanes**")
        chart(
            style(
                fig,
                height=360,
                showlegend=True,
                legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
                xaxis_title="Expected annual hurricane loss",
                xaxis_tickformat=".2%",
                yaxis_title="Home value change since 2024",
                yaxis_tickformat="+.0%",
            )
        )

footer(
    ["zillow", "bps", "acs", "qcew", "fred"],
    "FEMA National Risk Index v1.20 (climate risk)",
)
