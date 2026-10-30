"""Phase 16: the deck's charts at 1920x1080 with large labels, from the same metrics as the Phase 9 notebooks. No
titles: each slide's headline states the finding. Writes docs/figures/deck/*.png.
Run: uv run python notebooks/deck_charts.py
"""

import matplotlib.pyplot as plt
from common import (
    BLUE,
    FIGURES,
    INK,
    INK2,
    MUTED,
    permits_vs_growth,
    price_to_income_change,
    ranked_bars,
    rent_wage_gap,
)
from matplotlib.ticker import FuncFormatter, PercentFormatter

OUT = FIGURES / "deck"
plt.rcParams.update({"font.size": 26, "figure.dpi": 120, "axes.linewidth": 1.5})


def save(fig, name):
    fig.set_size_inches(16, 9)
    fig.tight_layout(pad=1.2)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=120)  # 1920x1080
    plt.close(fig)


p2i = price_to_income_change()
fig, ax = ranked_bars(p2i.change, "+{:.2f}", FuncFormatter(lambda v, _: f"{v:+.1f}"))
ax.set_xlabel("Change in price-to-income, years of median income")
save(fig, "price_to_income_change")

gap = rent_wage_gap()
fig, ax = ranked_bars(
    gap.gap * 100, "{:+.0f} pp", FuncFormatter(lambda v, _: f"{v:+.0f}"), diverging=True
)
ax.set_xlabel("Rent growth minus wage growth, percentage points")
ax.margins(x=0.2)  # room for the end labels
save(fig, "rent_minus_wage")

d, fit = permits_vs_growth()
fig, ax = plt.subplots()
ax.scatter(
    d.permits_per_1000, d.zhvi_growth, s=260, color=MUTED, edgecolor=INK2, zorder=3
)
austin = d.loc["Austin"]
ax.scatter(austin.permits_per_1000, austin.zhvi_growth, s=420, color=BLUE, zorder=4)
for metro, row in d.iterrows():
    ax.annotate(
        metro,
        (row.permits_per_1000, row.zhvi_growth),
        xytext=(
            14,
            {"Atlanta": 16, "Seattle": -20}.get(metro, 0),
        ),  # those two sit on top of each other
        textcoords="offset points",
        va="center",
        color=INK if metro == "Austin" else INK2,
        fontweight="bold" if metro == "Austin" else "normal",
        fontsize=22,
    )
x = d.permits_per_1000.sort_values()
ax.plot(x, fit["slope"] * x + fit["intercept"], color=INK2, lw=2, ls="--", zorder=2)
ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
ax.set_xlabel("Housing units permitted per 1,000 residents a year, 2016-2025")
ax.set_ylabel("Home value growth, 2015-2025")
ax.margins(x=0.18, y=0.1)
save(fig, "permits_vs_growth")
print(
    f"wrote {len(list(OUT.glob('*.png')))} charts to {OUT}; permits r = {fit['r']:.2f}"
)
