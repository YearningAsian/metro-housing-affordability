import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    MUTED,
    change,
    chart,
    footer,
    latest_month,
    metro_month,
    metro_names,
    pick_metro,
    style,
)

names = metro_names()
p2i = change()
share = change("mortgage_share")
worst = p2i.index[0]
latest = latest_month()

st.title("Which metro got least affordable?")
st.markdown(
    f"### {names[worst]}: a typical home costs {p2i.latest[worst]:.1f}× the median "
    f"household income, up from {p2i.start[worst]:.1f}× in 2015."
)
st.caption(
    "Price to income = Zillow's typical home value ÷ the Census median household income. "
    f"2015 average against the 12 months to {latest:%B %Y}."
)

code, name = pick_metro()
m = metro_month()
mm = m[m.cbsa_code == code].set_index("month")
now = mm.loc[latest]
year_ago = mm.loc[latest - pd.DateOffset(years=1)]
rank = list(p2i.index).index(code) + 1
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Price to income",
    f"{p2i.latest[code]:.1f}×",
    f"{p2i.change[code]:+.2f} since 2015",
    delta_color="inverse",
    help=f"Rank {rank} of {len(p2i)} for the largest rise.",
)
c2.metric(
    "Mortgage share of income",
    f"{share.latest[code]:.0%}",
    f"{100 * share.change[code]:+.0f} pts since 2015",
    delta_color="inverse",
    help="Monthly principal, interest and property tax on the typical home, 10% down, "
    "30-year fixed at that month's rate, over monthly median household income. Leaves "
    "out insurance and HOA fees. Latest 12 months against the 2015 average.",
)
c3.metric(
    "Typical home value",
    f"${now.zhvi_usd:,.0f}",
    f"{now.zhvi_yoy_growth:+.1%} in a year",
    delta_color="inverse",
)
c4.metric(
    "Typical rent",
    f"${now.zori_usd:,.0f}/mo",
    f"{now.zori_yoy_growth:+.1%} in a year",
    delta_color="inverse",
)
c5.metric(
    "30-year mortgage rate",
    f"{now.mortgage_rate_pct:.2f}%",
    f"{now.mortgage_rate_pct - year_ago.mortgage_rate_pct:+.2f} pts in a year",
    delta_color="inverse",
    help="National, Freddie Mac weekly survey.",
)

measure = st.segmented_control(
    "Measure",
    ["Price to income", "Mortgage share of income"],
    default="Price to income",
    required=True,
)
if measure == "Price to income":
    col, d, unit = "price_to_income", p2i, "price to income since 2015"
    bar_fmt, line_fmt, axis = "{:+.2f}", "%{y:.2f}×", {"yaxis_ticksuffix": "×"}
else:
    col, d, unit = "mortgage_share", share, "mortgage share since 2015, points"
    d = d.assign(change=100 * d.change)
    bar_fmt, line_fmt, axis = "{:+.0f}", "%{y:.0%}", {"yaxis_tickformat": ".0%"}

left, right = st.columns([2, 3], gap="large")
with left:
    st.subheader(f"Rise in {unit}")
    s = d.change.sort_values()
    fig = go.Bar(
        x=s.values,
        y=s.index.map(names),
        orientation="h",
        marker_color=[BLUE if c == code else MUTED for c in s.index],
        text=[bar_fmt.format(v) for v in s.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
    )
    chart(
        style(
            go.Figure(fig),
            height=420,
            barcornerradius=4,
            bargap=0.3,
            xaxis_showgrid=False,
            xaxis_showticklabels=False,
            xaxis_range=[min(0, s.min() * 1.15), s.max() * 1.15],  # room for labels
        )
    )
with right:
    st.subheader(f"{measure}, monthly")
    fig = go.Figure()
    # selected metro drawn last, on top
    for c in sorted(names.index, key=lambda c: c == code):
        dd = m[(m.cbsa_code == c) & m[col].notna()]
        sel = c == code
        fig.add_scatter(
            x=dd.month,
            y=dd[col],
            name=names[c],
            mode="lines",
            line={"color": BLUE if sel else MUTED, "width": 2.5 if sel else 1},
            hovertemplate="%{fullData.name}, %{x|%b %Y}: "
            + line_fmt
            + "<extra></extra>",
        )
    fig.add_annotation(
        x=latest,
        y=now[col],
        text=f"<b>{name}</b>",
        xanchor="left",
        showarrow=False,
        font_color=BLUE,
        xshift=4,
    )
    chart(
        style(
            fig,
            height=420,
            hovermode="closest",
            margin={"l": 8, "r": 110, "t": 8, "b": 8},
            xaxis_range=[m.month.min(), latest],  # the end label sits in the margin
            **axis,
        )
    )

footer(["zillow", "acs", "fred"])
