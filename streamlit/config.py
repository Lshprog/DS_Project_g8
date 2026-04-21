FEATURE_COLS = [
    'log_return', 'roll5_ret', 'roll10_ret', 'roll20_vol', 'ma5_ratio', 'ma20_ratio',
    'avg_sentiment', 'sentiment_std', 'log_news_vol',
    'composite_price_signal',
    'supply_price_signal', 'demand_price_signal', 'inventory_price_signal',
    'transport_price_signal', 'policy_price_signal', 'weather_price_signal',
    'macro_price_signal', 'outage_price_signal',
    'supply_count', 'demand_count', 'inventory_count', 'transport_count',
    'policy_count', 'weather_count', 'macro_count', 'outage_count',
]

EVENT_CATEGORIES = [
    'supply', 'demand', 'inventory', 'transport',
    'policy', 'weather', 'macro', 'outage'
]

COMMODITY_TOPIC_MAP = {
    "Brent": "oil",
    "Natural Gas": "gas",
    "Silver": "silver",
}

COMMODITY_PRICE_FILE_MAP = {
    "Brent": "brent_daily.csv",
    "Natural Gas": "natural_gas_daily.csv",
    "Silver": "silver_daily.csv",
}