import json
from pathlib import Path

from alert_rules import load_alert_rules

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

# --- 3. DEMO ALERT RANGES (edit threshold_editor/thresholds.json) ---
ALERT_RULES = load_alert_rules()
CRITICAL_RANGES = {
    test_name: {bound: value for bound, value in rule.items() if bound in ("low", "high")}
    for test_name, rule in ALERT_RULES.items()
}


def get_critical_ranges():
    return load_alert_rules()


def save_critical_ranges(critical_ranges):
    existing = load_alert_rules()
    updated = {}
    for test_name, thresholds in critical_ranges.items():
        rule = dict(thresholds)
        if test_name in existing:
            rule.setdefault("unit", existing[test_name].get("unit", ""))
        updated[test_name] = rule

    configuration_path = (
        Path(__file__).parent / "threshold_editor" / "thresholds.json"
    )
    with configuration_path.open("w", encoding="utf-8") as rules_file:
        json.dump({
            "_note": (
                "DEMO ALERT TRIGGERS ONLY. Confirm thresholds and units with "
                "the laboratory director before clinical use."
            ),
            "critical_ranges": updated,
        }, rules_file, indent=4)
        rules_file.write("\n")

TECHNICAL_ERROR_KEYWORDS = [
    "no result", "no-result", "technical error", "tech error", "error", "failed", "invalid", "timeout"
]
