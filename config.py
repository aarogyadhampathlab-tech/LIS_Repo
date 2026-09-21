import os

# --- 1. NETWORK & PATH SETTINGS ---
NETWORK_SOURCE = r'\\192.168.1.103\log1' 
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv'

# --- 2. TEST MAPPING (Add new IDs here) ---
TEST_MAP = {
    "319": "TOTAL BILIRUBIN", "905": "CONJUGATED (Direct)", "798": "UNCONJUGATED (Indirect)",
    "320": "AST / SGOT", "357": "ALT / SGPT", "321": "ALKALINE PHOSPHATASE",
    "326": "GGT", "301": "TOTAL PROTEIN", "303": "ALBUMIN",
    "315": "UREA", "314": "SERUM CREATININE",
    "302": "URIC ACID", "309": "SODIUM (Na+)", "308": "POTASSIUM (K+)",
     
    "539": "HbA1c", "925": "DERIVED HbA1c", "450": "LDH", "300": "glucose",
    "927": "a1c","306":"amylase", "325": "lipase", "910": "GLOBULIN"
}

# --- 3. CRITICAL VALUE RANGES ---
CRITICAL_RANGES = {
    "SODIUM (Na+)": {"low": 120, "high": 155},
    "POTASSIUM (K+)": {"low": 3.5, "high": 6.5},
    "GLUCOSE": {"high": 250},
    "SERUM CREATININE": {"high": 2.0},
    "TOTAL BILIRUBIN": {"high": 2.0},
    "AST / SGOT": {"high": 100},
    "ALT / SGPT": {"high": 100},
}

TECHNICAL_ERROR_KEYWORDS = [
    "no result", "no-result", "technical error", "tech error", "error", "failed", "invalid", "timeout"
]
