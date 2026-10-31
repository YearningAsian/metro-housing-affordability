"""Phase 17: the affordability ranking as a bar chart race for the video. Each frame ranks the 11 metros by
price-to-income (years of median income to buy the typical home), January 2015 to the latest month, with values
and ranks interpolated between months so bars glide past each other. Needs ffmpeg on PATH.
Writes data/video/affordability_race.mp4 (1920x1080), or affordability_race_vertical.mp4 (1080x1920) with --vertical.
Run: uv run python notebooks/bar_race.py [--vertical]
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
from common import BLUE, INK, INK2, METRO, MUTED, ORANGE, ROOT, q
from matplotlib.animation import FFMpegWriter

VERTICAL = "--vertical" in sys.argv
STEPS, FPS, HOLD = (
    4,
    30,
    3,
)  # frames per month, frames per second, seconds held on the last month
HIGHLIGHT = {
    "Seattle": BLUE,
    "Austin": ORANGE,
}  # largest and smallest rise since 2015 (findings Q1)
OUT = ROOT / "data" / "video"

d = q(
    """select cbsa_code, month, price_to_income from gold.mart_metro_month
    where month >= '2015-01-01' and price_to_income is not null order by month"""
)
wide = d.pivot(index="month", columns="cbsa_code", values="price_to_income").ffill()
wide = wide.dropna().rename(columns=METRO)  # months where every metro has a value
ranks = wide.rank(axis=1, method="first")  # 1 = most affordable, drawn at the bottom

# Linear interpolation between months; the last month repeats for the hold
n = len(wide)
t = np.append(np.arange((n - 1) * STEPS + 1) / STEPS, np.full(HOLD * FPS, n - 1.0))
x = np.arange(n)
vals = np.column_stack([np.interp(t, x, wide[m]) for m in wide.columns])
ys = np.column_stack([np.interp(t, x, ranks[m]) for m in wide.columns])
xmax = wide.max().max() * 1.12

plt.rcParams.update({"font.size": 30 if VERTICAL else 26, "axes.linewidth": 1.5})
fig, ax = plt.subplots(figsize=(9, 16) if VERTICAL else (16, 9), dpi=120)
fig.subplots_adjust(
    left=0.05,
    right=0.97,
    top=0.78 if VERTICAL else 0.84,
    bottom=0.14 if VERTICAL else 0.06,
)


def draw(i):
    ax.clear()
    colors = [HIGHLIGHT.get(m, MUTED) for m in wide.columns]
    ax.barh(ys[i], vals[i], height=0.78, color=colors)
    for m, v, y in zip(wide.columns, vals[i], ys[i]):
        bold = "bold" if m in HIGHLIGHT else "normal"
        ink = "#ffffff" if m in HIGHLIGHT else INK  # white inside the saturated bars
        ax.text(
            v - xmax * 0.01, y, m, ha="right", va="center", color=ink, fontweight=bold
        )
        ax.text(v + xmax * 0.01, y, f"{v:.1f}", ha="left", va="center", color=INK2)
    month = wide.index[round(min(t[i], n - 1))]
    ax.set_xlim(0, xmax)
    ax.set_ylim(0.4, len(wide.columns) + 0.6)
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.spines[["left", "top", "right"]].set_visible(False)
    # Landscape: the month sits in the empty lower right; the phone frame has no room there, so it goes under the axis
    ax.text(
        0.99,
        -0.07 if VERTICAL else 0.02,
        f"{month:%b %Y}",
        transform=ax.transAxes,
        ha="right",
        va="top" if VERTICAL else "bottom",
        fontsize=64,
        fontweight="bold",
        color=MUTED,
    )


br = "\n" if VERTICAL else " "  # the phone frame needs the titles on two lines
fig.text(
    0.05,
    0.94,
    f"Years of median income{br}to buy the typical home",
    fontsize=34 if VERTICAL else 32,
    fontweight="bold",
    color=INK,
    va="top" if VERTICAL else "baseline",
)
fig.text(
    0.05,
    0.86 if VERTICAL else 0.885,
    f"Least affordable on top.{br}Zillow home value index over{br}ACS 5-year median"
    " household income",
    fontsize=20,
    color=INK2,
    va="top" if VERTICAL else "baseline",
    wrap=True,
)

OUT.mkdir(parents=True, exist_ok=True)
path = OUT / f"affordability_race{'_vertical' if VERTICAL else ''}.mp4"
writer = FFMpegWriter(fps=FPS, bitrate=6000, extra_args=["-pix_fmt", "yuv420p"])
with writer.saving(fig, str(path), dpi=120):
    for i in range(len(t)):
        draw(i)
        writer.grab_frame()
first, last = wide.iloc[0], wide.iloc[-1]
print(
    f"wrote {path} ({len(t)} frames, {len(t) / FPS:.0f} s), {wide.index[0]:%b %Y} to {wide.index[-1]:%b %Y}"
)
print(
    "least affordable first:",
    first.idxmax(),
    f"{first.max():.2f}",
    "->",
    last.idxmax(),
    f"{last.max():.2f}",
)
