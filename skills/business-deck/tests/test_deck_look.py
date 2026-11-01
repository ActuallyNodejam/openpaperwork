"""deck_look.py never hands two runs the same folder: each run writes its pages and its sheet into a folder it
made itself inside the one it was given, so a reader of the printed paths cannot be shown another run's sheet,
even when both are pointed at one shared folder (the shape of /tmp/look on a busy machine)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "scripts" / "deck_look.py"

try:
    from PIL import Image
except ImportError:                                  # the script itself runs through uv; the test needs Pillow to make a PDF
    Image = None


def pdf(path, colour, pages):
    ims = [Image.new("RGB", (320, 180), colour) for _ in range(pages)]
    ims[0].save(path, "PDF", save_all=True, append_images=ims[1:])
    return str(path)


def look(deck, folder, sheet="sheet.jpg"):
    out = subprocess.run([sys.executable, str(SCRIPT), deck, str(folder), "--sheet", sheet, "--width", "200"],
                         capture_output=True, text=True, check=True).stdout.split()
    return [Path(line) for line in out]


@unittest.skipIf(Image is None, "Pillow is not here")
class RunsDoNotShare(unittest.TestCase):
    def test_two_runs_in_one_folder_see_only_their_own_sheet(self):
        with tempfile.TemporaryDirectory(prefix="decklook-test-") as tmp:
            tmp = Path(tmp)
            shared = tmp / "look"
            first = look(pdf(tmp / "a.pdf", "red", 2), shared)
            second = look(pdf(tmp / "b.pdf", "blue", 5), shared)
            sheet_a = [p for p in first if p.name == "sheet.jpg"][0]
            sheet_b = [p for p in second if p.name == "sheet.jpg"][0]
            self.assertNotEqual(sheet_a.parent, sheet_b.parent)
            for p in first + second:
                self.assertEqual(p.parent.parent, shared)       # inside the folder given, never beside it
            # a's folder still holds a's two pages and a red sheet after b has run
            self.assertEqual(sorted(p.name for p in sheet_a.parent.iterdir()), ["page-01.png", "page-02.png", "sheet.jpg"])
            self.assertEqual(len(list(sheet_b.parent.glob("page-*.png"))), 5)
            self.assertGreater(Image.open(sheet_a).getpixel((60, 60))[0], 200)   # red
            self.assertGreater(Image.open(sheet_b).getpixel((60, 60))[2], 200)   # blue

    def test_a_sheet_name_with_a_folder_stays_in_the_run(self):
        with tempfile.TemporaryDirectory(prefix="decklook-test-") as tmp:
            tmp = Path(tmp)
            out = look(pdf(tmp / "a.pdf", "red", 1), tmp / "look", sheet="/tmp/look/sheet.jpg")
            self.assertTrue(all(p.is_relative_to(tmp / "look") for p in out), out)


if __name__ == "__main__":
    unittest.main()
