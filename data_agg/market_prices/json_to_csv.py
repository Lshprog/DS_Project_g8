#!/usr/bin/env python3
import json
import csv
import sys
import argparse
from pathlib import Path

def convert_json_to_csv(json_filepath: str | Path, csv_filepath: str | Path) -> None:
    """
    Converts a market data JSON file (containing a 'data' array) into a CSV file.
    """
    json_path = Path(json_filepath)
    csv_path = Path(csv_filepath)

    with open(json_path, 'r', encoding='utf-8') as f:
        content = json.load(f)

    # Extract the data array
    data_records = content.get("data")
    
    if not data_records or not isinstance(data_records, list):
        raise ValueError(f"No valid 'data' array found in {json_path}")

    # Determine CSV headers from the first record to be adaptable
    if len(data_records) > 0:
        headers = list(data_records[0].keys())
    else:
        headers = ["date", "value"]  # Fallback if empty

    # Ensure output directory exists
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data_records)

def process_directory(input_dir: Path, output_dir: Path) -> None:
    """Finds all JSON files in input_dir and converts them, saving to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_files = list(input_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
        
    for json_path in json_files:
        csv_path = output_dir / json_path.with_suffix('.csv').name
        try:
            convert_json_to_csv(json_path, csv_path)
        except Exception as e:
            print(f"Failed to convert {json_path.name}: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Market Data JSON to CSV")
    parser.add_argument("input_path", help="Path to the input JSON file or directory containing JSON files")
    parser.add_argument("-o", "--output", help="Path to the output CSV file or directory", default=None)
    
    args = parser.parse_args()
    input_path = Path(args.input_path)
    
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist.", file=sys.stderr)
        return 1
        
    if input_path.is_dir():
        # Directory Mode
        output_dir = Path(args.output) if args.output else input_path.parent / "csv"
        process_directory(input_path, output_dir)
        
    else:
        # Single File Mode
        if args.output:
            csv_path = Path(args.output)
        else:
            csv_path = input_path.with_suffix('.csv')
            
        try:
            convert_json_to_csv(input_path, csv_path)
        except Exception as e:
            print(f"Error converting file: {e}", file=sys.stderr)
            return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
