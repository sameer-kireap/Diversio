from django.test import SimpleTestCase
from preview.domain.parser import ParseError, parse_hris_csv

class CSVParserTests(SimpleTestCase):
    def test_parses_valid_csv_with_utf8_bom_and_quoted_commas(self):
        csv_data = (
            b"\xef\xbb\xbfemployee_id,employee_name,email,manager_id,manager_email,department\n"
            b'DIV-101,"Alvarez, Ren\xc3\xa9e",DEMO.RENEE@DIVERSIO.COM,DIV-100,,Engineering\n'
            b' DIV-102 , Hana Patel , DEMO.HANA@DIVERSIO.COM , DIV-101 , demo.renee@diversio.com , Product \n'
        )

        records = parse_hris_csv(csv_data)

        self.assertEqual(len(records), 2)

        r1 = records[0]
        self.assertEqual(r1.employee_id, "DIV-101")
        self.assertEqual(r1.employee_name, "Alvarez, Renée")
        self.assertEqual(r1.email, "demo.renee@diversio.com")
        self.assertEqual(r1.manager_id, "DIV-100")
        self.assertEqual(r1.department, "Engineering")

        r2 = records[1]
        self.assertEqual(r2.employee_id, "DIV-102")
        self.assertEqual(r2.employee_name, "Hana Patel")
        self.assertEqual(r2.email, "demo.hana@diversio.com")
        self.assertEqual(r2.manager_email, "demo.renee@diversio.com")
        self.assertEqual(r2.department, "Product")

    def test_missing_required_header_raises_parse_error(self):
        invalid_csv = "employee_id,email,department\nDIV-101,a@b.com,Engineering\n".encode("utf-8")
        with self.assertRaises(ParseError) as ctx:
            parse_hris_csv(invalid_csv)
        self.assertIn("Missing required columns", str(ctx.exception))

    def test_non_utf8_binary_raises_parse_error_not_unhandled_exception(self):
        """A binary file that is not valid UTF-8 must produce a clean ParseError,
        not an unhandled UnicodeDecodeError propagating to the caller."""
        # Latin-1 byte 0xFF is invalid in UTF-8
        non_utf8_bytes = b"\xff\xfe invalid latin-1 content"
        with self.assertRaises(ParseError) as ctx:
            parse_hris_csv(non_utf8_bytes)
        self.assertIn("encoding error", str(ctx.exception).lower())

    def test_empty_file_raises_parse_error(self):
        """An empty upload must raise ParseError, not return an empty list silently."""
        with self.assertRaises(ParseError) as ctx:
            parse_hris_csv(b"")
        self.assertIn("empty", str(ctx.exception).lower())
