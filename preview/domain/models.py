from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class RawRecord:
    source_row_number: int
    employee_id: str
    employee_name: str
    email: str
    manager_id: str
    manager_email: str
    department: str

@dataclass(frozen=True)
class ValidationError:
    source_row_number: int
    error_type: str
    message: str
    raw_record: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class Employee:
    source_row_number: int
    employee_id: str
    employee_name: str
    email: str
    department: str
    manager_id: Optional[str] = None
    manager_email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ManagerReportSummary:
    manager_id: str
    manager_name: str
    manager_email: str
    direct_report_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ImportPreviewResult:
    total_source_rows: int
    accepted_employees: List[Employee]
    # identity_errors: rows rejected from analysis (duplicate ID/email, missing fields)
    identity_errors: List[ValidationError]
    # manager_errors: employees who remain accepted but have an unresolvable manager ref
    manager_errors: List[ValidationError]
    # validation_errors: identity_errors + manager_errors combined, sorted by row number
    validation_errors: List[ValidationError]
    root_employees: List[Employee]
    manager_report_summaries: List[ManagerReportSummary]
    cycle_members: List[Employee]
    raw_records: List[RawRecord]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_source_rows": self.total_source_rows,
            "accepted_employees": [emp.to_dict() for emp in self.accepted_employees],
            "identity_errors": [err.to_dict() for err in self.identity_errors],
            "manager_errors": [err.to_dict() for err in self.manager_errors],
            "validation_errors": [err.to_dict() for err in self.validation_errors],
            "root_employees": [emp.to_dict() for emp in self.root_employees],
            "manager_report_summaries": [m.to_dict() for m in self.manager_report_summaries],
            "cycle_members": [emp.to_dict() for emp in self.cycle_members],
            "raw_records": [asdict(r) for r in self.raw_records],
        }
