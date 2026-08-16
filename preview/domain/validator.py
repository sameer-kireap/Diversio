from collections import Counter
from typing import List, Tuple

from .models import Employee, RawRecord, ValidationError

def validate_identities(records: List[RawRecord]) -> Tuple[List[Employee], List[ValidationError]]:

    id_counts = Counter(r.employee_id for r in records if r.employee_id)
    email_counts = Counter(r.email for r in records if r.email)

    accepted_employees: List[Employee] = []
    validation_errors: List[ValidationError] = []

    for record in records:
        record_errors: List[str] = []

        if not record.employee_id:
            record_errors.append("Missing required field: employee_id is empty.")
        elif id_counts[record.employee_id] > 1:
            record_errors.append(
                f"Duplicate employee_id '{record.employee_id}': ID occurs {id_counts[record.employee_id]} times in upload."
            )

        if not record.email:
            record_errors.append("Missing required field: email is empty.")
        elif email_counts[record.email] > 1:
            record_errors.append(
                f"Duplicate email '{record.email}': email occurs {email_counts[record.email]} times in upload."
            )

        if record_errors:
            raw_dict = {
                "employee_id": record.employee_id,
                "employee_name": record.employee_name,
                "email": record.email,
                "manager_id": record.manager_id,
                "manager_email": record.manager_email,
                "department": record.department,
            }
            for err_msg in record_errors:
                validation_errors.append(
                    ValidationError(
                        source_row_number=record.source_row_number,
                        error_type="Identity Validation Error",
                        message=err_msg,
                        raw_record=raw_dict,
                    )
                )
        else:
            accepted_employees.append(
                Employee(
                    source_row_number=record.source_row_number,
                    employee_id=record.employee_id,
                    employee_name=record.employee_name,
                    email=record.email,
                    department=record.department,
                    manager_id=record.manager_id or None,
                    manager_email=record.manager_email or None,
                )
            )

    return accepted_employees, validation_errors
