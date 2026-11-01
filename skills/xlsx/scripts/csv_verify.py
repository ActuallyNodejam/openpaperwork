#!/usr/bin/env python3
"""Read-only CSV shape verification against the requested table."""
import argparse
import csv
import json
import sys


def verify(path, headers, expected_rows=None, encoding="utf-8-sig", delimiter=","):
    errors = []
    count = 0
    with open(path, encoding=encoding, newline="") as source:
        reader = csv.reader(source, delimiter=delimiter, strict=True)
        actual = next(reader, None)
        if actual != headers:
            errors.append({"kind": "header", "expected": headers, "actual": actual})
        for count, row in enumerate(reader, 1):
            if len(row) != len(headers):
                errors.append({"kind": "width", "record": count + 1,
                               "expected": len(headers), "actual": len(row)})
    if expected_rows is not None and count != expected_rows:
        errors.append({"kind": "row_count", "expected": expected_rows, "actual": count})
    return {"ok": not errors, "data_rows": count, "columns": len(headers),
            "errors": errors,
            "scope": "CSV shape only; verify values and source coverage separately."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--headers", required=True, help="JSON array of exact column names")
    parser.add_argument("--rows", type=int, help="Expected data records, excluding header")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--delimiter", default=",")
    args = parser.parse_args()
    try:
        headers = json.loads(args.headers)
        if not isinstance(headers, list) or not headers or not all(isinstance(x, str) for x in headers):
            raise ValueError("--headers must be a nonempty JSON array of strings")
        if args.rows is not None and args.rows < 0:
            raise ValueError("--rows cannot be negative")
        result = verify(args.file, headers, args.rows, args.encoding, args.delimiter)
    except (ValueError, OSError, csv.Error) as error:
        result = {"ok": False, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
