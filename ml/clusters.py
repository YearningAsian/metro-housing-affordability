"""Phase 13: neighborhood clusters from each ZIP's last 12 months.

Six measures per ZIP over the 12 months to a window end: price growth, price-to-income, permits per 1,000 residents,
days on market, rent growth and net migration. They are clipped to the 1st-99th percentile and standardized, then
grouped with k-means. The scaler and centroids are fit on the latest window and reused for December 2019, so the
two assignments are comparable and show how ZIPs moved.

Writes ml.zip_clusters (zip, window end, cluster, name), docs/figures/cluster_maps.png and cluster_shares.png, and
prints the silhouette sweep, the Gaussian-mixture cross-check and the profiles for docs/clusters_report.md.
Run: uv run --group ml --group dev python -m ml.clusters
"""

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
K = 6
THEN = "2019-12-01"
MEASURES = {
    "price_growth": "12-month ZHVI growth (%)",
    "price_to_income": "price-to-income (years)",
    "permits_per_1000": "permits per 1,000 residents",
    "days_on_market": "median days on market",
    "rent_growth": "12-month ZORI growth (%)",
    "net_migration": "net migration per 1,000",
}
# shortcut: names were chosen by reading the September 2026 profiles; reread them and rename after a refit on
# new data (clusters are numbered by price growth, highest first)
NAMES = {
    0: "Pricey and still rising",
    1: "Growing in-migration suburbs",
    2: "Expensive fast-selling core",
    3: "Flat and typical",
    4: "Affordable with rising rents",
    5: "Building boom, prices slipping",
}
# reference categorical palette (dataviz skill), fixed order
PALETTE = [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
]


def window(con, end):
    """One row per ZIP with a ZHVI: the six measures over the 12 months to end; rent and days on market missing in
    a ZIP take its metro's median (rent_imputed, dom_imputed)."""
    d = con.execute(
        """
        select zip, any_value(cbsa_code) cbsa_code,
            100 * any_value(zhvi_yoy_growth) filter (month = $end) price_growth,
            avg(price_to_income) price_to_income,
            any_value(permits_per_1000) filter (month = $end) permits_per_1000,
            avg(median_days_on_market) days_on_market,
            100 * any_value(zori_yoy_growth) filter (month = $end) rent_growth,
            avg(net_migration_rate) net_migration
        from gold.mart_zip_month
        where month > $end::date - interval 12 month and month <= $end
        group by zip
        order by zip  -- k-means seeding depends on row order
        """,
        {"end": end},
    ).df()
    d = d.dropna(
        subset=["price_growth", "price_to_income", "permits_per_1000", "net_migration"]
    )
    for col, flag in [
        ("rent_growth", "rent_imputed"),
        ("days_on_market", "dom_imputed"),
    ]:
        d[flag] = d[col].isna()
        d[col] = d[col].fillna(d.groupby("cbsa_code")[col].transform("median"))
    return d.dropna(subset=list(MEASURES)).reset_index(drop=True)


def scale(d, bounds, scaler):
    return scaler.transform(
        d[list(MEASURES)].clip(bounds.loc[0.01], bounds.loc[0.99], axis=1)
    )


def fit(now):
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler

    bounds = now[list(MEASURES)].quantile([0.01, 0.99])
    scaler = StandardScaler().fit(
        now[list(MEASURES)].clip(bounds.loc[0.01], bounds.loc[0.99], axis=1)
    )
    x = scale(now, bounds, scaler)
    print("k  silhouette  GMM agreement (adjusted Rand)")
    models = {}
    for k in range(3, 9):
        models[k] = KMeans(k, n_init=20, random_state=SEED).fit(x)
        gmm = GaussianMixture(k, n_init=5, random_state=SEED).fit(x).predict(x)
        print(
            f"{k}  {silhouette_score(x, models[k].labels_):.3f}       "
            f"{adjusted_rand_score(models[k].labels_, gmm):.3f}"
        )
    return models, bounds, scaler, x


def relabel(km, now):
    """Cluster ids ordered by median price growth, highest first, so numbering is stable across reruns."""
    order = (
        now.groupby(km.labels_).price_growth.median().sort_values(ascending=False).index
    )
    return {old: new for new, old in enumerate(order)}


def profiles(now, labels):
    med = now.groupby(labels)[list(MEASURES)].median()
    z = (med - now[list(MEASURES)].median()) / now[list(MEASURES)].std()
    med["zips"] = pd.Series(labels).value_counts()
    return med.round(1), z.round(2)


def main(explore=False):
    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
    end = con.sql(
        "select max(month) from gold.mart_zip_month where zhvi_usd is not null"
    ).fetchall()[0][0]
    now, then = window(con, end), window(con, THEN)
    names = con.sql(
        "select cbsa_code, split_part(metro_name, ',', 1) metro from gold.dim_metro"
    ).df()
    names = names.set_index("cbsa_code").metro
    con.close()
    print(
        f"{len(now):,} ZIPs to {end:%b %Y}; rent imputed for {now.rent_imputed.mean():.0%}"
    )
    models, bounds, scaler, _ = fit(now)
    if explore:
        for k in range(3, 9):
            ids = relabel(models[k], now)
            med, z = profiles(now, np.vectorize(ids.get)(models[k].labels_))
            print(f"\nk={k}\n{med.to_string()}\n{z.to_string()}")
        return
    km = models[K]
    ids = relabel(km, now)
    now["cluster"] = np.vectorize(ids.get)(km.labels_)
    then["cluster"] = np.vectorize(ids.get)(km.predict(scale(then, bounds, scaler)))
    med, z = profiles(now, now.cluster)
    print(
        f"\nprofiles (medians), k={K}\n{med.to_string()}\n\nz-scores of the medians\n{z.to_string()}"
    )
    moved = then[["zip", "cluster"]].merge(
        now[["zip", "cluster"]], on="zip", suffixes=("_2019", "_now")
    )
    print("\nZIPs by cluster, December 2019 (rows) to now (columns)")
    print(pd.crosstab(moved.cluster_2019, moved.cluster_now, margins=True).to_string())
    print(
        f"stayed in the same cluster: {(moved.cluster_2019 == moved.cluster_now).mean():.0%}"
    )
    share = (
        pd.crosstab(now.cbsa_code.map(names), now.cluster, normalize="index")
        .mul(100)
        .round(0)
    )
    print(f"\nshare of ZIPs by metro (%)\n{share.to_string()}")
    if NAMES:
        save(now, then, end, names)


def save(now, then, end, names):
    clusters = pd.concat(
        [now.assign(window_end=end), then.assign(window_end=pd.Timestamp(THEN))]
    )
    clusters["cluster_name"] = clusters.cluster.map(NAMES)
    cols = [
        "zip",
        "cbsa_code",
        "window_end",
        "cluster",
        "cluster_name",
        *MEASURES,
        "rent_imputed",
        "dom_imputed",
    ]
    clusters = clusters[cols]
    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"))
    con.execute("create schema if not exists ml")
    con.execute("create or replace table ml.zip_clusters as select * from clusters")
    con.close()
    charts(now, end, names)


def charts(now, end, names):
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    shapes = json.loads((ROOT / "data" / "export" / "zip_shapes.geojson").read_text())
    rings = {}
    for f in shapes["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        rings[f["properties"]["zip"]] = [p[0] for p in polys]
    color = dict(zip(now.zip, now.cluster.map(lambda c: PALETTE[c])))

    metros = names.sort_values()
    fig, axes = plt.subplots(3, 4, figsize=(12, 9.5))
    for ax, (code, metro) in zip(axes.flat, metros.items()):
        zips = [z for z in now.zip[now.cbsa_code == code] if z in rings]
        polys = [r for z in zips for r in rings[z]]
        colors = [color[z] for z in zips for _ in rings[z]]
        ax.add_collection(
            PolyCollection(
                polys, facecolors=colors, edgecolors="#fcfcfb", linewidths=0.3
            )
        )
        ax.autoscale_view()
        ax.set_aspect(
            1 / np.cos(np.radians(np.mean([p[1] for r in polys[:50] for p in r])))
        )
        ax.set_title(metro)
        ax.axis("off")
    legend = axes.flat[-1]
    legend.axis("off")
    for c, name in NAMES.items():
        legend.scatter([], [], s=80, marker="s", color=PALETTE[c], label=name)
    legend.legend(loc="center left", frameon=False, title="Cluster")
    fig.suptitle(f"Neighborhood clusters, 12 months to {end:%b %Y}", x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "figures" / "cluster_maps.png", dpi=130)

    share = pd.crosstab(now.cbsa_code.map(names), now.cluster, normalize="index").mul(
        100
    )
    share = share.loc[share[0].sort_values().index]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    left = np.zeros(len(share))
    for c in share.columns:
        ax.barh(
            share.index,
            share[c],
            left=left,
            color=PALETTE[c],
            edgecolor="#fcfcfb",
            linewidth=2,
            label=NAMES[c],
        )
        left += share[c]
    ax.set_xlabel("share of the metro's ZIPs (%)")
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    ax.set_title(f"Cluster mix by metro, sorted by the share of '{NAMES[0]}'")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "figures" / "cluster_shares.png", dpi=150)


if __name__ == "__main__":
    import sys

    main(explore="--explore" in sys.argv)
