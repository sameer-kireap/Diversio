from django.test import SimpleTestCase
from preview.domain.hierarchy import analyze_hierarchy
from preview.domain.models import Employee

class HierarchyAnalyzerTests(SimpleTestCase):
    def test_manager_resolution_conflict_and_missing_manager(self):
        accepted = [
            Employee(2, "DIV-100", "Avery Root", "avery@diversio.com", "Exec", None, None),
            Employee(3, "DIV-200", "Bob Mgr", "bob@diversio.com", "Eng", "DIV-100", None),
            Employee(4, "DIV-300", "Charlie Conflict", "charlie@diversio.com", "Eng", "DIV-100", "bob@diversio.com"),
            Employee(5, "DIV-400", "Dave Missing", "dave@diversio.com", "Eng", "DIV-999", None),
        ]

        roots, mgr_summaries, cycles, errors = analyze_hierarchy(accepted)

        # Roots: Only DIV-100 (Avery) has no manager fields
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].employee_id, "DIV-100")

        # Manager summaries: DIV-100 has 1 report (Bob)
        self.assertEqual(len(mgr_summaries), 1)
        self.assertEqual(mgr_summaries[0].manager_id, "DIV-100")
        self.assertEqual(mgr_summaries[0].direct_report_count, 1)

        # Errors: Charlie (Conflict: ID points to Avery, Email points to Bob) and Dave (Missing DIV-999)
        self.assertEqual(len(errors), 2)
        err_messages = [err.message for err in errors]
        self.assertTrue(any("Manager reference conflict" in msg for msg in err_messages))
        self.assertTrue(any("Manager ID 'DIV-999' not found" in msg for msg in err_messages))

    def test_cycle_detection_excludes_employees_reporting_into_a_cycle(self):
        # Topology:
        # A -> B -> C -> A (Cycle of A, B, C)
        # D -> A (D reports to A, but D is NOT in the loop)
        accepted = [
            Employee(2, "DIV-A", "Alice", "alice@diversio.com", "Research", "DIV-B", None),
            Employee(3, "DIV-B", "Bob", "bob@diversio.com", "Research", "DIV-C", None),
            Employee(4, "DIV-C", "Charlie", "charlie@diversio.com", "Research", "DIV-A", None),
            Employee(5, "DIV-D", "Dave External", "dave@diversio.com", "Research", "DIV-A", None),
        ]

        roots, mgr_summaries, cycles, errors = analyze_hierarchy(accepted)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(cycles), 3)

        cycle_ids = {emp.employee_id for emp in cycles}
        self.assertEqual(cycle_ids, {"DIV-A", "DIV-B", "DIV-C"})
        self.assertNotIn("DIV-D", cycle_ids)

    def test_both_fields_supplied_manager_id_not_found(self):
        """Case 4 sub-path: both manager_id and manager_email provided,
        but manager_id resolves to nobody while manager_email resolves successfully.
        Per spec both must identify the same employee → error."""
        accepted = [
            Employee(2, "DIV-100", "Root", "root@diversio.com", "Exec", None, None),
            Employee(3, "DIV-200", "Sub", "sub@diversio.com", "Eng", "DIV-NONEXIST", "root@diversio.com"),
        ]

        roots, mgr_summaries, cycles, errors = analyze_hierarchy(accepted)

        self.assertEqual(len(errors), 1)
        self.assertIn("DIV-NONEXIST", errors[0].message)
        # DIV-200 must not appear as a root (has manager fields) and not produce a relationship
        self.assertFalse(any(e.employee_id == "DIV-200" for e in roots))
        self.assertEqual(len(mgr_summaries), 0)

    def test_both_fields_supplied_manager_email_not_found(self):
        """Case 4 sub-path: both manager_id and manager_email provided,
        but manager_email resolves to nobody while manager_id resolves successfully.
        Per spec both must identify the same employee → error."""
        accepted = [
            Employee(2, "DIV-100", "Root", "root@diversio.com", "Exec", None, None),
            Employee(3, "DIV-200", "Sub", "sub@diversio.com", "Eng", "DIV-100", "nobody@diversio.com"),
        ]

        roots, mgr_summaries, cycles, errors = analyze_hierarchy(accepted)

        self.assertEqual(len(errors), 1)
        self.assertIn("nobody@diversio.com", errors[0].message)
        # DIV-200 must not appear as a root and not produce a reporting relationship
        self.assertFalse(any(e.employee_id == "DIV-200" for e in roots))
        self.assertEqual(len(mgr_summaries), 0)
