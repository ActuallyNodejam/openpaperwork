"""Open a person's workbook so a save keeps what openpyxl cannot model.

The app bundles paper-xlsx, which imports as openpyxl. It loads an existing
workbook in preserve mode: a save copies every untouched part byte for byte
(charts, pictures, sparklines, Excel 2010 data bars, pivots), clears formula
results the edit made stale, and rewrites formulas, names, tables and chart
ranges on a row or column shift. An edit it cannot save safely raises
PaperRefusal before anything is written. Stock openpyxl has none of this; there
`open_book` is a plain load_workbook and `kept` runs the edit once.
"""
from __future__ import annotations

from openpyxl import load_workbook

try:
    from openpyxl.errors import PaperRefusal
    PAPER = True
except ImportError:  # stock openpyxl
    PAPER = False

    class PaperRefusal(Exception):
        pass


def open_book(path, keep=True):
    """The workbook at `path`; keep=False asks for the stock, lossy round trip."""
    if PAPER:
        return load_workbook(path, preserve=None if keep else False)
    return load_workbook(path)


def kept(path, edit):
    """Run edit(wb) and return (its result, report).

    First on a preserving load; when paper-xlsx refuses (or trips on a file
    it cannot read that way), again on the stock load, as every edit ran
    before paper-xlsx, and the report says what refused so the hand-back
    can name what may not have survived. paper-xlsx writes nothing on a
    refusal, and an edit that fails on both loads raises the stock error.
    """
    if PAPER:
        try:
            return edit(open_book(path)), {"preserved": True}
        except Exception as exc:  # noqa: BLE001 - the stock run below decides
            refused = f"{type(exc).__name__}: {exc}"
        return edit(open_book(path, keep=False)), {
            "preserved": False, "preserve_refused": refused}
    return edit(open_book(path)), {"preserved": False}
