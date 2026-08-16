from django.test import SimpleTestCase
from preview.domain.models import RawRecord
from preview.domain.validator import validate_identities

class IdentityValidatorTests(SimpleTestCase):
    def test_duplicate_employee_id_invalidates_all_sharing_rows(self):
        records = [
            RawRecord(2, "DIV-100", "Alice", "alice@diversio.com", "", "", "Eng"),
            RawRecord(3, "DIV-100", "Alice Duplicate", "alice.dup@diversio.com", "", "", "Eng"),
            RawRecord(4, "DIV-200", "Bob", "bob@diversio.com", "", "", "Product"),
        ]

        accepted, errors = validate_identities(records)

        # Both Row 2 and Row 3 must be invalidated due to duplicate ID DIV-100
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0].employee_id, "DIV-200")

        self.assertEqual(len(errors), 2)
        error_rows = [err.source_row_number for err in errors]
        self.assertIn(2, error_rows)
        self.assertIn(3, error_rows)
        self.assertTrue(all("Duplicate employee_id" in err.message for err in errors))

    def test_missing_required_fields_produces_error(self):
        records = [
            RawRecord(2, "", "No ID", "noid@diversio.com", "", "", "Eng"),
            RawRecord(3, "DIV-300", "No Email", "", "", "", "Eng"),
        ]

        accepted, errors = validate_identities(records)
        self.assertEqual(len(accepted), 0)
        self.assertEqual(len(errors), 2)
