#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path


MARKET_ASSETS = [
    {"name": "wti", "params": {"function": "WTI", "interval": "daily"}},
    {"name": "brent", "params": {"function": "BRENT", "interval": "daily"}},
    {"name": "natural_gas", "params": {"function": "NATURAL_GAS", "interval": "daily"}},
    {"name": "silver", "params": {"function": "GOLD_SILVER_HISTORY", "symbol": "SILVER", "interval": "daily"}}
]


def filter_last_n_years(data_list, years=2):
    """Filters a list of dictionaries containing a 'date' key to keep only the last `years` of data."""
    cutoff_date = datetime.utcnow() - timedelta(days=365 * years)
    filtered_data = []
    
    for entry in data_list:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
            if entry_date >= cutoff_date:
                filtered_data.append(entry)
        except (KeyError, ValueError):
            # Skip entries that don't conform to expected date format
            pass
            
    return filtered_data


def fetch_alpha_vantage_data(api_key, params):
    """Fetches data from AlphaVantage API."""
    url = "https://www.alphavantage.co/query"
    
    # Inject API key
    query_params = params.copy()
    query_params["apikey"] = api_key
    
    response = requests.get(url, params=query_params, timeout=30)
    response.raise_for_status()
    
    return response.json()


def main() -> int:
    load_dotenv()
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        print("Missing ALPHAVANTAGE_API_KEY in .env", file=sys.stderr)
        return 1

    # Create data directory
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    for i, asset in enumerate(MARKET_ASSETS):
        name = asset["name"]
        params = asset["params"]
        
        print(f"Fetching data for: {name}...")
        try:
            data = fetch_alpha_vantage_data(api_key, params)
            
            # Check for generic API errors (e.g., invalid key, rate limit)
            if "Information" in data and "rate limit" in data["Information"].lower():
                print(f"  --> Rate limit exceeded. Skipping {name}. Consider adding a delay.")
                continue
            if "Error Message" in data:
                print(f"  --> API Error for {name}: {data['Error Message']}")
                continue
            
            # Filter for last 2 years
            if "data" in data and isinstance(data["data"], list):
                original_count = len(data["data"])
                filtered_data = filter_last_n_years(data["data"], years=2)
                data["data"] = filtered_data
                print(f"  --> Filtered {original_count} down to {len(filtered_data)} records (last 2 years).")
            else:
                print(f"  --> Warning: Unexpected data format for {name}. Missing 'data' array.")

            # Save to JSON
            out_path = out_dir / f"{name}_daily_{ts}.json"
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2)
                
            print(f"  --> Saved to: {out_path}")
            
        except requests.exceptions.HTTPError as e:
             print(f"  --> HTTP Error: {e}")
        except Exception as e:
             print(f"  --> Unexpected Error: {e}")

        # Add a sleep to respect free-tier rate limits (usually 5/min) except for the last item
        if i < len(MARKET_ASSETS) - 1:
            print("  --> Sleeping for 12 seconds to avoid rate limits...")
            time.sleep(12)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())