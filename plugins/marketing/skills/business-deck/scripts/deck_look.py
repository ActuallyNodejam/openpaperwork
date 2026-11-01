#!/usr/bin/env python3
"""The pages of a deck as pictures to look at: one PNG a page and one contact sheet.

    python3 deck_look.py <deck>.pdf <folder> [--sheet sheet.jpg] [--across 4] [--width 640]

Every run writes into a folder of its own, made fresh inside <folder> (look/run-ab12cd/), and the sheet goes
there too, whatever --sheet is called; so a reader of the paths it prints can only ever see this run's pictures,
even when <folder> is shared with other runs. Reads the PDF the builder wrote. Pages are drawn with PDFium (pypdfium2) when it is installed, else with
poppler's pdftoppm. Where this Python lacks Pillow the script runs itself through uv. Prints the files it wrote,
one a line.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile


def pages_of(pdf, width):
    """Every page of the PDF as a PIL image `width` pixels wide."""
    from PIL import Image
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pdfium = None
    if pdfium is not None:
        doc = pdfium.PdfDocument(pdf)
        out = []
        for page in doc:
            scale = width / float(page.get_width())
            out.append(page.render(scale=scale).to_pil().convert("RGB"))
        return out
    tool = shutil.which("pdftoppm")
    if not tool:
        raise SystemExit("neither pypdfium2 nor pdftoppm is here to draw the pages")
    with tempfile.TemporaryDirectory(prefix="deck-look-") as tmp:
        subprocess.run([tool, "-png", "-scale-to-x", str(width), "-scale-to-y", "-1", pdf, os.path.join(tmp, "p")],
                       check=True, capture_output=True)
        return [Image.open(f).convert("RGB").copy() for f in sorted(glob.glob(os.path.join(tmp, "p*.png")))]


def sheet(images, across, gap=16, ground="#9a9a9a"):
    from PIL import Image
    w, h = images[0].size
    down = (len(images) + across - 1) // across
    out = Image.new("RGB", (across * w + (across + 1) * gap, down * h + (down + 1) * gap), ground)
    for n, im in enumerate(images):
        out.paste(im, (gap + (n % across) * (w + gap), gap + (n // across) * (h + gap)))
    return out


def run_folder(folder):
    """A new, empty folder inside `folder` that no other run shares."""
    os.makedirs(folder, exist_ok=True)
    return tempfile.mkdtemp(prefix="run-", dir=folder)


def through_uv():
    """Pillow draws the pictures and PDFium the pages. Where this Python has neither and uv is installed, the same
    command runs again through uv, which fetches them into its own cache; once only. Without uv, one plain line."""
    try:
        import PIL  # noqa: F401
        return
    except ImportError as missing:
        if shutil.which("uv") and not os.environ.get("BDECK_UV"):
            os.environ["BDECK_UV"] = "1"
            sys.stdout.flush()
            os.execvp("uv", ["uv", "run", "--quiet", "--no-project", "--with", "pillow", "--with", "pypdfium2", "python3",
                             os.path.abspath(__file__)] + sys.argv[1:])
        raise SystemExit("deck_look.py needs Pillow to draw the pages, and this Python does not have it (%s). Install it once, "
                         "python3 -m pip install pillow pypdfium2, and run the same command again; the deck itself is "
                         "built and checked without it" % missing)


def main(argv=None):
    through_uv()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("folder")
    ap.add_argument("--sheet")
    ap.add_argument("--across", type=int, default=4)
    ap.add_argument("--width", type=int, default=640)
    a = ap.parse_args(argv)
    images = pages_of(a.pdf, a.width)
    run = run_folder(a.folder)
    for n, im in enumerate(images, 1):
        path = os.path.join(run, "page-%02d.png" % n)
        im.save(path)
        print(path)
    if a.sheet and images:
        out = os.path.join(run, os.path.basename(a.sheet))
        sheet(images, a.across).save(out, quality=88)
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
