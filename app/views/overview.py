import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    MUTED,
    chart,
    footer,
    latest_month,
    metro_month,
    metro_names,
    p2i_change,
    pick_metro,
    style,
)

names = metro_names()
change = p2i_change()
worst = change.index[0]
latest = latest_month()

st.title("Which metro got least affordable?")
st.markdown(
    f"### {names[worst]}: a typical home costs {change.latest[worst]:.1f}× the median "
    f"household income, up {change.change[worst]:.2f} since 2015."
)
st.caption(
    "Price to income = Zillow's typical home value ÷ the Census median household income. "
    f"2015 average against the 12 months to {latest:%B %Y}."
)

code, name = pick_metro()
m = metro_month()
now = m[(m.cbsa_code == code) & (m.month == latest)].iloc[0]
rank = list(change.index).index(code) + 1
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Price to income",
    f"{change.latest[code]:.1f}×",
    f"{change.change[code]:+.2f} since 2015",
    delta_color="inverse",
    help=f"Rank {rank} of {len(change)} for the largest rise.",
)
c2.metric(
    "Typical home value",
    f"${now.zhvi_usd:,.0f}",
    f"{now.zhvi_yoy_growth:+.1%} in a year",
    delta_color="inverse",
)
c3.metric(
    "Typical rent",
    f"${now.zori_usd:,.0f}/mo",
    f"{now.zori_yoy_growth:+.1%} in a year",
    delta_color="inverse",
)
c4.metric(
    "30-year mortgage rate",
    f"{now.mortgage_rate_pct:.2f}%",
    help="National, Freddie Mac weekly survey.",
)

left, right = st.columns([2, 3], gap="large")
with left:
    st.subheader("Rise in price to income since 2015")
    s = change.change.sort_values()
    fig = go.Bar(
        x=s.values,
        y=s.index.map(names),
        orientation="h",
        marker_color=[BLUE if c == code else MUTED for c in s.index],
        text=[f"{v:+.2f}" for v in s.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:+.2f}<extra></extra>",
    )
    chart(
        style(
            go.Figure(fig),
            height=420,
            barcornerradius=4,
            bargap=0.3,
            xaxis_showgrid=False,
            xaxis_showticklabels=False,
            xaxis_range=[min(0, s.min()), s.max() * 1.15],  # room for the end labels
        )
    )
with right:
    st.subheader("Price to income, monthly")
    fig = go.Figure()
    # selected metro drawn last, on top
    for c in sorted(names.index, key=lambda c: c == code):
        d = m[(m.cbsa_code == c) & m.price_to_income.notna()]
        sel = c == code
        fig.add_scatter(
            x=d.month,
            y=d.price_to_income,
            name=names[c],
            mode="lines",
            line={"color": BLUE if sel else MUTED, "width": 2.5 if sel else 1},
            hovertemplate="%{fullData.name}, %{x|%b %Y}: %{y:.2f}×<extra></extra>",
        )
    last = m[(m.cbsa_code == code) & (m.month == latest)]
    fig.add_annotation(
        x=latest,
        y=last.price_to_income.iloc[0],
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
            yaxis_ticksuffix="×",
            margin={"l": 8, "r": 110, "t": 8, "b": 8},
        )
    )

footer(
    "Zillow ZHVI and ZORI (home values and rents), Census ACS 5-year (household income, which lags about "
    "2 years), Freddie Mac via FRED (mortgage rate)"
)
