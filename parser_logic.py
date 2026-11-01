import time
from config import TEST_MAP

# Define IDs you want to ignore
HIDDEN_IDS = ["950", "951", "952"]

def parse_log_line(line):
    """Parse a result line, retaining explicit missing-result records."""
    parts = [p.strip() for p in line.split('\t')]
    
    if len(parts) >= 5:
        name = parts[1]
        tid = parts[4]  # This is the Test ID
        res = parts[5] if len(parts) >= 6 else ""
        
        if tid in HIDDEN_IDS:
            return None
            
        if any(c.isalpha() for c in name):
            test_display_name = TEST_MAP.get(tid, f"ID: {tid}")
            patient_id = parts[2] or "UNKNOWN"
            if not res or "no result" in res.casefold() or "no-result" in res.casefold():
                res = "MISSING_RESULT"
            return (patient_id, name, test_display_name, res)
            
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
