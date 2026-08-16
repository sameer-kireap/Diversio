import csv
import io
from typing import List

from .models import RawRecord

REQUIRED_HEADERS = {
    "employee_id",
    "employee_name",
    "email",
    "manager_id",
    "manager_email",
    "department",
}

class ParseError(Exception):
    pass

def parse_hris_csv(file_content_bytes: bytes) -> List[RawRecord]:
    """Parse raw bytes into a list of RawRecords.

    Raises ParseError for file-level failures (bad encoding, missing headers).
    Row-level anomalies such as missing identity fields are handled downstream
    by validate_identities(); this parser only surfaces structural problems.
    """
    # UTF-8 with optional Byte Order Mark handling per RFC 3629
    try:
        text_content = file_content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("File encoding error: Upload must be valid UTF-8.") from exc

    stream = io.StringIO(text_content)

    # Standard CSV parsing conforming to RFC 4180
    try:
        reader = csv.DictReader(stream)
    except Exception as exc:
        raise ParseError(f"Malformed CSV structure: {str(exc)}") from exc

    if reader.fieldnames is None:
        raise ParseError("CSV file is empty or missing headers.")

    normalized_field_map = {
        name.lstrip("\ufeff").strip().lower(): name
        for name in reader.fieldnames
        if name
    }
    missing_headers = REQUIRED_HEADERS - set(normalized_field_map.keys())

    if missing_headers:
        missing_str = ", ".join(sorted(missing_headers))
        raise ParseError(f"CSV header validation failed. Missing required columns: {missing_str}")

    records: List[RawRecord] = []

    # 1-indexed source row counter, offset by 1 for CSV header row
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(str(val).strip() for val in row.values() if val is not None):
            continue

        raw_dict = {k: v if v is not None else "" for k, v in row.items()}

        emp_id = raw_dict.get(normalized_field_map["employee_id"], "").strip()
        emp_name = raw_dict.get(normalized_field_map["employee_name"], "").strip()
        email = raw_dict.get(normalized_field_map["email"], "").strip().lower()
        mgr_id = raw_dict.get(normalized_field_map["manager_id"], "").strip()
        mgr_email = raw_dict.get(normalized_field_map["manager_email"], "").strip().lower()
        dept = raw_dict.get(normalized_field_map["department"], "").strip()

        records.append(
            RawRecord(
                source_row_number=line_number,
                employee_id=emp_id,
                employee_name=emp_name,
                email=email,
                manager_id=mgr_id,
                manager_email=mgr_email,
                department=dept,
            )
        )

    return records
