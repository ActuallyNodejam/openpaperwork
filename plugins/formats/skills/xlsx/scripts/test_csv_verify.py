import csv
import hashlib
import pathlib
import tempfile
import unittest
from csv_verify import verify


class VerifyCSV(unittest.TestCase):
    def test_literal_newlines_fail_without_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "bad.csv"
            path.write_bytes(b"item,price\\nchair,12\\ntable,")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            result = verify(path, ["item", "price"], 2)
            self.assertFalse(result["ok"])
            self.assertEqual(result["data_rows"], 0)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_valid_quoted_multiline_and_blank_price(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "good.csv"
            with path.open("w", newline="", encoding="utf-8-sig") as stream:
                csv.writer(stream).writerows([["item", "price"],
                    ["chair, blue", "12"], ["two\nline label", ""], [r"literal\nlabel", "5"]])
            self.assertTrue(verify(path, ["item", "price"], 3)["ok"])

    def test_ragged_and_missing_records(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "ragged.csv"
            path.write_text("item,price\nchair,12,extra\n", encoding="utf-8")
            result = verify(path, ["item", "price"], 2)
            self.assertEqual([x["kind"] for x in result["errors"]], ["width", "row_count"])

    def test_semicolon_and_header_only(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "empty.csv"
            path.write_text("item;price\n", encoding="utf-8")
            self.assertTrue(verify(path, ["item", "price"], 0, delimiter=";")["ok"])


if __name__ == "__main__":
    unittest.main()
