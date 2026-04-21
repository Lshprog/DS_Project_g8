import numpy as np
from config import EVENT_CATEGORIES

def build_features(price_df, daily_df):
    df = price_df.copy()

    df["log_return"] = np.log(df["price"]).diff()
    df["roll5_ret"] = df["price"].pct_change().rolling(5).mean()
    df["roll10_ret"] = df["price"].pct_change().rolling(10).mean()
    df["roll20_vol"] = df["price"].pct_change().rolling(20).std()
    df["ma5_ratio"] = df["price"] / df["price"].rolling(5).mean()
    df["ma20_ratio"] = df["price"] / df["price"].rolling(20).mean()

    df = df.rename(columns={"date": "trading_day"})
    df = df.merge(daily_df, on="trading_day", how="left")

    fill_cols = (
        ['avg_sentiment', 'sentiment_std', 'news_volume', 'log_news_vol',
         'composite_price_signal']
        + [f'{cat}_price_signal' for cat in EVENT_CATEGORIES]
        + [f'{cat}_count' for cat in EVENT_CATEGORIES]
    )

    for c in fill_cols:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0)

    # lag sentiment by 1 day to match notebook logic
    df[fill_cols] = df[fill_cols].shift(1)

    df["target_return"] = df["log_return"].shift(-1)
    df["target_up"] = (df["target_return"] > 0).astype(int)

    df = df.dropna().reset_index(drop=True)
    return df