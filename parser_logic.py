from config import TEST_MAP

# Define IDs you want to ignore
HIDDEN_IDS = ["950", "951", "952"]


def _normalize_test_id(test_id):
    test_id = test_id.strip()
    integer_part, separator, fractional_part = test_id.partition(".")
    if integer_part.isdigit() and (
        not separator
        or (fractional_part and all(digit == "0" for digit in fractional_part))
    ):
        return integer_part.lstrip("0") or "0"
    return test_id


def _test_name_for_id(test_id):
    if test_id in TEST_MAP:
        return TEST_MAP[test_id]

    normalized_id = _normalize_test_id(test_id)
    matches = {
        test_name
        for mapped_id, test_name in TEST_MAP.items()
        if _normalize_test_id(mapped_id) == normalized_id
    }
    if len(matches) == 1:
        return matches.pop()
    return f"ID: {test_id}"


def parse_log_line(line):
    """Parse a result line, retaining explicit missing-result records."""
    parts = [p.strip() for p in line.split('\t')]
    
    if len(parts) >= 5:
        name = parts[1]
        tid = parts[4]  # This is the Test ID
        res = parts[5] if len(parts) >= 6 else ""
        
        if tid in HIDDEN_IDS:
            return None

        patient_name = name or "UNKNOWN"
        patient_id = parts[2] or "UNKNOWN"
        if patient_name == "UNKNOWN" and patient_id == "UNKNOWN":
            return None

        test_display_name = _test_name_for_id(tid)
        if not res or "no result" in res.casefold() or "no-result" in res.casefold():
            res = "MISSING_RESULT"
        return (patient_id, patient_name, test_display_name, res)
            
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
