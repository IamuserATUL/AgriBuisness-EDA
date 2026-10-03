# Exploratory Data Analysis and Visualization for Agribusiness Insights

Week 3 task: an end-to-end exploratory data analysis (EDA) of public agribusiness data, covering
**crop performance (yield)**, **production trends** and **input utilization (cultivated area)**.
The project produces charts, summary tables and an auto-written **Word report** (`.docx`).

## Dataset

**Crop Production in India**: district-level records of area and production by crop, season and year,
compiled from the Government of India's open data portal (data.gov.in) and hosted on Kaggle:
<https://www.kaggle.com/datasets/abhinand05/crop-production-in-india>

Why this dataset: official public statistics; granular (district x crop x season x year); and it directly
supports the three themes of the brief (yield, production trends, land-input utilization).
See [`data/README.md`](data/README.md) for download steps.

## Quick start

```bash
git clone <your-repo-url>
cd agribusiness-eda
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. put the downloaded CSV at data/raw/crop_production.csv  (see data/README.md)
python src/eda.py --input data/raw/crop_production.csv   # figures + tables + results.json
python src/build_report.py                                # reports/Agribusiness_EDA_Report.docx
```

## Project structure

```
agribusiness-eda/
├── data/raw/                 # put the downloaded CSV here (git-ignored)
├── src/
│   ├── eda.py                # cleaning, descriptive stats, statistical tests, all figures
│   └── build_report.py       # writes the Word report from the computed results
├── tests/make_synthetic_data.py   # fake data for smoke-testing the pipeline only
├── outputs/                  # figures/, tables/, results.json (created when you run eda.py)
├── reports/                  # Agribusiness_EDA_Report.docx (created by build_report.py)
├── requirements.txt
└── LICENSE
```

## What the analysis does

| Step | Technique |
|---|---|
| Data quality | Missing values, duplicates, zero-area rows, unit check (coconut is in nuts, excluded), partial-year detection |
| Descriptive statistics | count, mean, std, quartiles, median, skewness, kurtosis; log10 view of skewed variables |
| Outliers | 1.5 x IQR rule on log-yield within each crop |
| Production trends | Annual totals with OLS linear trend |
| Concentration | Share of top crops and top states |
| Crop performance | Yield by season (Kruskal-Wallis test), yield trends for top-5 crops, yield stability (CV), state x crop heatmap |
| Input utilization | Area vs production log-log regression (elasticity) and Spearman correlation matrix |

Figures written to `outputs/figures/`:
missing values, distributions, production trend, top crops, top states, yield by season,
area vs production, correlation heatmap, yield trends, yield stability, state x crop yield.

## Report contents (matches the task brief)

1. Objective
2. Dataset description and justification
3. Approach: descriptive statistics, visual and inferential techniques
4. Visualizations with interpretation of each pattern
5. Key insights for agribusiness decisions
6. Variables likely to influence outcomes (rainfall, irrigation, fertilizer, prices, soil)
7. Limitations and next steps
8. Tools and methodology

All numbers and interpretive sentences in the report are computed from `outputs/results.json`, so the
report always reflects the data you ran.

## Smoke test (optional)

```bash
python tests/make_synthetic_data.py
python src/eda.py --input data/raw/SYNTHETIC_smoke_test.csv
python src/build_report.py
```

This uses randomly generated data to check that the code runs. The report is stamped with a warning
when the input file name contains `SYNTHETIC`. **Never publish findings from it.**
Delete `outputs/` and `reports/` before running on the real data if you want a clean slate.

## Limitations

- No price or cost data, so profitability is not assessed.
- Yield is derived (Production / Area); reporting errors can distort it.
- Correlation is not causation; season, crop and state effects overlap.
- District coverage can vary by year, which affects trends.

## License

MIT
