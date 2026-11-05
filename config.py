import json
from pathlib import Path

from alert_rules import load_alert_rules


def load_test_map():
    configuration_path = Path(__file__).parent / "test_map.json"
    with configuration_path.open("r", encoding="utf-8") as mapping_file:
        categorized_map = json.load(mapping_file)

    test_map = {}
    for category, mappings in categorized_map.items():
        if not isinstance(mappings, dict):
            raise ValueError(
                f"Test map category '{category}' must contain a PID-to-name object"
            )
        for test_id, test_name in mappings.items():
            if not isinstance(test_name, str):
                raise ValueError(
                    f"Test name for PID '{test_id}' in '{category}' must be a string"
                )
            if test_id in test_map:
                raise ValueError(f"Duplicate PID '{test_id}' in test_map.json")
            test_map[test_id] = test_name
    return test_map


# --- 1. NETWORK & PATH SETTINGS ---
NETWORK_SOURCE = r'\\192.168.1.103\log1' 
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv'

# --- 2. TEST MAPPING (edit test_map.json) ---
TEST_MAP = load_test_map()

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
