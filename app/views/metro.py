import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    BLUES,
    INK2,
    MUTED,
    ORANGE,
    chart,
    footer,
    latest_month,
    load,
    metro_month,
    metro_names,
    pick_metro,
    style,
)


@st.cache_data(ttl="1d")
def zip_growth():
    """Per ZIP: typical home value growth from the 2015 average to the latest 12 months'
    average (the Overview's window)."""
    z = load("mart_zip_month.parquet")[["zip", "cbsa_code", "month", "zhvi_usd"]]
    recent = z.month > latest_month() - pd.DateOffset(months=12)
    g = pd.DataFrame(
        {
            "start": z[z.month.dt.year == 2015].groupby("zip").zhvi_usd.mean(),
            "latest": z[recent].groupby("zip").zhvi_usd.mean(),
            "cbsa_code": z.groupby("zip").cbsa_code.first(),
        }
    ).dropna()
    g["growth"] = g.latest / g.start - 1
    return g.reset_index()


names = metro_names()
latest = latest_month()
st.title("Metro detail")
code, name = pick_metro()
m = metro_month()
mm = m[m.cbsa_code == code].set_index("month")

st.subheader(f"Home value growth by ZIP code, 2015 to {latest:%B %Y}")
g = zip_growth()
g = g[g.cbsa_code == code]
st.caption(
    f"Typical home value in the 12 months to {latest:%B %Y} against the 2015 average. "
    f"Median ZIP: {g.growth.median():+.0%}. ZIPs without a 2015 value are left blank."
)
centre = load("centroids.parquet").query("kind == 'metro' and code == @code").iloc[0]
fig = px.choropleth_map(
    g,
    geojson=load("zip_shapes.geojson"),
    locations="zip",
    featureidkey="properties.zip",
    color="growth",
    color_continuous_scale=BLUES,
    custom_data=["latest"],
    center={"lat": centre.lat, "lon": centre.lon},
    zoom=7.6,
    map_style="carto-positron",
    opacity=0.85,
)
fig.update_traces(
    marker_line_width=0.3,
    marker_line_color="white",
    hovertemplate="ZIP %{location}: %{z:+.0%} since 2015, "
    "typical home $%{customdata[0]:,.0f}<extra></extra>",
)
fig.update_coloraxes(colorbar={"title": "", "tickformat": "+.0%", "thickness": 12})
chart(style(fig, height=520))

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Home values against wages")
    st.caption(
        "Both indexed to their 2015 average = 100. Wages are the QCEW average weekly "
        "wage, all industries, which peaks each fourth quarter with bonuses; a "
        "quarter's wage repeats until the next one is published."
    )
    fig = go.Figure()
    for col, label, color in [
        ("zhvi_usd", "Home value", BLUE),
        ("avg_weekly_wage_usd", "Weekly wage", ORANGE),
    ]:
        s = mm[col].dropna()
        s = 100 * s / s[s.index.year == 2015].mean()
        fig.add_scatter(
            x=s.index,
            y=s,
            name=label,
            mode="lines",
            line={"color": color, "width": 2},
            hovertemplate=f"{label}, %{{x|%b %Y}}: %{{y:.0f}}<extra></extra>",
        )
        fig.add_annotation(
            x=s.index[-1],
            y=s.iloc[-1],
            text=f"<b>{label}</b> {s.iloc[-1]:.0f}",
            xanchor="left",
            showarrow=False,
            font_color=INK2,
            xshift=4,
        )
    fig.add_hline(y=100, line_color=MUTED, line_width=1)
    chart(
        style(
            fig,
            showlegend=True,
            legend={"orientation": "h", "y": 1.08, "x": 0},
            margin={"l": 8, "r": 130, "t": 8, "b": 8},
            xaxis_range=[mm.index.min(), latest],  # the end labels sit in the margin
        )
    )
with right:
    st.subheader("Building permits per 1,000 residents")
    st.caption(
        "New housing units authorized in the past 12 months. "
        f"{name} in blue, the other metros in gray."
    )
    fig = go.Figure()
    # selected metro drawn last, on top
    for c in sorted(names.index, key=lambda c: c == code):
        d = m[(m.cbsa_code == c) & m.permits_per_1000.notna()]
        sel = c == code
        fig.add_scatter(
            x=d.month,
            y=d.permits_per_1000,
            name=names[c],
            mode="lines",
            line={"color": BLUE if sel else MUTED, "width": 2.5 if sel else 1},
            hovertemplate="%{fullData.name}, %{x|%b %Y}: %{y:.1f}<extra></extra>",
        )
    chart(style(fig, hovermode="closest"))

footer(
    "Zillow ZHVI (home values), BLS QCEW (wages), Census Building Permits Survey and "
    "ACS 5-year population (permits per 1,000), Census ZCTA boundaries 2020"
)
