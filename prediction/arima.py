 """
arima_commodities.py
────────────────────
ARIMA forecasting for WTI, Brent, Natural Gas, and Silver.

Usage:
    python arima_commodities.py

Dependencies:
    pip install pandas numpy statsmodels scikit-learn matplotlib
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

COMMODITIES = {
    "WTI Crude Oil":  {"file": "wti_daily_20260228_075143.csv",         "col": "value"},
    "Brent Crude Oil":{"file": "brent_daily_20260228_075143.csv",        "col": "value"},
    "Natural Gas":    {"file": "natural_gas_daily_20260228_075143.csv",  "col": "value"},
    "Silver":         {"file": "silver_daily_20260228_075143.csv",       "col": "price"},
}

TEST_SIZE = 60    # last 60 days held out for evaluation
HORIZON   = 30    # days to forecast into the future

# ── Helpers ───────────────────────────────────────────────────────────────────

def load(filepath, price_col):
    df = pd.read_csv(filepath, parse_dates=["date"])
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    series = df.set_index("date")[price_col].sort_index().dropna().astype(float)
    return series


def suggest_d(series):
    """Return d=0 if already stationary, else d=1."""
    _, p, *_ = adfuller(series.dropna())
    return 0 if p < 0.05 else 1


def walk_forward(series, order, test_size=TEST_SIZE, refit_every=21):
    """One-step-ahead rolling forecast — no look-ahead bias."""
    n = len(series) - test_size
    history, preds = list(series.iloc[:n]), []

    for i in range(test_size):
        if i % refit_every == 0:
            model = ARIMA(history, order=order).fit()
        try:
            preds.append(float(model.forecast(1).iloc[0]))
        except Exception:
            preds.append(history[-1])
        history.append(float(series.iloc[n + i]))

    return pd.Series(preds, index=series.index[-test_size:])


def evaluate(actual, predicted, name):
    mae  = mean_absolute_error(actual, predicted)
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)
    a, p = np.sign(actual.diff().dropna()), np.sign(predicted.diff().dropna())
    da   = float((a == p).mean() * 100)
    print(f"  {name}")
    print(f"    MAE={mae:.4f}  RMSE={rmse:.4f}  MAPE={mape:.2f}%  DirAcc={da:.1f}%")
    return {"Commodity": name, "MAE": mae, "RMSE": rmse, "MAPE (%)": mape, "DirAcc (%)": da}


def plot(y_train, y_test, preds, future, name):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6),
                                    gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle(f"{name} — ARIMA Forecast", fontweight="bold")

    ax1.plot(y_train.tail(120).index, y_train.tail(120), color="#aaa", label="Train (120d)")
    ax1.plot(y_test.index,  y_test,  color="#1f77b4", label="Actual")
    ax1.plot(preds.index,   preds,   color="#ff7f0e", linestyle="--", label="Forecast")
    ax1.plot(future.index, future["forecast"], color="#2ca02c", linestyle=":", label="Future")
    ax1.fill_between(future.index, future["lower"], future["upper"],
                     color="#2ca02c", alpha=0.15, label="95% CI")
    ax1.axvline(y_test.index[0], color="red", linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.tick_params(axis="x", rotation=30)

    resid = y_test - preds
    ax2.bar(resid.index, resid, color=["#2ca02c" if r >= 0 else "#d62728" for r in resid],
            alpha=0.6, width=1)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("Residual"); ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig(f"forecast_{name.lower().replace(' ', '_')}.png", dpi=150, bbox_inches="tight")
    plt.show()


# ── Main ──────────────────────────────────────────────────────────────────────

all_metrics = []

for name, meta in COMMODITIES.items():
    print(f"\n{'─'*45}\n{name}")

    series  = load(meta["file"], meta["col"])
    d       = suggest_d(series)
    order   = (1, d, 1)
    print(f"  Order: ARIMA{order}")

    y_train = series.iloc[:-TEST_SIZE]
    y_test  = series.iloc[-TEST_SIZE:]

    # Walk-forward evaluation
    preds   = walk_forward(series, order)
    metrics = evaluate(y_test, preds, name)
    all_metrics.append(metrics)

    # Future forecast (fit on full training set)
    fitted  = ARIMA(y_train, order=order).fit()
    fc      = fitted.get_forecast(HORIZON)
    ci      = fc.conf_int()
    future  = pd.DataFrame({
        "forecast": fc.predicted_mean.values,
        "lower":    ci.iloc[:, 0].values,
        "upper":    ci.iloc[:, 1].values,
    }, index=pd.bdate_range(y_test.index[-1] + pd.offsets.BDay(1), periods=HORIZON))

    plot(y_train, y_test, preds, future, name)

# Summary table
print(f"\n{'═'*60}\nSummary\n{'═'*60}")
print(pd.DataFrame(all_metrics).to_string(index=False))