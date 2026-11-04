import math

import plotly.graph_objects as go
import streamlit as st
from common import BLUE, INK2, chart, footer, load, pick_metro, style

TOP = 15

st.title("Migration")
code, name = pick_metro()
o = load("mart_migration_origins.parquet")
o = o[(o.cbsa_code == code) & (o.tax_year == o.tax_year.max())]
move_year = o.move_year.iloc[0]

# people-weighted, as in Phase 9 question 3
priced = o.dropna(subset=["origin_to_metro_zhvi"])
ratio = (priced.origin_to_metro_zhvi * priced.people).sum() / priced.people.sum()
st.markdown(
    f"### {o.people.sum():,.0f} people moved to {name} from other counties in "
    f"{move_year}. Homes where they came from cost {abs(ratio - 1):.0%} "
    f"{'more' if ratio > 1 else 'less'} than in {name}."
)
st.caption(
    "IRS county-to-county migration from tax returns: people are filers plus their "
    "dependents, and only flows of 20 returns or more are published. Moves between the "
    "metro's own counties are left out. The home-value comparison weights each origin "
    "county by the people it sent."
)

top = o.nlargest(TOP, "people")
places = load("centroids.parquet").set_index(["kind", "code"])
end = places.loc[("metro", code)]
top = top.join(places.loc["county"], on="origin_county_fips").dropna(subset=["lat"])
# zoom to the nearest origins that sent about 80% of the top origins' people, so a
# far-off county or two doesn't shrink the map to a continent
dist = (top.lat - end.lat) ** 2 + (
    (top.lon - end.lon) * math.cos(math.radians(end.lat))
) ** 2
near = top.loc[dist.sort_values().index]
near = near[near.people.cumsum().shift(fill_value=0) < 0.8 * near.people.sum()]
lat, lon = [*near.lat, end.lat], [*near.lon, end.lon]

st.subheader(f"Top {TOP} origin counties, moves in {move_year}")
fig = go.Figure()
width = 1 + 7 * top.people / top.people.max()
for r, w in zip(top.itertuples(), width):
    fig.add_scattermap(
        lat=[r.lat, end.lat],
        lon=[r.lon, end.lon],
        mode="lines",
        line={"color": BLUE, "width": w},
        opacity=0.6,
        hoverinfo="skip",
    )
fig.add_scattermap(
    lat=top.lat,
    lon=top.lon,
    mode="markers",
    marker={"color": BLUE, "size": 9},
    customdata=top[["origin_name", "people", "origin_to_metro_zhvi"]],
    hovertemplate="%{customdata[0]}: %{customdata[1]:,.0f} people, "
    "homes %{customdata[2]:.0%} of " + name + "'s<extra></extra>",
)
fig.add_scattermap(
    lat=[end.lat],
    lon=[end.lon],
    mode="markers+text",
    marker={"color": INK2, "size": 12},
    text=[name],
    textfont={"size": 14, "color": INK2},
    textposition="top center",
    hoverinfo="skip",
)
fig.update_layout(
    map={
        "style": "carto-positron",
        "center": {"lat": (min(lat) + max(lat)) / 2, "lon": (min(lon) + max(lon)) / 2},
        # fit the flows: a 512 px tile spans 360 degrees at zoom 0; sized for a ~700 x 520 px
        # map, where a degree of latitude takes about 3 times the room of one of longitude
        "zoom": min(
            6,
            math.log2(492 / max(max(lon) - min(lon), 3 * (max(lat) - min(lat)), 1))
            - 0.2,
        ),
    }
)
chart(style(fig, height=520))
st.caption(
    "The map frames the nearest origins, which sent about 80% of these movers; "
    "lines to farther ones may run off the edge."
)

st.subheader("Were they moving somewhere cheaper?")
st.caption(
    f"Typical home value in each origin county ÷ {name}'s. Right of the line: homes "
    f"cost more where they came from. Dot size: people."
)
dots = top.dropna(subset=["origin_to_metro_zhvi"]).sort_values("people")
fig = go.Figure(
    go.Scatter(
        x=dots.origin_to_metro_zhvi,
        y=dots.origin_name,
        mode="markers+text",
        marker={
            "color": BLUE,
            "size": 8 + 16 * dots.people / dots.people.max(),
            "line": {"color": "white", "width": 2},
        },
        text=[f"{v:.2f}×" for v in dots.origin_to_metro_zhvi],
        textposition="middle right",
        cliponaxis=False,
        textfont={"color": INK2},
        customdata=dots.people,
        hovertemplate="%{y}: homes %{x:.2f}× " + name + "'s, "
        "%{customdata:,.0f} people<extra></extra>",
    )
)
fig.add_vline(x=1, line_color=INK2, line_width=1)
hi = max(2, dots.origin_to_metro_zhvi.max() * 1.15)  # room for the labels
chart(
    style(
        fig,
        height=max(200, 30 * len(dots) + 60),
        xaxis_range=[0, hi],
        xaxis_ticksuffix="×",
        yaxis_showgrid=False,
        margin={"l": 8, "r": 48, "t": 8, "b": 8},  # room for the last label
    )
)

st.dataframe(
    top[["origin_name", "people", "agi_per_return_usd", "origin_to_metro_zhvi"]],
    hide_index=True,
    width="stretch",
    column_config={
        "origin_name": "Origin county",
        "people": st.column_config.NumberColumn("People", format="localized"),
        "agi_per_return_usd": st.column_config.NumberColumn(
            "Income per return", format="dollar"
        ),
        "origin_to_metro_zhvi": st.column_config.ProgressColumn(
            f"Home value against {name}",
            help="Typical home value in the origin county ÷ the metro's. 1.0 = equal.",
            format="%.2f×",
            min_value=0,
            max_value=float(max(2, top.origin_to_metro_zhvi.max())),
        ),
    },
)

footer(["irs", "zillow"], "Census county boundaries 2024")
