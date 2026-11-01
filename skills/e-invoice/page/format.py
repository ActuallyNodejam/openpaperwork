#!/usr/bin/env python3
"""Number, date and currency forms for the readable invoice page.

Every figure on the page goes through here, so the locale decides the form and no model has to
remember it. The XML keeps the ISO forms; this is for the page only.

    python3 format.py --locale de-DE --money 2150 --date 2026-10-01
    2.150,00
    01.10.2026
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import letter  # noqa: E402

# The forms come from the same table the locale check reads (skills/_checks/locales.json), which
# takes them from Unicode CLDR: 1.234,56 and 05.10.2026 in Germany, 1 234,56 and 2026-10-05 in
# Sweden, 1,234.56 and 05/10/2026 in Britain.
_TABLE = json.loads((Path(__file__).resolve().parents[2] / "_checks" / "locales.json").read_text())["locales"]
_STRF = {"dd": "%d", "MM": "%m", "yyyy": "%Y", "YYYY": "%Y", "DD": "%d"}


def _entry(locale):
    tag = str(locale or "")
    if tag in _TABLE:
        return _TABLE[tag]
    if tag.lower() in ("us", "en-us", "en_us"):
        return _TABLE["us"]
    return _TABLE["eu"]


def spec(locale):
    e = _entry(locale)
    pattern = e["date"]["pattern"]
    for k, v in _STRF.items():
        pattern = pattern.replace(k, v)
    return {"thousands": e["number"]["group"], "decimal": e["number"]["decimal"], "date": pattern,
            "currency": e["currency"].get("code") or "EUR"}


def money(value, locale="de-DE", decimals=2):
    return letter.money(value, locale, decimals)


def number(value, locale="de-DE"):
    """A quantity or a rate in the locale's form."""
    return letter.number(value, locale)


def date(iso, locale="de-DE"):
    """The CLDR short date of the locale. A pattern with single letters (d.M.yyyy, CLDR Finnish) writes
    the day and month without a leading zero; dd and MM keep it."""
    pattern = _entry(locale)["date"]["pattern"]
    try:
        d = dt.date.fromisoformat(str(iso).strip())
    except ValueError:
        return str(iso)
    if not re.search(r"(?<![dD])[dD](?![dD])|(?<!M)M(?!M)", pattern):
        return letter.date(iso, locale)
    out = re.sub(r"yyyy|YYYY|y", str(d.year), pattern)
    out = re.sub(r"dd|DD", "%02d" % d.day, out)
    out = re.sub(r"(?<![dD%])[dD]", str(d.day), out)
    out = re.sub(r"MM", "%02d" % d.month, out)
    return re.sub(r"(?<!M)M(?!M)", str(d.month), out)


def currency(locale="de-DE"):
    return spec(locale)["currency"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="de-DE")
    ap.add_argument("--money", type=float)
    ap.add_argument("--date")
    a = ap.parse_args()
    if a.money is not None:
        print(money(a.money, a.locale))
    if a.date:
        print(date(a.date, a.locale))
