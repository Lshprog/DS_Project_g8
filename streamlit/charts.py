import pandas as pd
import plotly.graph_objects as go
from pandas.tseries.offsets import BDay

def make_price_chart(filtered, latest, prob_up):
    price_hist = filtered[["trading_day", "price"]].copy().sort_values("trading_day")

    latest_price = price_hist["price"].iloc[-1]
    latest_date = price_hist["trading_day"].iloc[-1]

    future_dates = [latest_date + BDay(i) for i in range(1, 6)]

    recent_vol = float(latest["roll20_vol"].iloc[0]) if not pd.isna(latest["roll20_vol"].iloc[0]) else 0.002
    base_step = max(0.001, min(recent_vol, 0.01))

    direction_strength = (prob_up - 0.5) * 2
    projected_returns = [base_step * direction_strength for _ in range(5)]

    future_prices = [latest_price]
    for r in projected_returns:
        future_prices.append(future_prices[-1] * (1 + r))
    future_prices = future_prices[1:]

    y_min = min(price_hist["price"].min(), min(future_prices))
    y_max = max(price_hist["price"].max(), max(future_prices))
    pad = max((y_max - y_min) * 0.12, 0.5)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price_hist["trading_day"],
        y=price_hist["price"],
        mode="lines",
        name="Actual Price",
        line=dict(width=3, color="#7CC7FF")
    ))

    fig.add_trace(go.Scatter(
        x=[latest_date] + future_dates,
        y=[latest_price] + future_prices,
        mode="lines",
        name="Projected Next Week",
        line=dict(width=2, dash="dash", color="#A9D6FF"),
        opacity=0.4
    ))

    fig.update_layout(
        title="Price Trend",
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Price",
        margin=dict(l=20, r=20, t=50, b=20),
        height=420,
        legend=dict(orientation="h", y=1.02, x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    fig.update_yaxes(range=[y_min - pad, y_max + pad])
    return fig

def make_sentiment_chart(filtered):
    sent_plot = filtered[["trading_day", "avg_sentiment"]].copy().sort_values("trading_day")
    sent_plot["sentiment_smooth"] = sent_plot["avg_sentiment"].rolling(7, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sent_plot["trading_day"],
        y=sent_plot["avg_sentiment"],
        mode="lines",
        name="Raw Sentiment",
        opacity=0.20,
        line=dict(width=1, color="#9AA4B2")
    ))

    fig.add_trace(go.Scatter(
        x=sent_plot["trading_day"],
        y=sent_plot["sentiment_smooth"],
        mode="lines",
        name="7-Day Smoothed",
        line=dict(width=3, color="#4FD1C5")
    ))

    fig.update_layout(
        title="Sentiment Trend",
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Sentiment",
        margin=dict(l=20, r=20, t=50, b=20),
        height=420,
        legend=dict(orientation="h", y=1.02, x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    return fig