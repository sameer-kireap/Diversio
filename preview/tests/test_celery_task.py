import base64
from django.test import SimpleTestCase, override_settings
from preview.tasks import process_hris_csv_task

class CeleryTaskTests(SimpleTestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_celery_task_processes_sample_csv_eagerly(self):
        sample_csv = (
            "employee_id,employee_name,email,manager_id,manager_email,department\n"
            "DIV-100,Avery Morgan,demo.avery@diversio.com,,,Executive\n"
            "DIV-200,Sofia Chen,demo.sofia@diversio.com,DIV-100,,Engineering\n"
            "DIV-300,Casey Bell,demo.casey@diversio.com,DIV-999,,Operations\n"
        ).encode("utf-8")

        b64_content = base64.b64encode(sample_csv).decode("utf-8")
        result = process_hris_csv_task(b64_content)

        self.assertTrue(result["success"])
        self.assertEqual(result["total_source_rows"], 3)
        self.assertEqual(len(result["accepted_employees"]), 3)
        self.assertEqual(len(result["root_employees"]), 1)
        self.assertEqual(result["root_employees"][0]["employee_id"], "DIV-100")
        # Manager error for DIV-999 → appears in manager_errors, not identity_errors
        self.assertEqual(len(result["identity_errors"]), 0)
        self.assertEqual(len(result["manager_errors"]), 1)
        self.assertIn("DIV-999", result["manager_errors"][0]["message"])
        # Combined validation_errors should equal identity + manager
        self.assertEqual(
            len(result["validation_errors"]),
            len(result["identity_errors"]) + len(result["manager_errors"]),
        )
