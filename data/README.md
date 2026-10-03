# Data

The raw data is not committed to the repository (see `.gitignore`).

1. Open <https://www.kaggle.com/datasets/abhinand05/crop-production-in-india> (free Kaggle account needed).
2. Download the dataset and unzip it.
3. Copy the CSV to `data/raw/crop_production.csv` (the file is usually called `crop_production.csv` or `apy.csv`).

Expected columns: `State_Name, District_Name, Crop_Year, Season, Crop, Area, Production`.
`src/eda.py` stops with a clear message if any column is missing.

Original source: Government of India open data, <https://data.gov.in>. Check the dataset page for its licence terms.
