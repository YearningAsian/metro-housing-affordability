"""Shared setup for the Phase 9 notebooks: a read-only warehouse connection, the
question metrics (reused by the robustness notebook) and the chart style."""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "docs" / "figures"
con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
pd.set_option("display.precision", 3, "display.max_columns", 30, "display.width", 200)


def q(sql, params=None):
    return con.execute(sql, params).df()


METRO = q("select cbsa_code, split_part(metro_name, ',', 1) metro from gold.dim_metro")
METRO = METRO.set_index("cbsa_code")["metro"]
LATEST = q(
    "select max(month) m from gold.mart_metro_month where price_to_income is not null"
).m[0]
LATEST_12M = f"{(LATEST - pd.DateOffset(months=11)):%b %Y}–{LATEST:%b %Y}"

# Reference palette (dataviz skill): one highlight hue over gray context
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#c3c2b7", "#e8e7e3"
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "text.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.titlelocation": "left",
        "axes.titlesize": 10,
        "font.size": 9,
        "lines.linewidth": 2,
        "figure.dpi": 110,
    }
)


# ---------------------------------------------------------------- metrics
def price_to_income_change(start_year=2015):
    """Per metro: the start year's average price-to-income, ZHVI and CPI against the
    latest 12 months'. Income is ACS 5-year, so it lags about 2 years."""
    d = q(
        """
        select cbsa_code,
            avg(price_to_income) filter (year(month) = $y) start_p2i,
            avg(price_to_income) filter (month > $latest - interval 12 month) latest_p2i,
            avg(zhvi_usd) filter (year(month) = $y) start_zhvi,
            avg(zhvi_usd) filter (month > $latest - interval 12 month) latest_zhvi,
            avg(cpi) filter (year(month) = $y) start_cpi,
            avg(cpi) filter (month > $latest - interval 12 month) latest_cpi
        from gold.mart_metro_month group by all
        """,
        {"y": start_year, "latest": LATEST},
    )
    d["change"] = d.latest_p2i - d.start_p2i
    d.index = d.pop("cbsa_code").map(METRO).rename("metro")
    return d.sort_values("change", ascending=False)


def permits_vs_growth(permit_years=(2016, 2025), growth_years=(2015, 2025)):
    """Per metro: average yearly permits per 1,000 residents over permit_years
    (December rows hold the calendar year's trailing-12-month total) against ZHVI
    growth from December of growth_years[0] to December of growth_years[1].
    Returns the table and a numpy.polyfit line with its correlation."""
    d = q(
        """
        select cbsa_code,
            avg(permits_per_1000) filter (year(month) between $p0 and $p1) permits_per_1000,
            max(zhvi_usd) filter (year(month) = $g1)
                / max(zhvi_usd) filter (year(month) = $g0) - 1 zhvi_growth
        from gold.mart_metro_month where month(month) = 12 group by all
        """,
        dict(zip(("p0", "p1", "g0", "g1"), (*permit_years, *growth_years))),
    )
    d.index = d.pop("cbsa_code").map(METRO).rename("metro")
    slope, intercept = np.polyfit(d.permits_per_1000, d.zhvi_growth, 1)
    r = np.corrcoef(d.permits_per_1000, d.zhvi_growth)[0, 1]
    return d, {"slope": slope, "intercept": intercept, "r": r}


def quarterly():
    """Metro x QCEW quarter: average ZORI and CPI, the quarter's weekly wage and both
    year-over-year growths. Carried-forward months (no wage yet) are left out."""
    d = q(
        """
        select cbsa_code, wages_quarter as quarter, avg(zori_usd) zori_usd, avg(cpi) cpi,
            any_value(avg_weekly_wage_usd) wage_usd, avg(zori_yoy_growth) zori_yoy,
            any_value(avg_weekly_wage_yoy_growth) wage_yoy
        from gold.mart_metro_month where not wages_is_carried_forward
        group by all order by all
        """
    )
    d["metro"] = d.cbsa_code.map(METRO)
    return d


def rent_wage_gap(start="2015Q1"):
    """Per metro: ZORI and wage growth from the start quarter to the latest QCEW quarter,
    nominal and CPI-deflated. Both ends must be the same quarter of the year because
    QCEW wages are seasonal (Q4 bonuses)."""
    d = quarterly()
    end = d.quarter.max()
    assert start[-1] == end[-1], f"{start} and {end} are different quarters of the year"
    w = d[d.quarter.isin([start, end])].pivot(index="metro", columns="quarter")
    out = pd.DataFrame(
        {
            "rent_growth": w.zori_usd[end] / w.zori_usd[start] - 1,
            "wage_growth": w.wage_usd[end] / w.wage_usd[start] - 1,
            "inflation": w.cpi[end] / w.cpi[start] - 1,
        }
    )
    out["gap"] = out.rent_growth - out.wage_growth
    out.attrs["window"] = f"{start} to {end}"
    return out.sort_values("gap", ascending=False)


# ---------------------------------------------------------------- charts
def small_multiples(wide, order, titles, yfmt, zero=False):
    """One panel per metro: that metro in blue over all metros in gray.
    wide: index = x, one column per metro."""
    fig, axes = plt.subplots(3, 4, figsize=(11, 7), sharex=True, sharey=True)
    for ax, m in zip(axes.flat, order):
        for other in wide.columns:
            ax.plot(wide.index, wide[other], color=MUTED, lw=0.7)
        ax.plot(wide.index, wide[m], color=BLUE)
        if zero:
            ax.axhline(0, color=INK2, lw=0.8)
        ax.set_title(titles[m])
        ax.yaxis.set_major_formatter(yfmt)
    for ax in axes.flat[len(order) :]:
        ax.axis("off")
    return fig


def ranked_bars(s, label, xfmt, diverging=False):
    """Horizontal bars, largest on top, each labeled at its end. diverging colors
    positive bars red and negative bars blue."""
    s = s.sort_values()
    fig, ax = plt.subplots(figsize=(7, 0.38 * len(s) + 1.2))
    colors = [RED if v > 0 else BLUE for v in s] if diverging else BLUE
    ax.barh(s.index, s.values, color=colors, height=0.62)
    for y, v in enumerate(s.values):
        right = v >= 0
        ax.annotate(
            label.format(v),
            (v, y),
            xytext=(4 if right else -4, 0),
            textcoords="offset points",
            ha="left" if right else "right",
            va="center",
            color=INK,
        )
    ax.axvline(0, color=INK2, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(xfmt)
    ax.margins(x=0.12)
    return fig, ax


def save(fig, name, title, note):
    """Title the figure, add the source note under it and write docs/figures/<name>.png."""
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.text(0.01, 0, note, fontsize=7.5, color=INK2, va="top", wrap=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", dpi=150, bbox_inches="tight")
