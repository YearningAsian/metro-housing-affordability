import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    INK2,
    MUTED,
    RED,
    chart,
    footer,
    metro_month,
    metro_names,
    style,
)

names = metro_names()
m = metro_month()
st.title("Findings")
st.caption(
    "Two of the project's questions, answered across all the metros. The full "
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

footer(["zillow", "bps", "acs", "qcew"])
