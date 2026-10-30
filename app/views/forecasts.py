import plotly.express as px
import streamlit as st
from common import BLUE, RED, chart, footer, load, pick_metro, style

st.title("Forecasts")
st.caption(
    "A LightGBM model, refit each month on every ZIP outcome known so far, forecasts "
    "each ZIP's typical home value 12 months ahead and flags the ZIPs most likely to "
    "grow fastest in their metro. Not investment advice: a hot ZIP for buyers can mean "
    "rising rents and displacement for the people who live there."
)
try:
    f = load("mart_zip_forecast.parquet")
except OSError:  # the published exports predate the forecast mart
    f = None
if f is None or f.empty:
    st.info("Forecasts appear here after the next monthly pipeline run.")
    footer("Zillow ZHVI, the project's monthly model")
    st.stop()

code, name = pick_metro()
f = f[(f.cbsa_code == code) & (f.month == f.month.max())]
month = f.month.max()
st.subheader(
    f"Forecast home value growth, {month:%B %Y} to {month.replace(year=month.year + 1):%B %Y}"
)
st.caption(
    "In the 2024-2025 backtest a no-change forecast beat the model on average error, "
    "so read these as a ranking of ZIPs within the metro, not as price targets. The "
    "band aims at 80%; in the backtest the same method held 94% of outcomes, so it "
    "runs wide."
)
a, b, c = st.columns(3)
a.metric("Median ZIP forecast", f"{f.growth_pred.median():+.1%}")
b.metric("ZIPs flagged hot", f"{f.hot_flag.sum()} of {len(f)}")
c.metric(
    "Model run",
    f"{f.run_date.max():%d %b %Y}",
    help=f"commit {f.model_version.iloc[0]}",
)

centre = load("centroids.parquet").query("kind == 'metro' and code == @code").iloc[0]
top = max(f.growth_pred.abs().max(), 0.01)
fig = px.choropleth_map(
    f,
    geojson=load("zip_shapes.geojson"),
    locations="zip",
    featureidkey="properties.zip",
    color="growth_pred",
    color_continuous_scale=[RED, "#f0efec", BLUE],
    range_color=[-top, top],  # gray at zero: blue rises, red falls
    custom_data=["zhvi_usd", "growth_lo", "growth_hi", "hot_flag"],
    center={"lat": centre.lat, "lon": centre.lon},
    zoom=7.6,
    map_style="carto-positron",
    opacity=0.85,
)
fig.update_traces(
    marker_line_width=0.3,
    marker_line_color="white",
    hovertemplate="ZIP %{location}: %{z:+.1%} forecast "
    "(80% band %{customdata[1]:+.1%} to %{customdata[2]:+.1%}), "
    "typical home $%{customdata[0]:,.0f}, hot: %{customdata[3]}<extra></extra>",
)
fig.update_coloraxes(colorbar={"title": "", "tickformat": "+.0%", "thickness": 12})
chart(style(fig, height=520))

st.subheader(f"{name} ZIPs by hot-ZIP score")
t = f.sort_values("hot_score", ascending=False)[
    [
        "zip",
        "zhvi_usd",
        "growth_pred",
        "growth_lo",
        "growth_hi",
        "hot_rank_pct",
        "hot_flag",
    ]
]
pct = ["growth_pred", "growth_lo", "growth_hi", "hot_rank_pct"]
t[pct] = t[pct] * 100
t["zhvi_usd"] = t.zhvi_usd.round(-3).astype("Int64")
st.dataframe(
    t,
    hide_index=True,
    width="stretch",
    column_config={
        "zip": "ZIP",
        "zhvi_usd": st.column_config.NumberColumn(
            "Typical home, $", format="localized"
        ),
        "growth_pred": st.column_config.NumberColumn("Forecast", format="%+.1f%%"),
        "growth_lo": st.column_config.NumberColumn("Band low", format="%+.1f%%"),
        "growth_hi": st.column_config.NumberColumn("Band high", format="%+.1f%%"),
        "hot_rank_pct": st.column_config.NumberColumn(
            "Hot rank",
            format="%.0f",
            help="Percentile of the hot-ZIP score within the metro",
        ),
        "hot_flag": st.column_config.CheckboxColumn(
            "Flagged hot", help="Top 20% of the metro's ZIPs"
        ),
    },
)
footer(
    "Zillow ZHVI and the project's point-in-time features; model details in "
    "docs/model_card.md"
)
