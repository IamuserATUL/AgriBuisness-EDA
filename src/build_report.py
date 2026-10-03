"""Builds reports/Agribusiness_EDA_Report.docx from outputs/results.json and outputs/figures/*.png.

Every number and interpretive sentence is derived from results.json, so the report always matches the data
you ran. Usage: python src/build_report.py
"""
import argparse
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

DATASET_URL = "https://www.kaggle.com/datasets/abhinand05/crop-production-in-india"
SOURCE_NOTE = "Government of India open data (data.gov.in), compiled on Kaggle as 'Crop Production in India'"


def fmt(n, d=0):
    return f"{n:,.{d}f}"


def sig(p):
    return "statistically significant (p < 0.05)" if p is not None and p < 0.05 else "not statistically significant at the 5% level"


def table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
        for r in t.rows[0].cells[i].paragraphs[0].runs:
            r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()


def figure(doc, figdir, name, caption, width=6.0):
    p = figdir / name
    if not p.exists():
        return
    doc.add_picture(str(p), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.runs[0].italic = True
    c.runs[0].font.size = Pt(9)


def bullets(doc, items):
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def build(R, figdir, out_path):
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    o, cl = R["overview"], R["cleaning"]

    # ---------- Title
    t = doc.add_heading("Exploratory Data Analysis and Visualization for Agribusiness Insights", 0)
    doc.add_paragraph("Week 3 Task: Crop performance, production trends and input (land) utilization in India")

    if "SYNTHETIC" in R["input_file"].upper():
        w = doc.add_paragraph()
        r = w.add_run("WARNING: this report was generated from SYNTHETIC test data. None of the findings below are real. "
                      "Re-run the pipeline on the real dataset.")
        r.bold = True
        r.font.color.rgb = RGBColor(0xB2, 0x3A, 0x48)

    # ---------- 1 Objective
    doc.add_heading("1. Objective", 1)
    doc.add_paragraph(
        "The objective is an in-depth exploratory data analysis (EDA) of agribusiness data from a publicly available "
        "source. The analysis looks for patterns, trends and relationships using descriptive statistics and "
        "visualizations, then proposes variables that may influence agribusiness outcomes and highlights where further "
        "analytical work would be most valuable. The focus is crop performance (yield), production trends and "
        "input utilization (cultivated area).")

    # ---------- 2 Dataset
    doc.add_heading("2. Dataset description and justification", 1)
    doc.add_paragraph(f"Source: {SOURCE_NOTE} ({DATASET_URL}). File analysed: {R['input_file']}.")
    doc.add_paragraph(
        f"After cleaning, the data holds {fmt(o['rows'])} district-level records covering {o['states']} states/UTs, "
        f"{fmt(o['districts'])} districts and {o['crops']} crops between {o['year_min']} and {o['year_max']}.")
    table(doc, ["Column", "Meaning"], [
        ["State_Name / District_Name", "Administrative location of the record"],
        ["Crop_Year", "Agricultural year of the record"],
        ["Season", "Kharif, Rabi, Summer, Autumn, Winter or Whole Year"],
        ["Crop", "Crop name"],
        ["Area", "Area under cultivation (hectares): the land-input measure"],
        ["Production", "Output in tonnes (coconut is in nuts and is excluded)"],
        ["Yield (derived)", "Production / Area, in tonnes per hectare: the crop-performance measure"],
    ])
    doc.add_paragraph("Why this dataset:")
    bullets(doc, [
        "It comes from official government statistics, so it is publicly verifiable and free to use.",
        "It is granular (district x crop x season x year), which allows comparisons across place, crop and time.",
        "It directly supports the three themes in the brief: crop performance (yield), production trends "
        "(multi-year series) and input utilization (area under cultivation).",
        "It is large enough for robust statistics yet simple enough to explain every step.",
    ])

    # ---------- 3 Methodology
    doc.add_heading("3. Approach and methodology", 1)
    doc.add_heading("3.1 Data cleaning", 2)
    bullets(doc, [
        f"Raw rows: {fmt(cl['rows_raw'])}. Missing values were concentrated in: "
        + ", ".join(f"{k} ({v})" for k, v in cl["missing_per_column"].items() if v) + "."
        if any(cl["missing_per_column"].values()) else f"Raw rows: {fmt(cl['rows_raw'])}. No missing values were found.",
        f"Exact duplicate rows removed: {fmt(cl['duplicates'])}. Rows with missing Area/Production dropped: "
        f"{fmt(cl['rows_raw'] - cl['duplicates'] - cl['rows_after_dropna'])}.",
        f"Rows with zero area removed (yield undefined): {fmt(cl['nonpositive_area'])}.",
        f"Coconut rows excluded ({fmt(cl['coconut_rows_excluded'])}) because they are measured in nuts, not tonnes.",
        "Text columns were trimmed of whitespace (e.g. season labels carry trailing spaces).",
        f"Final analysis set: {fmt(cl['rows_final'])} rows.",
    ])
    yc = R["year_coverage"]
    if yc["dropped_years"]:
        doc.add_paragraph(
            "Years with far fewer records than typical (" + ", ".join(map(str, yc["dropped_years"])) +
            ") look only partly reported, so they were left out of time-trend analyses to avoid false declines.")
    doc.add_heading("3.2 Descriptive statistics", 2)
    doc.add_paragraph(
        "For Area, Production and Yield the analysis computed count, mean, standard deviation, quartiles, median, "
        "skewness and kurtosis. Because agricultural quantities span several orders of magnitude, distributions were "
        "also inspected on a log10 scale, and non-parametric statistics were preferred where assumptions of normality "
        "fail. Outliers were flagged with the 1.5 x IQR rule on log-yield within each crop.")
    doc.add_heading("3.3 Visual and inferential techniques", 2)
    bullets(doc, [
        "Histograms (raw vs log) for distribution shape; bar charts for rankings and concentration.",
        "Line charts with fitted linear trends (OLS regression) for temporal patterns.",
        "Box plots plus a Kruskal-Wallis test to compare yields across seasons.",
        "Log-log scatter plot with regression slope as an area-to-output elasticity; Spearman correlation matrix.",
        "Coefficient of variation (CV) of annual median yield as a simple stability / risk measure.",
        "Heatmap of median yield across the top states and crops to show geographic performance gaps.",
    ])

    # ---------- 4 Findings
    doc.add_heading("4. Data quality and distributions", 1)
    figure(doc, figdir, "01_missing_values.png", "Figure 1: Missing values by column in the raw data.", 4.8)
    d = {r["variable"]: r for r in R["describe"]}
    table(doc, ["Variable", "Mean", "Median", "Std", "Min", "Max", "Skew"],
          [[v, fmt(d[v]["mean"], 2), fmt(d[v]["median"], 2), fmt(d[v]["std"], 2), fmt(d[v]["min"], 2),
            fmt(d[v]["max"], 2), fmt(d[v]["skew"], 1)] for v in ["Area", "Production", "Yield"]])
    doc.add_paragraph(
        f"Interpretation. Production has a mean of {fmt(d['Production']['mean'])} t but a median of only "
        f"{fmt(d['Production']['median'])} t, and Area shows the same gap (mean {fmt(d['Area']['mean'])} ha vs median "
        f"{fmt(d['Area']['median'])} ha). With skewness of {d['Production']['skew']:.1f} for production, "
        "a few very large district-crop records dominate the averages, so medians and log scales describe the typical "
        f"record better. About {R['outliers']['share_pct']}% of records ({fmt(R['outliers']['yield_outlier_rows'])}) are yield "
        "outliers within their crop; some may be genuine high performers, others likely data-entry or unit errors, "
        "so they are kept but treated carefully (medians, log scale).")
    figure(doc, figdir, "02_distributions.png", "Figure 2: Distributions of Area, Production and Yield, raw (top) and log10 (bottom).")

    doc.add_heading("5. Production trends and market concentration", 1)
    tt = R["trend_total"]
    figure(doc, figdir, "03_production_trend.png", "Figure 3: Total recorded production by year with linear trend.")
    chg = (tt["last_mt"] / tt["first_mt"] - 1) * 100 if tt["first_mt"] else 0
    doc.add_paragraph(
        f"Interpretation. Recorded production moved from {tt['first_mt']} million tonnes in {tt['first_year']} to "
        f"{tt['last_mt']} million tonnes in {tt['last_year']} ({chg:+.0f}%). The fitted trend is "
        f"{tt['slope_mt_per_year']:+.2f} Mt per year (R-squared {tt['r2']}) and is {sig(tt['p_value'])}. "
        "Because coverage of districts can change between years, part of any rise may reflect reporting rather than "
        "real growth; this is flagged as a limitation.")
    figure(doc, figdir, "04_top_crops.png", "Figure 4: Top 10 crops by cumulative production.")
    tc = R["top_crops"]
    doc.add_paragraph(
        f"Interpretation. {tc[0]['crop']} is the largest crop by recorded tonnage ({tc[0]['share_pct']}% of the total), "
        f"followed by {tc[1]['crop']} ({tc[1]['share_pct']}%) and {tc[2]['crop']} ({tc[2]['share_pct']}%). The top three "
        f"crops together make up {R['top3_share_pct']}% of tonnage. Tonnage favours bulky crops, so these shares show "
        "volume rather than value; agribusiness decisions should be weighted by price as well.")
    figure(doc, figdir, "05_top_states.png", "Figure 5: Share of cumulative production by state.")
    ts = R["top_states"]
    doc.add_paragraph(
        f"Interpretation. Production is geographically concentrated: the top five states account for "
        f"{R['top5_state_share_pct']}% of output, led by {ts[0]['state']} ({ts[0]['share_pct']}%) and {ts[1]['state']} "
        f"({ts[1]['share_pct']}%). For input suppliers, processors and logistics firms, these regions represent the "
        "densest demand and supply, while also meaning shared exposure to regional weather or policy shocks.")

    doc.add_heading("6. Crop performance (yield)", 1)
    se = R["season"]
    figure(doc, figdir, "06_yield_by_season.png", "Figure 6: Yield by season.", 5.5)
    top_s, low_s = se["table"][0], se["table"][-1]
    kw = (f"A Kruskal-Wallis test gives H = {se['kruskal_H']} and the difference in yield between seasons is "
          f"{sig(se['kruskal_p'])}." if se["kruskal_H"] is not None else "")
    doc.add_paragraph(
        f"Interpretation. Median yield is highest in the {top_s['Season']} season ({top_s['median']:.2f} t/ha) and lowest "
        f"in {low_s['Season']} ({low_s['median']:.2f} t/ha). {kw} Note that season is partly a proxy for crop mix "
        "(different crops are grown in different seasons), so this should be read together with the crop-level views.")
    figure(doc, figdir, "09_yield_trends.png", "Figure 7: Median district yield over time for the top-5 crops.")
    rows = [[y["crop"], f"{y['slope_per_year']:+.3f}", f"{y['pct_per_year']:+.2f}%", f"{y['p_value']:.3f}",
             "Yes" if y["p_value"] < 0.05 else "No"] for y in R["yield_trends"]]
    table(doc, ["Crop", "Slope (t/ha/yr)", "Change per year", "p-value", "Significant"], rows)
    up = [y["crop"] for y in R["yield_trends"] if y["p_value"] < 0.05 and y["slope_per_year"] > 0]
    down = [y["crop"] for y in R["yield_trends"] if y["p_value"] < 0.05 and y["slope_per_year"] < 0]
    flat = [y["crop"] for y in R["yield_trends"] if y["p_value"] >= 0.05]
    parts = []
    if up:
        parts.append("a significant upward yield trend for " + ", ".join(up))
    if down:
        parts.append("a significant downward trend for " + ", ".join(down))
    if flat:
        parts.append("no clear trend (stagnation or noise) for " + ", ".join(flat))
    doc.add_paragraph("Interpretation. The top-5 crops show " + "; ".join(parts) + ". "
                      "Crops with stagnant yields are candidates for agronomic support, better seed varieties or "
                      "extension services, whereas rising yields signal technology or input improvements that are working.")
    if R["stability"]:
        figure(doc, figdir, "10_yield_stability.png", "Figure 8: Year-to-year yield variability among top-10 crops.", 5.5)
        st = R["stability"]
        doc.add_paragraph(
            f"Interpretation. {st[0]['crop']} has the steadiest yield (CV {st[0]['cv_pct']}%), whereas {st[-1]['crop']} is the "
            f"most variable (CV {st[-1]['cv_pct']}%). Higher variability implies higher production risk, relevant to "
            "contract farming, crop insurance pricing and procurement planning.")
    figure(doc, figdir, "11_state_crop_yield.png", "Figure 9: Median yield by state and crop (top 8 each).")
    ex = R.get("state_crop_extremes")
    if ex:
        doc.add_paragraph(
            f"Interpretation. Even within the same crop, yields differ widely by state. Among the displayed pairs the "
            f"highest median yield is {ex['best']['crop']} in {ex['best']['state']} ({ex['best']['yield']} t/ha) and the "
            f"lowest is {ex['worst']['crop']} in {ex['worst']['state']} ({ex['worst']['yield']} t/ha). Gaps within the "
            "same crop point to differences in irrigation, soil, inputs and practice that could be closed, and so "
            "to where extension and input investments might earn the best return.")

    doc.add_heading("7. Input utilization: area versus production", 1)
    ap = R["area_production"]
    figure(doc, figdir, "07_area_vs_production.png", "Figure 10: Area vs production (log-log).", 4.8)
    el = ap["loglog_slope"]
    el_txt = ("close to 1, meaning output scales almost proportionally with land" if 0.9 <= el <= 1.1
              else "below 1, indicating diminishing returns to extra land" if el < 0.9
              else "above 1, suggesting larger units achieve disproportionately higher output")
    doc.add_paragraph(
        f"Interpretation. Area and production are strongly rank-correlated (Spearman rho = {ap['spearman_rho']}). On the log-log "
        f"scale the slope is {el} (R-squared {ap['loglog_r2']}), {el_txt}. The R-squared shows that area alone "
        f"explains about {ap['loglog_r2'] * 100:.0f}% of the variation in production on the log scale; the remainder is "
        "driven by crop type, yield level and other factors, which motivates the crop- and region-level analysis above.")
    figure(doc, figdir, "08_correlation_heatmap.png", "Figure 11: Spearman correlation matrix.", 4.4)
    doc.add_paragraph(
        f"Interpretation. Year is only weakly related to log-yield (rho = {R['corr_year_yield']}), so across all crops "
        "pooled together there is little time-driven yield signal, which fits the crop-level picture: gains are crop- "
        "and place-specific rather than universal.")

    # ---------- 8 insights
    doc.add_heading("8. Key insights for agribusiness decisions", 1)
    bullets(doc, [
        f"Concentration: the top three crops make up {R['top3_share_pct']}% of tonnage and the top five states "
        f"{R['top5_state_share_pct']}% of output. Supply-chain and processing investments will find scale in these hubs, "
        "but face correlated risk.",
        "Yield gaps: the same crop performs very differently across states, so closing gaps is likely a bigger lever "
        "than expanding area.",
        "Risk: yield volatility differs by crop (see Figure 8); contracts, insurance and storage should be priced by crop-specific risk.",
        f"Land use: output scales with area (log-log slope {el}), but area explains only part of production; "
        "productivity-enhancing inputs matter.",
        "Seasonality: yield and mix differ by season, which affects logistics, storage capacity and working-capital cycles.",
    ])

    doc.add_heading("9. Variables likely to influence agribusiness outcomes", 1)
    doc.add_paragraph("Based on the patterns above, these are the variables worth adding or modelling next:")
    table(doc, ["Variable", "Why it matters", "Possible public source"], [
        ["Rainfall / temperature", "Main driver of year-to-year yield variability", "India Meteorological Department"],
        ["Irrigated area share", "Likely explains state-level yield gaps", "Land Use Statistics, Ministry of Agriculture"],
        ["Fertilizer and seed use", "Direct input-to-yield link", "Fertiliser Association of India, data.gov.in"],
        ["Market prices (MSP, mandi prices)", "Converts tonnage into revenue and drives crop choice", "Agmarknet, CACP"],
        ["Soil type / quality", "Explains within-state heterogeneity", "Soil Health Card data"],
        ["Season and crop type", "Already shown to separate yield levels", "In this dataset"],
    ])

    # ---------- 10 limitations
    doc.add_heading("10. Limitations and next steps", 1)
    bullets(doc, [
        "The dataset records quantities, not prices or costs, so profitability cannot be assessed directly.",
        "Yield is derived (Production / Area); reporting errors in either field distort it. Outliers were retained.",
        "Correlation is not causation: season, crop and state effects are intertwined.",
        "Reporting coverage may vary across years and districts, which can distort trends.",
        "Next steps: merge weather and price data, fit a multivariable model (e.g. regression with crop and state "
        "fixed effects, or gradient boosting) for yield, and run forecasting for production planning.",
    ])

    # ---------- 11 tools
    doc.add_heading("11. Tools and methodology used", 1)
    table(doc, ["Tool", "Purpose"], [
        ["Python 3", "Analysis language"],
        ["pandas, NumPy", "Data cleaning, aggregation, derived variables"],
        ["SciPy", "Spearman correlation, linear regression, Kruskal-Wallis test"],
        ["Matplotlib, Seaborn", "All charts"],
        ["python-docx", "Automatic generation of this report"],
        ["Git / GitHub", "Version control and sharing; full code and instructions in the repository"],
    ])
    doc.add_paragraph("Reproducibility: run python src/eda.py then python src/build_report.py (see README.md).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="outputs/results.json")
    ap.add_argument("--figures", default="outputs/figures")
    ap.add_argument("--out", default="reports/Agribusiness_EDA_Report.docx")
    a = ap.parse_args()
    build(json.load(open(a.results)), Path(a.figures), Path(a.out))
    print(f"Report written to {a.out}")
