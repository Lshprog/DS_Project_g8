import streamlit as st
import pandas as pd
import numpy as np
import joblib
from config import EVENT_CATEGORIES

@st.cache_data
def load_price_data(path):
    df = pd.read_csv(str(path))
    df.columns = [c.strip() for c in df.columns]

    # standardize columns
    if "value" in df.columns and "price" not in df.columns:
        df = df.rename(columns={"value": "price"})
    if "Date" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"Date": "date"})

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["date", "price"]).sort_values("date").reset_index(drop=True)
    return df

@st.cache_data
def load_sentiment_data(path, selected_topic):
    df = pd.read_csv(str(path))
    df.columns = [c.strip() for c in df.columns]

    if "date" not in df.columns:
        raise ValueError("Sentiment file must contain a 'date' column")

    if "topic" not in df.columns:
        raise ValueError("Sentiment file must contain a 'topic' column")

    df["trading_day"] = pd.to_datetime(df["date"], errors="coerce")
    df["topic"] = df["topic"].astype(str).str.strip().str.lower()

    selected_topic = selected_topic.strip().lower()
    df = df[df["topic"] == selected_topic].copy()

    if df.empty:
        raise ValueError(f"No sentiment rows found for topic: {selected_topic}")

    expected_base = [
        "avg_sentiment",
        "sentiment_std",
        "news_volume",
        "log_news_vol",
        "composite_price_signal",
    ]

    for col in expected_base:
        if col not in df.columns:
            if col == "log_news_vol" and "news_volume" in df.columns:
                df["log_news_vol"] = np.log1p(df["news_volume"])
            else:
                df[col] = 0.0

    for cat in EVENT_CATEGORIES:
        for suffix in ["price_signal", "count"]:
            col = f"{cat}_{suffix}"
            if col not in df.columns:
                df[col] = 0.0

    keep_cols = (
        ["trading_day", "avg_sentiment", "sentiment_std", "news_volume",
         "log_news_vol", "composite_price_signal"]
        + [f"{cat}_price_signal" for cat in EVENT_CATEGORIES]
        + [f"{cat}_count" for cat in EVENT_CATEGORIES]
    )

    df = df[keep_cols].dropna(subset=["trading_day"]).copy()

    agg_map = {
        "avg_sentiment": "mean",
        "sentiment_std": "mean",
        "news_volume": "sum",
        "log_news_vol": "mean",
        "composite_price_signal": "mean",
    }

    for cat in EVENT_CATEGORIES:
        agg_map[f"{cat}_price_signal"] = "mean"
        agg_map[f"{cat}_count"] = "sum"

    df = df.groupby("trading_day", as_index=False).agg(agg_map)
    df = df.sort_values("trading_day").reset_index(drop=True)

    return df

@st.cache_resource
def load_model_and_scaler(model_path, scaler_path):
    model = joblib.load(str(model_path))
    scaler = joblib.load(str(scaler_path))
    return model, scaler