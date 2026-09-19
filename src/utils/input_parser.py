"""Input parsing utility for phone numbers and full CRM CSV column passthrough."""
import csv
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


COMMON_PHONE_HEADERS = {
    "phone",
    "phonenumber",
    "phone_number",
    "mobile",
    "cell",
    "telephone",
    "tel",
    "contact",
    "num",
    "numero",
    "phone_1",
    "work_phone",
    "direct_phone",
}


@dataclass
class InputPhoneRecord:
    """Individual phone entry preserving custom CRM columns from CSV."""
    raw_number: str
    custom_fields: Optional[Dict[str, Any]] = None


def parse_csv_records(csv_text: str) -> List[InputPhoneRecord]:
    """Extract phone numbers and preserve all other CSV columns for CRM passthrough."""
    if not csv_text or not csv_text.strip():
        return []

    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    if not lines:
        return []

    # Detect delimiter
    first_line = lines[0]
    delimiter = ","
    for d in [",", ";", "\t", "|"]:
        if d in first_line:
            delimiter = d
            break

    reader = csv.reader(io.StringIO(csv_text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return []

    first_row = [c.strip() for c in rows[0]]
    phone_col_idx = -1
    for idx, col_name in enumerate(first_row):
        normalized_header = col_name.lower().replace(" ", "_")
        if normalized_header in COMMON_PHONE_HEADERS:
            phone_col_idx = idx
            break

    has_header = (phone_col_idx != -1)
    if not has_header:
        # Default to first column if no explicit phone header
        phone_col_idx = 0
        headers = [f"column_{i+1}" for i in range(len(first_row))]
        start_row = 0
    else:
        headers = first_row
        start_row = 1

    records: List[InputPhoneRecord] = []
    for row in rows[start_row:]:
        if not row or not any(row):
            continue

        if len(row) > phone_col_idx:
            raw_phone = row[phone_col_idx].strip()
            if not raw_phone:
                continue

            # Skip row if it repeats header name
            if raw_phone.lower().replace(" ", "_") in COMMON_PHONE_HEADERS:
                continue

            # Collect other columns for CRM passthrough
            custom_data: Dict[str, Any] = {}
            for col_idx, col_val in enumerate(row):
                if col_idx != phone_col_idx:
                    col_header = headers[col_idx] if col_idx < len(headers) else f"column_{col_idx+1}"
                    custom_data[col_header] = col_val.strip()

            records.append(InputPhoneRecord(
                raw_number=raw_phone,
                custom_fields=custom_data if custom_data else None
            ))

    return records


def parse_csv_phone_numbers(csv_text: str) -> List[str]:
    """Extract raw phone number list from CSV text (convenience helper)."""
    return [r.raw_number for r in parse_csv_records(csv_text)]


def normalize_input_records(
    phone_numbers: Optional[List[str]],
    csv_content: Optional[str]
) -> List[InputPhoneRecord]:
    """Combine array inputs and CSV records, preserving order and deduplicating."""
    combined: List[InputPhoneRecord] = []

    if phone_numbers:
        for p in phone_numbers:
            if isinstance(p, str) and p.strip():
                combined.append(InputPhoneRecord(raw_number=p.strip(), custom_fields=None))

    if csv_content:
        csv_records = parse_csv_records(csv_content)
        combined.extend(csv_records)

    seen = set()
    deduped: List[InputPhoneRecord] = []
    for record in combined:
        if record.raw_number not in seen:
            seen.add(record.raw_number)
            deduped.append(record)

    return deduped


def normalize_phone_input_list(
    phone_numbers: Optional[List[str]],
    csv_content: Optional[str]
) -> List[str]:
    """Combine and deduplicate phone numbers as plain strings (backward-compatible)."""
    return [r.raw_number for r in normalize_input_records(phone_numbers, csv_content)]
