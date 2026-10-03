"""Exploratory Data Analysis for the India crop production dataset.

Input : CSV with columns State_Name, District_Name, Crop_Year, Season, Crop, Area, Production
        (the "Crop Production in India" dataset compiled from data.gov.in, a.k.a. apy.csv)
Output: outputs/results.json, outputs/figures/*.png, outputs/tables/*.csv

Usage : python src/eda.py --input data/raw/crop_production.csv
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import MaxNLocator
from scipy import stats

REQUIRED = ["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"]
sns.set_theme(style="whitegrid", context="notebook")


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def load_and_clean(path):
    raw = pd.read_csv(path)
    missing_cols = [c for c in REQUIRED if c not in raw.columns]
    if missing_cols:
        raise SystemExit(f"Input is missing expected columns: {missing_cols}\nFound: {list(raw.columns)}")
    log = {"rows_raw": int(len(raw)), "missing_per_column": raw[REQUIRED].isna().sum().astype(int).to_dict()}

    df = raw[REQUIRED].copy()
    for c in ["State_Name", "District_Name", "Season", "Crop"]:
        df[c] = df[c].astype("string").str.strip()
    log["duplicates"] = int(df.duplicated().sum())
    df = df.drop_duplicates()
    df = df.dropna(subset=["Area", "Production", "Crop", "State_Name", "Season", "Crop_Year"])
    log["rows_after_dropna"] = int(len(df))
    log["nonpositive_area"] = int((df["Area"] <= 0).sum())
    df = df[df["Area"] > 0]
    # Coconut is recorded in nuts, every other crop in tonnes: exclude to avoid mixing units.
    is_coconut = df["Crop"].str.contains("coconut", case=False, na=False)
    log["coconut_rows_excluded"] = int(is_coconut.sum())
    df = df[~is_coconut].copy()
    df["Crop_Year"] = df["Crop_Year"].astype(int)
    df["Yield"] = df["Production"] / df["Area"]
    log["rows_final"] = int(len(df))
    return df.reset_index(drop=True), log


def main(args):
    out = Path(args.outdir)
    figdir, tabdir = out / "figures", out / "tables"
    figdir.mkdir(parents=True, exist_ok=True)
    tabdir.mkdir(parents=True, exist_ok=True)

    df, clean_log = load_and_clean(args.input)
    R = {"input_file": Path(args.input).name, "cleaning": clean_log}
    R["overview"] = {
        "rows": len(df), "states": int(df["State_Name"].nunique()), "districts": int(df["District_Name"].nunique()),
        "crops": int(df["Crop"].nunique()), "seasons": sorted(df["Season"].unique().tolist()),
        "year_min": int(df["Crop_Year"].min()), "year_max": int(df["Crop_Year"].max()),
    }

    # ---- Fig 1: missing values in raw data
    miss = pd.Series(clean_log["missing_per_column"])
    fig, ax = plt.subplots(figsize=(7, 3.5))
    sns.barplot(x=miss.values, y=miss.index, ax=ax, color="#4c9f70")
    ax.set(title="Missing values per column (raw data)", xlabel="Number of missing rows", ylabel="")
    save(fig, figdir / "01_missing_values.png")

    # ---- Descriptive statistics
    num = df[["Area", "Production", "Yield"]]
    desc = num.describe().T
    desc["skew"] = num.skew()
    desc["kurtosis"] = num.kurt()
    desc["median"] = num.median()
    desc.round(3).to_csv(tabdir / "descriptive_statistics.csv")
    R["describe"] = desc.round(3).reset_index().rename(columns={"index": "variable"}).to_dict("records")

    # ---- Fig 2: distributions raw vs log10
    fig, axes = plt.subplots(2, 3, figsize=(12, 6))
    for j, col in enumerate(["Area", "Production", "Yield"]):
        sns.histplot(df[col], bins=60, ax=axes[0, j], color="#c0803a")
        axes[0, j].set(title=f"{col} (raw)", xlabel=col)
        sns.histplot(np.log10(df[col].clip(lower=1e-6)), bins=60, ax=axes[1, j], color="#4c9f70")
        axes[1, j].set(title=f"{col} (log10)", xlabel=f"log10({col})")
    save(fig, figdir / "02_distributions.png")

    # ---- Outliers: IQR rule on log yield within each crop
    def iqr_flags(s):
        ls = np.log10(s.clip(lower=1e-6))
        q1, q3 = ls.quantile([0.25, 0.75])
        return (ls < q1 - 1.5 * (q3 - q1)) | (ls > q3 + 1.5 * (q3 - q1))
    flags = df.groupby("Crop", group_keys=False)["Yield"].apply(iqr_flags)
    R["outliers"] = {"yield_outlier_rows": int(flags.sum()), "share_pct": round(100 * float(flags.mean()), 2)}

    # ---- Year coverage (partial years distort trends)
    yr_counts = df.groupby("Crop_Year").size()
    valid_years = yr_counts[yr_counts >= 0.5 * yr_counts.median()].index.tolist()
    R["year_coverage"] = {"valid_years": [int(y) for y in valid_years],
                          "dropped_years": [int(y) for y in yr_counts.index if y not in valid_years]}
    dv = df[df["Crop_Year"].isin(valid_years)]

    # ---- Fig 3: national production trend
    tot = dv.groupby("Crop_Year")["Production"].sum() / 1e6
    sl = stats.linregress(tot.index, tot.values)
    R["trend_total"] = {"first_year": int(tot.index.min()), "last_year": int(tot.index.max()),
                        "first_mt": round(float(tot.iloc[0]), 2), "last_mt": round(float(tot.iloc[-1]), 2),
                        "slope_mt_per_year": round(float(sl.slope), 3), "p_value": float(sl.pvalue),
                        "r2": round(float(sl.rvalue ** 2), 3)}
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(tot.index, tot.values, marker="o", color="#2d6a4f", label="Total production")
    ax.plot(tot.index, sl.intercept + sl.slope * tot.index, "--", color="#b23a48", label="Linear trend")
    ax.set(title="Total recorded crop production by year (coconut excluded)", xlabel="Crop year",
           ylabel="Million tonnes")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    save(fig, figdir / "03_production_trend.png")

    # ---- Fig 4: top crops by production + concentration
    crop_tot = df.groupby("Crop")["Production"].sum().sort_values(ascending=False)
    share = crop_tot / crop_tot.sum() * 100
    crop_tot.head(20).to_csv(tabdir / "top_crops_production.csv")
    top10 = crop_tot.head(10)
    R["top_crops"] = [{"crop": k, "production_mt": round(v / 1e6, 2), "share_pct": round(float(share[k]), 2)}
                      for k, v in top10.items()]
    R["top3_share_pct"] = round(float(share.head(3).sum()), 1)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(x=top10.values / 1e6, y=top10.index, ax=ax, color="#2d6a4f")
    ax.set(title="Top 10 crops by cumulative production", xlabel="Million tonnes", ylabel="")
    save(fig, figdir / "04_top_crops.png")

    # ---- Fig 5: top states
    st_tot = df.groupby("State_Name")["Production"].sum().sort_values(ascending=False)
    st_share = st_tot / st_tot.sum() * 100
    R["top_states"] = [{"state": k, "share_pct": round(float(st_share[k]), 2)} for k in st_tot.head(10).index]
    R["top5_state_share_pct"] = round(float(st_share.head(5).sum()), 1)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(x=st_share.head(10).values, y=st_share.head(10).index, ax=ax, color="#c0803a")
    ax.set(title="Top 10 states: share of cumulative production", xlabel="% of total", ylabel="")
    save(fig, figdir / "05_top_states.png")

    # ---- Fig 6: yield by season + Kruskal-Wallis
    seas = df.groupby("Season")["Yield"].agg(["count", "median", "mean"]).sort_values("median", ascending=False)
    seas.round(3).to_csv(tabdir / "yield_by_season.csv")
    groups = [g["Yield"].values for _, g in df.groupby("Season") if len(g) >= 30]
    H, p = stats.kruskal(*groups) if len(groups) > 1 else (np.nan, np.nan)
    R["season"] = {"table": seas.round(3).reset_index().to_dict("records"),
                   "kruskal_H": None if np.isnan(H) else round(float(H), 2),
                   "kruskal_p": None if np.isnan(p) else float(p)}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.boxplot(data=df, x="Season", y="Yield", order=seas.index, ax=ax, color="#9bc4a8", showfliers=False)
    ax.set(title="Yield (tonnes/ha) by season (outliers hidden)", xlabel="", ylabel="Tonnes per hectare")
    save(fig, figdir / "06_yield_by_season.png")

    # ---- Fig 7: area vs production (log-log) + elasticity
    rho, rp = stats.spearmanr(df["Area"], df["Production"])
    ll = stats.linregress(np.log10(df["Area"]), np.log10(df["Production"].clip(lower=1e-6)))
    R["area_production"] = {"spearman_rho": round(float(rho), 3), "spearman_p": float(rp),
                            "loglog_slope": round(float(ll.slope), 3), "loglog_r2": round(float(ll.rvalue ** 2), 3)}
    samp = df.sample(min(len(df), 20000), random_state=42)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(np.log10(samp["Area"]), np.log10(samp["Production"].clip(lower=1e-6)), s=4, alpha=0.25, color="#2d6a4f")
    xs = np.linspace(np.log10(df["Area"]).min(), np.log10(df["Area"]).max(), 50)
    ax.plot(xs, ll.intercept + ll.slope * xs, color="#b23a48", label=f"slope = {ll.slope:.2f}")
    ax.set(title="Area vs production (log-log, up to 20k-row sample)", xlabel="log10(Area, ha)",
           ylabel="log10(Production, t)")
    ax.legend()
    save(fig, figdir / "07_area_vs_production.png")

    # ---- Fig 8: correlation heatmap (log scale + year)
    cm = pd.DataFrame({"log Area": np.log10(df["Area"]), "log Production": np.log10(df["Production"].clip(lower=1e-6)),
                       "log Yield": np.log10(df["Yield"].clip(lower=1e-6)),
                       "Year": df["Crop_Year"]}).corr(method="spearman")
    cm.round(3).to_csv(tabdir / "correlation_matrix.csv")
    R["corr_year_yield"] = round(float(cm.loc["Year", "log Yield"]), 3)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="RdYlGn", vmin=-1, vmax=1, ax=ax)
    ax.set_title("Spearman correlation matrix")
    save(fig, figdir / "08_correlation_heatmap.png")

    # ---- Fig 9: yield trends for the top-5 crops (median district yield per year)
    top5 = list(crop_tot.head(5).index)
    R["yield_trends"] = []
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for c in top5:
        s = dv[dv["Crop"] == c].groupby("Crop_Year")["Yield"].median()
        if len(s) < 5:
            continue
        r = stats.linregress(s.index, s.values)
        R["yield_trends"].append({"crop": c, "slope_per_year": round(float(r.slope), 4),
                                  "pct_per_year": round(float(100 * r.slope / s.mean()), 2),
                                  "p_value": float(r.pvalue), "years": len(s)})
        ax.plot(s.index, s.values, marker=".", label=c)
    ax.set(title="Median district yield over time, top-5 crops (log scale)", xlabel="Crop year",
           ylabel="Tonnes per hectare (log scale)", yscale="log")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(fontsize=8)
    save(fig, figdir / "09_yield_trends.png")

    # ---- Yield stability (CV of annual median yield) for top-10 crops
    cv_rows = []
    for c in top10.index:
        s = dv[dv["Crop"] == c].groupby("Crop_Year")["Yield"].median()
        if len(s) >= 5 and s.mean() > 0:
            cv_rows.append({"crop": c, "cv_pct": round(float(100 * s.std() / s.mean()), 1),
                            "mean_yield": round(float(s.mean()), 2)})
    cv = pd.DataFrame(cv_rows, columns=["crop", "cv_pct", "mean_yield"]).sort_values("cv_pct")
    cv.to_csv(tabdir / "yield_stability.csv", index=False)
    R["stability"] = cv.to_dict("records")
    if len(cv):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.barplot(data=cv, x="cv_pct", y="crop", ax=ax, color="#c0803a")
        ax.set(title="Year-to-year yield variability (coefficient of variation)",
               xlabel="CV of annual median yield (%)", ylabel="")
        save(fig, figdir / "10_yield_stability.png")

    # ---- Fig 11: state x crop median yield heatmap
    ts, tc = list(st_tot.head(8).index), list(crop_tot.head(8).index)
    piv = df[df["State_Name"].isin(ts) & df["Crop"].isin(tc)].pivot_table(
        index="State_Name", columns="Crop", values="Yield", aggfunc="median").reindex(index=ts, columns=tc)
    piv.round(2).to_csv(tabdir / "state_crop_median_yield.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.heatmap(piv, annot=True, fmt=".1f", cmap="YlGn", ax=ax, cbar_kws={"label": "t/ha"})
    ax.set(title="Median yield: top states x top crops", xlabel="", ylabel="")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    save(fig, figdir / "11_state_crop_yield.png")
    flat = piv.stack().dropna()
    if len(flat):
        R["state_crop_extremes"] = {
            "best": {"state": flat.idxmax()[0], "crop": flat.idxmax()[1], "yield": round(float(flat.max()), 2)},
            "worst": {"state": flat.idxmin()[0], "crop": flat.idxmin()[1], "yield": round(float(flat.min()), 2)}}

    with open(out / "results.json", "w") as f:
        json.dump(R, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"Done. {R['overview']['rows']:,} clean rows analysed -> {out}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw/crop_production.csv")
    ap.add_argument("--outdir", default="outputs")
    main(ap.parse_args())
