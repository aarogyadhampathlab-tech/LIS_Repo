import time
from config import TEST_MAP

# Define IDs you want to ignore
HIDDEN_IDS = ["950", "951", "952"]

def parse_log_line(line):
    """Parses a single line and filters out hidden IDs."""
    parts = [p.strip() for p in line.split('\t')]
    
    if len(parts) >= 6:
        name = parts[1]
        tid = parts[4]  # This is the Test ID
        res = parts[5]
        
        # --- NEW FILTER LOGIC ---
        # 1. Skip if the ID is in our hidden list
        if tid in HIDDEN_IDS:
            return None
            
        # 2. Regular validation
        if any(c.isalpha() for c in name) and "No Result" not in res:
            test_display_name = TEST_MAP.get(tid, f"ID: {tid}")
            return (name, test_display_name, res)
            
    return None

def process_file(file_path):
    """Reads the file and extracts only allowed test rows."""
    valid_rows = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                result = parse_log_line(line)
                if result:
                    valid_rows.append(result)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return valid_rows
