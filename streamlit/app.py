import streamlit as st
import pandas as pd
from pathlib import Path

from config import FEATURE_COLS, COMMODITY_TOPIC_MAP, COMMODITY_PRICE_FILE_MAP
from loaders import load_price_data, load_sentiment_data, load_model_and_scaler
from features import build_features
from style import apply_custom_style
from tabs.overview_tab import render_overview_tab
from tabs.evaluation_tab import render_evaluation_tab

st.set_page_config(
    page_title="Commodity Direction Dashboard",
    page_icon="📈",
    layout="wide"
)

apply_custom_style()

BASE_DIR = Path(__file__).resolve().parent.parent

st.title("Commodity Price Direction Dashboard")
st.caption("Historical price and sentiment analytics with next-day direction prediction")

commodity = st.selectbox("Commodity", ["Brent", "Natural Gas", "Silver"])

selected_topic = COMMODITY_TOPIC_MAP[commodity]
selected_price_file = COMMODITY_PRICE_FILE_MAP[commodity]

price_df = load_price_data(BASE_DIR / "data" / selected_price_file)
sent_df = load_sentiment_data(
    BASE_DIR / "data" / "daily_topic_sentiment.csv",
    selected_topic
)

model, scaler = load_model_and_scaler(
    BASE_DIR / "models" / "xgb_model.pkl",
    BASE_DIR / "models" / "scaler.pkl"
)

if commodity != "Brent":
    st.info("Charts now reflect the selected commodity and matching topic sentiment. Prediction model validity depends on whether it was trained for this commodity.")

merged = build_features(price_df, sent_df)

min_date = merged["trading_day"].min().date()
max_date = merged["trading_day"].max().date()

default_window_days = 30

if "start_date" not in st.session_state:
    st.session_state.start_date = max(min_date, max_date - pd.Timedelta(days=default_window_days))

if "end_date" not in st.session_state:
    st.session_state.end_date = max_date

def clamp_dates():
    if st.session_state.start_date < min_date:
        st.session_state.start_date = min_date
    if st.session_state.end_date > max_date:
        st.session_state.end_date = max_date
    if st.session_state.start_date > st.session_state.end_date:
        st.session_state.start_date = st.session_state.end_date

st.markdown("### Select History Range")

btn1, btn2, btn3, btn4 = st.columns(4)

with btn1:
    if st.button("← 1 Day", use_container_width=True):
        st.session_state.start_date -= pd.Timedelta(days=1)
        st.session_state.end_date -= pd.Timedelta(days=1)
        clamp_dates()

with btn2:
    if st.button("→ 1 Day", use_container_width=True):
        st.session_state.start_date += pd.Timedelta(days=1)
        st.session_state.end_date += pd.Timedelta(days=1)
        clamp_dates()

with btn3:
    if st.button("← 1 Week", use_container_width=True):
        st.session_state.start_date -= pd.Timedelta(days=7)
        st.session_state.end_date -= pd.Timedelta(days=7)
        clamp_dates()

with btn4:
    if st.button("→ 1 Week", use_container_width=True):
        st.session_state.start_date += pd.Timedelta(days=7)
        st.session_state.end_date += pd.Timedelta(days=7)
        clamp_dates()

selected_range = st.date_input(
    "Choose date range",
    value=(st.session_state.start_date, st.session_state.end_date),
    min_value=min_date,
    max_value=max_date
)

if len(selected_range) == 2:
    st.session_state.start_date, st.session_state.end_date = selected_range
    clamp_dates()

filtered = merged[
    (merged["trading_day"].dt.date >= st.session_state.start_date) &
    (merged["trading_day"].dt.date <= st.session_state.end_date)
].copy()

if filtered.empty:
    st.warning("No data available for the selected date range.")
    st.stop()

latest = filtered.iloc[[-1]].copy()
X_latest = latest[FEATURE_COLS]
X_latest_scaled = scaler.transform(X_latest)

prob_up = model.predict_proba(X_latest_scaled)[0][1]
pred = int(prob_up >= 0.5)

overview_tab, eval_tab = st.tabs(["Overview", "Model Evaluation"])

with overview_tab:
    render_overview_tab(filtered, latest, prob_up, pred)

with eval_tab:
    render_evaluation_tab(filtered, model, scaler, FEATURE_COLS)