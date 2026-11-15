import json
import math
import re
from pathlib import Path


ALERT_RULES_PATH = Path(__file__).parents[1] / "config" / "thresholds.json"
CRITICAL_TEST_ALIASES = {
    "sodium": "sodiumna",
    "potassium": "potassiumk",
    "bloodglucoserandom": "glucose",
}


def find_critical_range(test_name, critical_ranges):
    normalized_name = re.sub(r"[^a-z0-9]", "", test_name.casefold())
    normalized_name = CRITICAL_TEST_ALIASES.get(normalized_name, normalized_name)
    for configured_name, definition in critical_ranges.items():
        normalized_configured_name = re.sub(
            r"[^a-z0-9]", "", configured_name.casefold()
        )
        if normalized_name == normalized_configured_name:
            return definition
    return None


def load_alert_rules(path=ALERT_RULES_PATH):
    with Path(path).open("r", encoding="utf-8") as rules_file:
        configuration = json.load(rules_file)

    if not isinstance(configuration, dict):
        raise ValueError("thresholds.json must contain a JSON object.")

    tests = configuration.get("critical_ranges")
    if not isinstance(tests, dict) or not tests:
        raise ValueError(
            "thresholds.json must contain a non-empty 'critical_ranges' object."
        )

    validated = {}
    for test_name, rule in tests.items():
        if not isinstance(test_name, str) or not test_name.strip():
            raise ValueError("Each test range needs a non-empty test name.")
        if not isinstance(rule, dict):
            raise ValueError(f"The range for {test_name!r} must be an object.")

        thresholds = {}
        for bound in ("low", "high"):
            value = rule.get(bound)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"The {bound} threshold for {test_name!r} must be numeric.")
                if not math.isfinite(value):
                    raise ValueError(f"The {bound} threshold for {test_name!r} must be finite.")
                thresholds[bound] = value

        if not thresholds:
            raise ValueError(f"The range for {test_name!r} needs a low or high threshold.")
        if (
            "low" in thresholds
            and "high" in thresholds
            and thresholds["low"] >= thresholds["high"]
        ):
            raise ValueError(f"The low threshold must be below the high threshold for {test_name!r}.")

        unit = rule.get("unit", "")
        if not isinstance(unit, str):
            raise ValueError(f"The unit for {test_name!r} must be a string.")
        thresholds["unit"] = unit
        validated[test_name] = thresholds

    return validated
