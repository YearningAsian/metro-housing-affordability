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
BLUE, ORANGE, RED, AQUA = "#2a78d6", "#eb6834", "#e34948", "#1baf7a"
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
    latest 12 months'. Metro income is ACS 1-year, interpolated between releases
    and carried forward from the latest, so it lags about a year."""
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


# monthly cost of the typical home: principal and interest on ZHVI less `down`, 30-year
# fixed at that month's rate, plus property tax at the ACS effective rate when $taxes = 1
PAYMENT = """
    select cbsa_code, month, median_household_income_usd income,
        (1 - $down) * zhvi_usd * r / (1 - pow(1 + r, -360)) + $taxes * zhvi_usd * property_tax_rate / 12 payment
    from (select *, mortgage_rate_pct / 1200 r from gold.mart_metro_month)
"""


def mortgage_share_change(start_year=2015, down=0.10, taxes=True):
    """Per metro: the monthly payment on the typical home (PAYMENT; principal, interest
    and, with `taxes`, property tax) over median household income / 12, as the start
    year's average against the latest 12 months'. Leaves out insurance and HOA fees;
    ACS income lags about a year, so recent shares run a little high."""
    d = q(
        f"""
        with m as (select *, payment / (income / 12) share from ({PAYMENT}))
        select cbsa_code,
            avg(share) filter (year(month) = $y) start_share,
            avg(share) filter (month > $latest - interval 12 month and month <= $latest) latest_share
        from m group by all
        """,
        {"y": start_year, "latest": LATEST, "down": down, "taxes": int(taxes)},
    )
    d["change"] = d.latest_share - d.start_share
    d.index = d.pop("cbsa_code").map(METRO).rename("metro")
    return d.sort_values("latest_share", ascending=False)


def mortgage_share_split(down=0.10):
    """Per metro: the log change in the mortgage share (PAYMENT with taxes over income)
    split exactly into price (ZHVI), financing (rate and property tax per dollar
    borrowed) and income, for 2015 to 2021, 2021 to the latest 12 months, and 2015 to
    the latest 12 months. Each period is the mean of its monthly logs; a component's
    value is its log-point contribution (0.10 = about 10% higher share)."""
    d = q(
        """
        with m as (
            select cbsa_code, month,
                ln(zhvi_usd) price,
                ln((1 - $down) * r / (1 - pow(1 + r, -360)) + property_tax_rate / 12) financing,
                -ln(median_household_income_usd / 12) income
            from (select *, mortgage_rate_pct / 1200 r from gold.mart_metro_month)
        )
        select cbsa_code,
            case when year(month) = 2015 then '2015' when year(month) = 2021 then '2021' else 'latest' end period,
            avg(price) price, avg(financing) financing, avg(income) income
        from m
        where year(month) in (2015, 2021) or (month > $latest - interval 12 month and month <= $latest)
        group by all
        """,
        {"latest": LATEST, "down": down},
    ).set_index(["cbsa_code", "period"])
    out = []
    for start, end in (("2015", "2021"), ("2021", "latest"), ("2015", "latest")):
        w = d.xs(end, level="period") - d.xs(start, level="period")
        w["total"] = w.sum(axis=1)
        w["window"] = f"{start}-{end}"
        out.append(w)
    out = pd.concat(out).reset_index()
    out["metro"] = out.pop("cbsa_code").map(METRO)
    return out.set_index(["window", "metro"]).sort_index()


# lower bounds of the ACS B19001 income brackets (households_by_income)
BRACKETS = (
    np.array([0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100, 125, 150, 200]) * 1000
)


def share_above(income, households):
    """Share of households with income at or above `income`, linear within a bracket.
    shortcut: above $200k (the open top bracket) it returns the top bracket's share, an
    upper bound; fit a Pareto tail if a needed income ever passes $200k."""
    households = np.asarray(households, dtype=float)
    below = np.concatenate([[0], np.cumsum(households[:-1])]) / households.sum()
    return 1 - np.interp(income, BRACKETS, below)


def affordable_share(start_year=2015, down=0.10, burden=0.30):
    """Per metro: the income that keeps the typical home's monthly PAYMENT (with taxes)
    at `burden` of income, and the share of households who earn it. The start year uses
    its own ACS 1-year brackets and average payment; the latest 12 months use the
    latest vintage's brackets, which lag about a year."""
    d = q(
        f"""
        select cbsa_code,
            avg(payment) filter (year(month) = $y) start_payment,
            avg(payment) filter (month > $latest - interval 12 month and month <= $latest) latest_payment
        from ({PAYMENT}) group by all
        """,
        {"y": start_year, "latest": LATEST, "down": down, "taxes": 1},
    ).set_index("cbsa_code")
    h = q(
        """
        select cbsa_code, acs_vintage, households_by_income from gold.fct_income
        where geo_level = 'metro' and acs_vintage <= year($latest)
        """,
        {"latest": LATEST},
    )
    h = h[h.acs_vintage.isin([start_year, h.acs_vintage.max()])]
    h = h.pivot(index="cbsa_code", columns="acs_vintage", values="households_by_income")
    d["latest_vintage"] = h.columns.max()
    for when, vintage in (("start", start_year), ("latest", h.columns.max())):
        d[f"{when}_income_needed"] = d[f"{when}_payment"] * 12 / burden
        d[f"{when}_share"] = [
            share_above(need, h.loc[c, vintage])
            for c, need in d[f"{when}_income_needed"].items()
        ]
    d["change"] = d.latest_share - d.start_share
    d.index = d.index.map(METRO).rename("metro")
    return d.sort_values("latest_share")


# a bracket split evenly: half of the $50k-60k households are at $55k or more
assert abs(share_above(55_000, [0] * 9 + [1] + [0] * 6) - 0.5) < 1e-9


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
