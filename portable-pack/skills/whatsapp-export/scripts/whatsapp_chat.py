#!/usr/bin/env python3
"""Read a WhatsApp "Export chat" file (.txt, or .zip with media) into a dated transcript.

Parsing is ported from whatsapp-chat-parser (github.com/Pustur/whatsapp-chat-parser, MIT, Copyright 2018
Loris Bettazza, at 57484d5a53cacff39083237825f8cf2df7501129): its line regexes for iOS and Android exports
in 12- and 24-hour clocks, multiline merging, system messages, attachment names and the day/month order
detection. The zip handling and the transcript are Nodejam's.

  python3 whatsapp_chat.py "WhatsApp Chat - Site team.zip"            # transcript to stdout
  python3 whatsapp_chat.py chat.zip --json --out chat.json             # one object per message
  python3 whatsapp_chat.py chat.zip --since 2026-09-01 --search offert # narrow it down

A zip's media is copied, never overwriting, into "<zip name> files" beside it, and each message names
the saved file. Nothing is sent anywhere.
"""
import argparse
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

SHARED = (
    r"^(?:‎|‏)*\[?(\d{1,4}[-/.]\s?\d{1,4}[-/.]\s?\d{1,4})[,.]?\s\D*?"
    r"(\d{1,2}[.:]\d{1,2}(?:[.:]\d{1,2})?)(?:\s([ap]\.?\s?m\.?))?\]?(?:\s-|:)?\s"
)
MESSAGE = re.compile(SHARED + r"(.+?):\s([\s\S]*)", re.IGNORECASE)
SYSTEM = re.compile(SHARED + r"([\s\S]+)", re.IGNORECASE)
ATTACHMENT = re.compile(r"^(?:‎|‏)*(?:<.+:(.+)>|([\w-]+\.\w+)\s[(<].+[)>])")
MARKS = re.compile(r"[‎‏‪-‮]")


def merge(lines):
    """Joins continuation lines onto their message; a dated line without an author is a system message."""
    messages = []
    for line in lines:
        if MESSAGE.match(line):
            messages.append({"system": False, "raw": line})
        elif SYSTEM.match(line):
            messages.append({"system": True, "raw": line})
        elif messages:
            messages[-1]["raw"] += "\n" + line
    return messages


def order(date):
    """Puts the longest number (the year) last."""
    a, b, c = re.split(r"[-/.] ?", date)
    longest = max(len(a), len(b), len(c))
    if len(c) == longest:
        return [a, b, c]
    if len(b) == longest:
        return [a, c, b]
    return [b, c, a]


def days_first(dates):
    """True when days come before months, from numbers above 12, then decreasing runs, then change rate."""
    if any(d[0] > 12 for d in dates):
        return True
    if any(d[1] > 12 for d in dates):
        return False
    by_year = {}
    for d in dates:
        by_year.setdefault(d[2], []).append(d)
    results = []
    for group in by_year.values():
        pairs = list(zip(group, group[1:]))
        if any(b[0] < a[0] for a, b in pairs):
            results.append(True)
        elif any(b[1] < a[1] for a, b in pairs):
            results.append(False)
    if True in results:
        return True
    if False in results:
        return False
    first = sum(abs(b[0] - a[0]) for a, b in zip(dates, dates[1:]))
    second = sum(abs(b[1] - a[1]) for a, b in zip(dates, dates[1:]))
    return first >= second


def parse(text):
    raw = merge(re.split(r"\r\n|\r|\n", text))
    parsed = []
    for item in raw:
        if item["system"]:
            date, time, ampm, body = SYSTEM.match(item["raw"]).groups()
            author = None
        else:
            date, time, ampm, author, body = MESSAGE.match(item["raw"]).groups()
        parsed.append((date, time, ampm, author, body))
    unique = list(dict.fromkeys(p[0] for p in parsed))
    first = days_first([[int(n) for n in order(d)] for d in unique]) if unique else True
    messages = []
    for date, time, ampm, author, body in parsed:
        a, b, year = order(date)
        day, month = (a, b) if first else (b, a)
        year = "2000"[: 4 - len(year)] + year
        hours, minutes, *rest = re.split(r"[:.]", time)
        hours = int(hours)
        if ampm:
            pm = re.sub(r"[^apm]", "", ampm, flags=re.IGNORECASE).upper() == "PM"
            hours = (0 if hours == 12 else hours) + (12 if pm else 0)
        when = datetime(int(year), int(month), int(day), hours, int(minutes), int(rest[0]) if rest else 0)
        found = ATTACHMENT.match(body)
        messages.append({
            "time": when.isoformat(timespec="minutes"),
            "author": MARKS.sub("", author).strip() if author else None,
            "text": MARKS.sub("", body).strip(),
            **({"attachment": (found.group(1) or found.group(2)).strip()} if found else {}),
        })
    return messages


def load(path):
    """Returns the chat text and, for a zip, the folder its media was copied into."""
    if path.suffix.lower() != ".zip":
        return path.read_text(encoding="utf-8-sig"), None, {}
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        chats = [n for n in names if n.lower().endswith(".txt")]
        chat = next((n for n in chats if Path(n).name == "_chat.txt"), None) or (chats[0] if chats else None)
        if not chat:
            raise SystemExit("No chat text (.txt) inside this zip.")
        text = archive.read(chat).decode("utf-8-sig")
        media = [n for n in names if n != chat]
        folder = path.with_name(f"{path.stem} files")
        saved = {}
        if media:
            folder.mkdir(exist_ok=True)
            for name in media:
                target = free(folder / Path(name).name)
                target.write_bytes(archive.read(name))
                saved[Path(name).name] = target
        return text, folder if media else None, saved


def free(target):
    """The first name that does not exist yet, so nothing already there is overwritten."""
    if not target.exists():
        return target
    for n in range(2, 10_000):
        candidate = target.with_name(f"{target.stem} ({n}){target.suffix}")
        if not candidate.exists():
            return candidate
    raise SystemExit(f"Too many files named {target.name}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("chat", type=Path, help="exported .txt or .zip")
    parser.add_argument("--json", action="store_true", help="one JSON object per message instead of a transcript")
    parser.add_argument("--out", type=Path, help="write here instead of stdout (never overwrites)")
    parser.add_argument("--since", help="first day to keep, YYYY-MM-DD")
    parser.add_argument("--until", help="last day to keep, YYYY-MM-DD")
    parser.add_argument("--search", help="keep messages containing this text (any case)")
    args = parser.parse_args()

    text, folder, saved = load(args.chat)
    messages = parse(text)
    for message in messages:
        if message.get("attachment") in saved:
            message["file"] = str(saved[message["attachment"]])
    messages = [
        m for m in messages
        if (not args.since or m["time"][:10] >= args.since)
        and (not args.until or m["time"][:10] <= args.until)
        and (not args.search or args.search.lower() in m["text"].lower())
    ]
    if args.json:
        output = json.dumps(messages, ensure_ascii=False, indent=1)
    else:
        people = sorted({m["author"] for m in messages if m["author"]})
        header = [
            f"# {args.chat.stem}",
            f"{len(messages)} messages"
            + (f", {messages[0]['time'][:10]} to {messages[-1]['time'][:10]}" if messages else "")
            + (f", from {', '.join(people)}" if people else ""),
            *([f"Media copied to: {folder}"] if folder else []),
            "",
        ]
        lines = [
            f"[{m['time'].replace('T', ' ')}] {m['author'] or '(WhatsApp)'}: {m['text']}"
            + (f"  [file: {m['file']}]" if m.get("file") else "")
            for m in messages
        ]
        output = "\n".join(header + lines)
    if args.out:
        if args.out.exists():
            raise SystemExit(f"{args.out} already exists; choose another name.")
        args.out.write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {len(messages)} messages to {args.out}")
    else:
        sys.stdout.write(output + "\n")


if __name__ == "__main__":
    main()
