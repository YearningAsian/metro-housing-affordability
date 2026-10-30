"""Phase 14: which ZIPs land in their metro's top 20% of home value growth over the next 12 months?

Classifies target_top20 from ml.features_zip_month. Each evaluation fit sees only rows whose outcome was published
before its period began: rows known by January 2023 for the 2023 validation months and by January 2024 for the
2024-2025 test months. Models: last year's growth as a baseline score, logistic regression, and LightGBM with the
positive class weighted 4:1. Explanations are LightGBM's TreeSHAP values (pred_contrib), in log-odds.

Draws docs/figures/hot_zips_*.png and prints the metrics and the current top flags for docs/hot_zips_report.md. The
monthly scores and flags go to ml.predictions through ml/train.py.
Run: uv run --group ml --group dev python -m ml.hot_zips
"""

import pandas as pd

from ml.forecast import ROOT, features, fit_lgbm, known_by, load

TOP = 20  # flagged ZIPs per month for the headline precision
WEIGHT = 4  # positive class weight: 80% negatives to 20% positives
FITS = {
    "validate": "2023-01-01",
    "test": "2024-01-01",
}  # each period's model trains on rows known by this date
BLUE, RED, GRAY, INK = "#2a78d6", "#e34948", "#c3c2b7", "#52514e"


def fit_logit(train, cols):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    return model.fit(train[cols], train.target_top20.astype(int))


def fit_classifier(train, cols):
    return fit_lgbm(
        train, cols, objective="binary", label="target_top20", scale_pos_weight=WEIGHT
    )


def flag(d, col):
    """True for the top 20% of each metro's ZIPs by score that month."""
    return d.groupby(["cbsa_code", "month"], observed=True)[col].rank(pct=True) > 0.8


def metrics(d, col):
    from sklearn.metrics import average_precision_score

    top = d.sort_values(col, ascending=False).groupby("month").head(TOP)
    return {
        f"precision, top {TOP} a month": top.target_top20.mean(),
        "precision, top 20% per metro": d.target_top20[flag(d, col)].mean(),
        "PR-AUC": average_precision_score(d.target_top20.astype(int), d[col]),
    }


def evaluate(zips, cols, numeric):
    rows, scored = {}, {}
    for split, date in FITS.items():
        train = known_by(zips, pd.Timestamp(date))
        d = zips[(zips.split == split) & zips.target_top20.notna()].copy()
        # ZIPs with under a year of ZHVI get a neutral baseline score: their metro's median that month
        d["baseline"] = d.zhvi_growth_12m.fillna(
            d.groupby(["cbsa_code", "month"], observed=True).zhvi_growth_12m.transform(
                "median"
            )
        )
        d["logit"] = fit_logit(train, numeric).predict_proba(d[numeric])[:, 1]
        model = fit_classifier(train, cols)
        d["lgbm"] = model.predict(d[cols])
        print(
            f"{split}: trained on {len(train):,} rows, scored {len(d):,} ZIP-months in {d.month.nunique()} months"
        )
        for m in ["baseline", "logit", "lgbm"]:
            rows[(split, m)] = metrics(d, m)
        scored[split] = (d, model)
    table = pd.DataFrame(rows).T.round(3)
    table.loc[("both", "base rate"), :] = [0.2, 0.2, 0.2]
    return table, scored


def charts(test, test_model, model, cols, latest, names):
    """Calibration and global SHAP on the test months (test_model); single-ZIP SHAP on the latest scores (model)."""
    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve

    fig, ax = plt.subplots(figsize=(5, 4.2))
    ax.plot(
        [0, 1],
        [0, 1],
        color=GRAY,
        linestyle="--",
        linewidth=1,
        label="perfectly calibrated",
    )
    for m, color, label in [
        ("logit", INK, "logistic regression"),
        ("lgbm", BLUE, "LightGBM, class-weighted"),
    ]:
        true, pred = calibration_curve(
            test.target_top20.astype(int), test[m], n_bins=10, strategy="quantile"
        )
        ax.plot(
            pred, true, color=color, linewidth=2, marker="o", markersize=5, label=label
        )
    ax.set_xlabel("predicted probability")
    ax.set_ylabel("share that landed in the top 20%")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Calibration on the 2024-2025 test months", fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "figures" / "hot_zips_calibration.png", dpi=150)

    shap = pd.DataFrame(
        test_model.predict(test[cols], pred_contrib=True)[:, :-1], columns=cols
    )
    imp = shap.abs().mean().sort_values().tail(12)
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.barh(imp.index, imp, color=BLUE, height=0.7)
    ax.set_xlabel("mean |SHAP value| (log-odds)")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "What drives the hot-ZIP score, 2024-2025 test months", fontsize=10, loc="left"
    )
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "figures" / "hot_zips_shap_global.png", dpi=150)

    # the top-scored ZIP in each of the three metros with the highest top scores
    picks = (
        latest.sort_values("score", ascending=False)
        .drop_duplicates("cbsa_code")
        .head(3)
    )
    contrib = model.predict(picks[cols], pred_contrib=True)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    explained = []
    for ax, (_, row), c in zip(axes, picks.iterrows(), contrib, strict=True):
        s = pd.Series(c[:-1], index=cols)
        s = s[s.abs().sort_values().tail(8).index]
        labels = [f"{f} = {fmt(row[f])}" for f in s.index]
        ax.barh(labels, s, color=[RED if v > 0 else BLUE for v in s], height=0.7)
        ax.axvline(0, color=INK, linewidth=0.6)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_title(
            f"ZIP {row.zip}, {names[row.cbsa_code]}: score {row.score:.2f}",
            fontsize=9,
            loc="left",
        )
        ax.set_xlabel("push toward hot (red) or not (blue), log-odds", fontsize=8)
        explained.append((row.zip, names[row.cbsa_code], row.score, c[-1], s[::-1]))
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "figures" / "hot_zips_shap_zips.png", dpi=150)
    return imp[::-1], explained


def fmt(v):
    if pd.isna(v):
        return "missing"
    return f"{v:.3g}" if isinstance(v, int | float) else str(v)


def main():
    zips, _, names = load()
    cols = features(zips)
    numeric = [c for c in cols if c != "cbsa_code"]
    pd.set_option("display.width", 200)
    table, scored = evaluate(zips, cols, numeric)
    print(f"\n{table.to_string()}")
    test, test_model = scored["test"]
    by_metro = (
        test.assign(hot=flag(test, "lgbm"))
        .query("hot")
        .groupby("cbsa_code", observed=True)
        .target_top20.mean()
    )
    print(
        f"\nLightGBM precision, top 20% per metro, test, by metro\n{by_metro.rename(names).round(3).to_string()}"
    )

    # the model the monthly run (ml/train.py) fits, scoring the latest month for the single-ZIP explanations
    model = fit_classifier(zips[zips.target_top20.notna()], cols)
    latest = zips[zips.month == zips.month.max()].copy()
    latest["score"] = model.predict(latest[cols])
    latest["flagged"] = flag(latest, "score")
    imp, explained = charts(test, test_model, model, cols, latest, names)
    print(f"\nmean |SHAP|, test\n{imp.round(3).to_string()}")
    for z, metro, score, base, s in explained:
        print(
            f"\nZIP {z} ({metro}), score {score:.3f}, base value {base:.3f}\n{s.round(3).to_string()}"
        )

    hot = latest.assign(cbsa_code=latest.cbsa_code.astype(str))
    top = hot[hot.flagged].sort_values("score", ascending=False)
    print(
        f"\n{hot.flagged.sum()} of {len(hot)} ZIPs flagged for {hot.month.max():%b %Y}; top 5 per metro:"
    )
    top5 = (
        top.groupby("cbsa_code").head(5).assign(metro=lambda t: t.cbsa_code.map(names))
    )
    print(
        top5.sort_values(["metro", "score"], ascending=[True, False])[
            ["metro", "zip", "score"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
