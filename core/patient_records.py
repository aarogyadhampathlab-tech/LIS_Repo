from datetime import datetime


def _patient_record_key(patient_id, patient_name):
    barcode = str(patient_id or "").strip()
    if barcode and barcode != "UNKNOWN":
        return ("barcode", barcode)
    return ("name", str(patient_name or "").strip().casefold())


def _is_missing_result(record):
    return str(record[3] or "").strip().casefold() == "missing_result"


def _missing_result_key(record):
    return (
        _patient_record_key(record[0], record[1]),
        record[2].casefold(),
    )


def index_missing_results(records):
    missing_records = {}
    for record in records:
        if _is_missing_result(record):
            missing_records.setdefault(_missing_result_key(record), []).append(record)
    return missing_records


def track_missing_result(record, missing_records):
    if _is_missing_result(record):
        missing_records.setdefault(_missing_result_key(record), []).append(record)


def remove_replaced_missing_results(
    records, received_at_by_record, incoming_record, missing_records=None
):
    patient_id, patient_name, test_name, result = incoming_record
    normalized_result = str(result or "").strip().casefold()
    if (
        not normalized_result
        or normalized_result == "missing_result"
        or "no result" in normalized_result
        or "no-result" in normalized_result
    ):
        return

    patient_key = _patient_record_key(patient_id, patient_name)
    if missing_records is not None:
        matching_records = missing_records.pop(
            (patient_key, test_name.casefold()), ()
        )
        for record in matching_records:
            try:
                records.remove(record)
            except ValueError:
                continue
            received_at_by_record.pop(record, None)
        return

    replaced_missing = [
        record
        for record in records
        if _patient_record_key(record[0], record[1]) == patient_key
        and record[2].casefold() == test_name.casefold()
        and str(record[3] or "").strip().casefold() == "missing_result"
    ]
    for record in replaced_missing:
        records.remove(record)
        received_at_by_record.pop(record, None)


def patient_freshness(received_at, now):
    age_seconds = (now - received_at).total_seconds()
    if age_seconds < 60 * 60:
        return "LATEST"
    if age_seconds < 24 * 60 * 60:
        return "OLD"
    return "LONG AGO"
