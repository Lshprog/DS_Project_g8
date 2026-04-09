# Project

## Overview
This project follows a standard data-science workflow from data ingestion to modeling and evaluation. Update the sections below to reflect your specific problem, dataset, and results.

## Goals
- Define the business or research question.
- Identify the target variable and success metrics.
- Set constraints (latency, interpretability, resources).

## Data
- **Source**: Describe where the data comes from.
- **Scope**: Time range, size, key fields.
- **Access**: Any credentials or permissions required.

## Process
1. **Ingestion**: Acquire raw data and place it under `data/` (or another folder you choose).
2. **Cleaning**: Handle missing values, duplicates, and outliers.
3. **Exploration**: Perform EDA to understand distributions and relationships.
4. **Feature Engineering**: Create or transform features based on insights.
5. **Modeling**: Train baseline and candidate models.
6. **Evaluation**: Compare models using agreed metrics and validation strategy.
7. **Reporting**: Summarize findings, limitations, and next steps.

## Repository Structure
- `data/` — raw and intermediate datasets (see `.gitignore`; `data/processed/` may hold small shared exports)
- `models/` — trained model artifacts (ignored by git)
- `outputs/` — plots, tables, and reports (ignored by git)
- `src/` — source code (add if applicable)
- `notebooks/` — exploratory notebooks (add if applicable)

## LSTM branch (`LSTM`)
Work on branch **`LSTM`** for commodity LSTM experiments ([repo](https://github.com/Lshprog/DS_Project_g8)).

| Notebook | Purpose |
|----------|---------|
| `notebooks/LSTMModel1.ipynb` | Baseline univariate LSTM on (synthetic) price series |
| `notebooks/LSTM_real_multifeature.ipynb` | Multivariate LSTM with FinBERT daily features; default CSV path `data/processed/merged_for_lstm.csv` (run from repo root) |
| `notebooks/finBert_commodity_pipeline.ipynb` | Teammate FinBERT + topic pipeline; run through merge to regenerate `merged_for_lstm.csv` |

**Dependencies** (typical): `torch`, `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `transformers`, `sentence-transformers`, `tqdm` (see `requirments.txt` and extend as needed for FinBERT).

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Describe how to run the pipeline or scripts once they exist.

## Results
Summarize key outcomes, metrics, and observations.

## Next Steps
- Improve feature engineering.
- Tune models and validate robustness.
- Prepare for deployment or presentation.
