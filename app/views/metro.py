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

MIN_SALES = 24  # Redfin sales in 12 months: about 2 a month
# ml/clusters.py's palette and the one-line profiles from docs/clusters_report.md, by cluster number
TYPE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
PROFILES = [
    "Highest price to income and the only clear price growth; little building",
    "Affordable, strong in-migration, prices still up, slow sales",
    "High prices that stopped rising; homes sell in under a month; people leave",
    "Near the median on everything; prices slightly down, rents flat",
    "Cheap to buy, with the fastest rent growth of any type",
    "The most building and in-migration; prices slipping",
]


@st.cache_data(ttl="1d")
def zip_types():
    """ml/clusters.py's neighborhood types, or None when the export has none."""
    try:
        return load("zip_clusters.parquet")
    except OSError:  # a missing local file or a 404 from Pages
        return None


@st.cache_data(ttl="1d")
def zip_growth():
    """Per ZIP: typical home value growth from the 2015 average to the latest 12 months'
    average (the Overview's window), and Redfin home sales in those 12 months."""
    z = load(
        "mart_zip_month.parquet",
        columns=["zip", "cbsa_code", "month", "zhvi_usd", "homes_sold"],
    )
    recent = z.month > latest_month() - pd.DateOffset(months=12)
    g = pd.DataFrame(
        {
            "start": z[z.month.dt.year == 2015].groupby("zip").zhvi_usd.mean(),
            "latest": z[recent].groupby("zip").zhvi_usd.mean(),
            "cbsa_code": z.groupby("zip").cbsa_code.first(),
        }
    ).dropna()
    g["sales"] = z[recent].groupby("zip").homes_sold.sum().reindex(g.index).fillna(0)
    g["growth"] = g.latest / g.start - 1
    return g.reset_index()


names = metro_names()
latest = latest_month()
st.title("Metro detail")
code, name = pick_metro()
m = metro_month()
mm = m[m.cbsa_code == code].set_index("month")

types = zip_types()
view = "Home value growth"
if types is not None:
    view = (
        st.segmented_control(
            "Color ZIPs by",
            [view, "Neighborhood type"],
            default=view,
            key="zip_view",
        )
        or view
    )  # clicking the selected option again clears it
centre = load("centroids.parquet").query("kind == 'metro' and code == @code").iloc[0]
shapes = load("zip_shapes.geojson")
if view == "Neighborhood type":
    now_end = types.window_end.max()
    t = types[(types.cbsa_code == code) & (types.window_end == now_end)]
    st.subheader(f"Neighborhood types, 12 months to {now_end:%B %Y}")
    st.caption(
        "Each ZIP's nearest of six types, grouped by k-means on its last 12 months of home value and rent "
        "growth, price to income, permits, days on market and net migration. The types sit on a continuum, "
        "not in sharp groups, and are refit by hand, not monthly. Method: docs/clusters_report.md."
    )
    order = (
        types.drop_duplicates("cluster").sort_values("cluster").cluster_name.tolist()
    )
    fig = px.choropleth_map(
        t,
        geojson=shapes,
        locations="zip",
        featureidkey="properties.zip",
        color="cluster_name",
        category_orders={"cluster_name": order},
        color_discrete_map=dict(zip(order, TYPE_COLORS, strict=True)),
        center={"lat": centre.lat, "lon": centre.lon},
        zoom=7.6,
        map_style="carto-positron",
        opacity=0.85,
    )
    fig.update_traces(
        marker_line_width=0.3,
        marker_line_color="white",
        hovertemplate="ZIP %{location}: %{fullData.name}<extra></extra>",
    )
    chart(
        style(
            fig,
            height=560,
            showlegend=True,
            legend={
                "orientation": "h",
                "y": 1.0,
                "yanchor": "bottom",
                "x": 0,
                "title": "",
            },
        )
    )
    then = types[(types.cbsa_code == code) & (types.window_end < now_end)]
    every = types[types.window_end == now_end]
    st.dataframe(
        pd.DataFrame(
            {
                "Type": order,
                "ZIPs": t.cluster.value_counts().reindex(range(6), fill_value=0).values,
                "Share here": t.cluster.value_counts(normalize=True)
                .reindex(range(6), fill_value=0)
                .values,
                "All metros": every.cluster.value_counts(normalize=True)
                .reindex(range(6), fill_value=0)
                .values,
                f"ZIPs in {then.window_end.max():%b %Y}": then.cluster.value_counts()
                .reindex(range(6), fill_value=0)
                .values,
                "Profile": PROFILES,
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Share here": st.column_config.NumberColumn(format="percent"),
            "All metros": st.column_config.NumberColumn(format="percent"),
        },
    )
    stayed = t.merge(then, on="zip", suffixes=("", "_then"))
    st.caption(
        f"{(stayed.cluster == stayed.cluster_then).mean():.0%} of {name}'s typed ZIPs are the same type as in "
        f"{then.window_end.max():%B %Y}, scored with today's type definitions."
    )

else:
    st.subheader(f"Home value growth by ZIP code, 2015 to {latest:%B %Y}")
    g = zip_growth()
    g = g[g.cbsa_code == code]
    thin = g.sales < MIN_SALES
    st.caption(
        f"Typical home value in the 12 months to {latest:%B %Y} against the 2015 average. "
        f"Median ZIP: {g[~thin].growth.median():+.0%}. ZIPs without a 2015 value are left "
        f"blank. {thin.sum()} ZIPs with fewer than {MIN_SALES} Redfin sales in those 12 "
        "months are gray: Zillow's value there rests on few sales and can swing on noise."
    )
    fig = px.choropleth_map(
        g[~thin],
        geojson=shapes,
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
    fig.add_choroplethmap(
        geojson=shapes,
        locations=g[thin].zip,
        featureidkey="properties.zip",
        z=g[thin].sales,
        colorscale=[MUTED, MUTED],
        showscale=False,
        marker={"opacity": 0.85, "line": {"width": 0.3, "color": "white"}},
        hovertemplate="ZIP %{location}: %{z:.0f} sales in 12 months, too few to "
        "rate<extra></extra>",
    )
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

footer(["zillow", "redfin", "qcew", "bps", "acs"], "Census ZCTA boundaries 2020")
