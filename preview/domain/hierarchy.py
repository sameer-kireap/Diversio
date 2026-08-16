from typing import Dict, List, Optional, Set, Tuple

from .models import Employee, ManagerReportSummary, ValidationError

COLOR_WHITE = 0
COLOR_GRAY = 1
COLOR_BLACK = 2

def analyze_hierarchy(
    accepted_employees: List[Employee],
) -> Tuple[List[Employee], List[ManagerReportSummary], List[Employee], List[ValidationError]]:

    accepted_by_id: Dict[str, Employee] = {emp.employee_id: emp for emp in accepted_employees}
    accepted_by_email: Dict[str, Employee] = {emp.email: emp for emp in accepted_employees}

    root_employees: List[Employee] = []
    manager_errors: List[ValidationError] = []
    
    # Adjacency representations for hierarchy graph
    # child_to_manager: emp_id -> manager_id (for graph cycle detection)
    # direct_reports: manager_id -> List[Employee] (for report counts)
    child_to_manager: Dict[str, str] = {}
    direct_reports: Dict[str, List[Employee]] = {}

    for emp in accepted_employees:
        has_id_ref = bool(emp.manager_id)
        has_email_ref = bool(emp.manager_email)

        # Case 1: Root employee (no manager references provided)
        if not has_id_ref and not has_email_ref:
            root_employees.append(emp)
            continue

        raw_dict = {
            "employee_id": emp.employee_id,
            "employee_name": emp.employee_name,
            "email": emp.email,
            "manager_id": emp.manager_id or "",
            "manager_email": emp.manager_email or "",
            "department": emp.department,
        }

        resolved_mgr: Optional[Employee] = None

        # Case 2: Only manager_id provided
        if has_id_ref and not has_email_ref:
            resolved_mgr = accepted_by_id.get(emp.manager_id)
            if resolved_mgr is None:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=f"Manager ID '{emp.manager_id}' not found in accepted employees.",
                        raw_record=raw_dict,
                    )
                )
                continue

        # Case 3: Only manager_email provided
        elif has_email_ref and not has_id_ref:
            resolved_mgr = accepted_by_email.get(emp.manager_email)
            if resolved_mgr is None:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=f"Manager email '{emp.manager_email}' not found in accepted employees.",
                        raw_record=raw_dict,
                    )
                )
                continue

        # Case 4: Both manager_id and manager_email provided
        else:
            mgr_by_id = accepted_by_id.get(emp.manager_id)
            mgr_by_email = accepted_by_email.get(emp.manager_email)

            if mgr_by_id is None and mgr_by_email is None:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=f"Neither manager_id '{emp.manager_id}' nor manager_email '{emp.manager_email}' were found.",
                        raw_record=raw_dict,
                    )
                )
                continue
            elif mgr_by_id is None:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=f"Manager ID '{emp.manager_id}' not found, but manager_email resolved to '{mgr_by_email.employee_name}'.",
                        raw_record=raw_dict,
                    )
                )
                continue
            elif mgr_by_email is None:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=f"Manager email '{emp.manager_email}' not found, but manager_id resolved to '{mgr_by_id.employee_name}'.",
                        raw_record=raw_dict,
                    )
                )
                continue

            if mgr_by_id.employee_id != mgr_by_email.employee_id:
                manager_errors.append(
                    ValidationError(
                        source_row_number=emp.source_row_number,
                        error_type="Manager Resolution Error",
                        message=(
                            f"Manager reference conflict: manager_id '{emp.manager_id}' points to "
                            f"'{mgr_by_id.employee_name}' ({mgr_by_id.email}), but manager_email '{emp.manager_email}' "
                            f"points to '{mgr_by_email.employee_name}' ({mgr_by_email.employee_id})."
                        ),
                        raw_record=raw_dict,
                    )
                )
                continue

            resolved_mgr = mgr_by_id

        # Self-management validation
        if resolved_mgr.employee_id == emp.employee_id:
            manager_errors.append(
                ValidationError(
                    source_row_number=emp.source_row_number,
                    error_type="Manager Resolution Error",
                    message=f"Self-management detected: Employee '{emp.employee_id}' cannot be their own manager.",
                    raw_record=raw_dict,
                )
            )
            continue

        # Record valid manager relationship
        child_to_manager[emp.employee_id] = resolved_mgr.employee_id
        direct_reports.setdefault(resolved_mgr.employee_id, []).append(emp)

    # Calculate manager report summaries
    manager_summaries: List[ManagerReportSummary] = []
    for mgr_id, reports in direct_reports.items():
        mgr_obj = accepted_by_id[mgr_id]
        manager_summaries.append(
            ManagerReportSummary(
                manager_id=mgr_obj.employee_id,
                manager_name=mgr_obj.employee_name,
                manager_email=mgr_obj.email,
                direct_report_count=len(reports),
            )
        )
    manager_summaries.sort(key=lambda s: s.direct_report_count, reverse=True)

    # Graph cycle detection via 3-state Depth First Search (DFS)
    cycle_member_ids: Set[str] = set()
    visited_colors: Dict[str, int] = {emp.employee_id: COLOR_WHITE for emp in accepted_employees}

    for start_id in accepted_by_id:
        if visited_colors[start_id] != COLOR_WHITE:
            continue

        path_stack: List[str] = []
        path_set: Set[str] = set()

        curr: Optional[str] = start_id
        while curr is not None:
            if visited_colors[curr] == COLOR_WHITE:
                visited_colors[curr] = COLOR_GRAY
                path_stack.append(curr)
                path_set.add(curr)

                next_mgr = child_to_manager.get(curr)
                if next_mgr is None:
                    # Reached root node or node with manager error
                    while path_stack:
                        node = path_stack.pop()
                        visited_colors[node] = COLOR_BLACK
                    curr = None
                elif visited_colors[next_mgr] == COLOR_GRAY:
                    # Cycle detected: extract nodes in cycle loop
                    cycle_start_index = path_stack.index(next_mgr)
                    loop_nodes = path_stack[cycle_start_index:]
                    cycle_member_ids.update(loop_nodes)

                    while path_stack:
                        node = path_stack.pop()
                        visited_colors[node] = COLOR_BLACK
                    curr = None
                elif visited_colors[next_mgr] == COLOR_BLACK:
                    # Reached an already fully explored path
                    while path_stack:
                        node = path_stack.pop()
                        visited_colors[node] = COLOR_BLACK
                    curr = None
                else:
                    curr = next_mgr

    cycle_members = [emp for emp in accepted_employees if emp.employee_id in cycle_member_ids]

    return root_employees, manager_summaries, cycle_members, manager_errors
