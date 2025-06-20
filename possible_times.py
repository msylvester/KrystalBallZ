#!/usr/bin/env python3
import sys
import json

def extract_posted_dates(data):
    """
    Recursively extract all posted_date key/value pairs from the given JSON data.
    If the data is a list of job objects, it returns a dict mapping each job's id (or index if id missing)
    to its posted_date value. If the JSON is a nested dict, it will attempt to pull out any posted_date keys.
    """
    results = {}
    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                if 'posted_date' in item:
                    key = item.get('id', f'job_{i}')
                    results[key] = item['posted_date']
                # Also check nested dictionaries/lists within each job
                nested = extract_posted_dates(item)
                if nested:
                    results[f'job_{i}_nested'] = nested
    elif isinstance(data, dict):
        for key, value in data.items():
            if key == 'posted_date':
                results[key] = value
            elif isinstance(value, (dict, list)):
                nested = extract_posted_dates(value)
                if nested:
                    results[key] = nested
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: possible_times.py <json_file>")
        sys.exit(1)
    json_file = sys.argv[1]
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)
    
    posted_dates = extract_posted_dates(data)
    with open("p_t.txt", "w") as f:
        f.write(json.dumps(posted_dates, indent=2))

if __name__ == '__main__':
    main()
