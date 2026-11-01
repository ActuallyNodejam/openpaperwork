"""A poster's file name keeps the fair's letters as plain letters (timed run c16, 2026-10-25)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poster import slugify  # noqa: E402


class Names(unittest.TestCase):
    def test_marked_letters_keep_their_base_letter(self):
        self.assertEqual(slugify("Resemässan Göteborg 2027"), "resemassan-goteborg-2027")
        self.assertEqual(slugify("Möbelmesse Köln"), "mobelmesse-koln")
        self.assertEqual(slugify("Straße Ærø Łódź"), "strasse-aero-lodz")

    def test_plain_names_are_as_before(self):
        self.assertEqual(slugify("Munich 2026"), "munich-2026")
        self.assertEqual(slugify(""), "")


if __name__ == "__main__":
    unittest.main()
