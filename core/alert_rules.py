import json
import math
import os
import re
import tempfile
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

    return validate_alert_rules(configuration)


def validate_alert_rules(configuration):
    if not isinstance(configuration, dict):
        raise ValueError("thresholds.json must contain a JSON object.")

    tests = configuration.get("critical_ranges")
    if not isinstance(tests, dict):
        raise ValueError("thresholds.json must contain a 'critical_ranges' object.")

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

        unit = rule.get("unit", "")
        if not isinstance(unit, str):
            raise ValueError(f"The unit for {test_name!r} must be a string.")
        thresholds["unit"] = unit
        enabled = rule.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"The enabled setting for {test_name!r} must be true or false.")
        if not any(bound in thresholds for bound in ("low", "high")) and enabled:
            raise ValueError(
                f"The range for {test_name!r} needs a low or high threshold "
                "before its alert can be enabled."
            )
        if (
            "low" in thresholds
            and "high" in thresholds
            and thresholds["low"] >= thresholds["high"]
        ):
            raise ValueError(f"The low threshold must be below the high threshold for {test_name!r}.")
        thresholds["enabled"] = enabled
        validated[test_name] = thresholds

    return validated


def save_alert_rules(alert_rules, path=ALERT_RULES_PATH):
    validated = validate_alert_rules({"critical_ranges": alert_rules})
    configuration_path = Path(path)
    with configuration_path.open("r", encoding="utf-8") as rules_file:
        existing_configuration = json.load(rules_file)
    if not isinstance(existing_configuration, dict):
        raise ValueError("thresholds.json must contain a JSON object.")

    configuration = {
        "_note": existing_configuration.get(
            "_note",
            "DEMO ALERT TRIGGERS ONLY. Confirm thresholds and units with "
            "the laboratory director before clinical use.",
        ),
        "critical_ranges": validated,
    }

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=configuration_path.parent,
            suffix=".tmp",
            delete=False,
        ) as rules_file:
            temporary_path = Path(rules_file.name)
            json.dump(configuration, rules_file, indent=4)
            rules_file.write("\n")
        os.replace(temporary_path, configuration_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return validated
