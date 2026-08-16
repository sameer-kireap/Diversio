import base64
from celery import shared_task
from django.core.cache import cache

from .domain.hierarchy import analyze_hierarchy
from .domain.models import ImportPreviewResult
from .domain.parser import ParseError, parse_hris_csv
from .domain.validator import validate_identities

@shared_task(bind=True)
def process_hris_csv_task(self, file_content_b64: str) -> dict:

    task_id = self.request.id or "sync-eager-task"

    try:
        file_content_bytes = base64.b64decode(file_content_b64.encode("utf-8"))
        raw_records = parse_hris_csv(file_content_bytes)
        accepted_employees, identity_errors = validate_identities(raw_records)
        root_employees, manager_summaries, cycle_members, manager_errors = analyze_hierarchy(accepted_employees)

        # Keep identity and manager errors separate so the UI can label them accurately.
        # Identity errors quarantine employees from analysis; manager errors do not.
        all_errors = identity_errors + manager_errors
        all_errors.sort(key=lambda err: err.source_row_number)

        result = ImportPreviewResult(
            total_source_rows=len(raw_records),
            accepted_employees=accepted_employees,
            identity_errors=identity_errors,
            manager_errors=manager_errors,
            validation_errors=all_errors,
            root_employees=root_employees,
            manager_report_summaries=manager_summaries,
            cycle_members=cycle_members,
            raw_records=raw_records,
        )

        result_dict = result.to_dict()
        result_dict["success"] = True

        # Store transient task result in cache for dashboard rendering.
        # RedisCache is shared across the Django web process and the Celery worker,
        # so this write is visible immediately to ResultsView.
        cache.set(f"hris_result_{task_id}", result_dict, timeout=3600)
        return result_dict

    except ParseError as parse_exc:
        error_payload = {
            "success": False,
            "error_title": "CSV Parsing Failure",
            "error_message": str(parse_exc),
        }
        cache.set(f"hris_result_{task_id}", error_payload, timeout=3600)
        return error_payload
    except Exception as exc:
        error_payload = {
            "success": False,
            "error_title": "Unhandled Import Processing Error",
            "error_message": f"An unexpected system error occurred: {str(exc)}",
        }
        cache.set(f"hris_result_{task_id}", error_payload, timeout=3600)
        return error_payload
