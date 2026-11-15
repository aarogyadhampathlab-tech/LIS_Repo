import csv
from pathlib import Path


def load_patient_names(csv_path):
    """Load barcode-to-name entries, keeping the latest row for each barcode."""
    patient_names = {}
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as patient_file:
        reader = csv.reader(patient_file)
        headers = [header.strip().casefold() for header in next(reader, [])]
        try:
            barcode_index = headers.index("barcode")
            name_index = headers.index("patient name")
        except ValueError as error:
            raise ValueError(
                "Patient CSV must contain Barcode and Patient Name columns"
            ) from error

        for row in reader:
            if max(barcode_index, name_index) >= len(row):
                continue
            barcode = row[barcode_index].strip()
            patient_name = row[name_index].strip()
            if barcode and patient_name:
                patient_names[barcode] = patient_name

    return patient_names
