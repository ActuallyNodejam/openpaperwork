#!/usr/bin/env python3
"""The season agenda card from a brand folder: every show of a season on one page, by month.

The layout is fixed (agenda.html, ported from the old app's social pack 0.3
templates/agenda.html) and the rows are the folder's own calendar rows: the
show's name, its city and country, its dates, and its hall and booth where the
calendar holds them. Nothing is invented: a show with no dates is left off and
named, a show with no booth has an empty corner. The page is printed by the
Nodejam app's own Chromium, like the fair poster.

    python3 agenda.py --kit <brand folder> --agenda agenda.json [--canvas 4x5,9x16 | --all-canvases]

agenda.json:
    {"season": "Fall 2026", "year": "2026",
     "fairs": ["Shanghai", "Paris", {"city": "Munich", "booth": "A12"}]}
`fairs` names the shows by city or by name; an entry may be an object that
words a row itself (name, city, country, dates, hall, booth). Without `fairs`
the card holds every calendar row of that year that has dates.

The folder's poster.json may hold the card's own paper, ink and accent:
    "agenda": {"ground": "#EAF4FA", "ink": "#0B1533", "accent": "#9DB2D1", "word": "Agenda"}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from poster import (CANVASES, SIZES, Kit, Stop, canvas_list, escape, font_faces, grow, print_job, read_json,  # noqa: E402
                    row_year, screen_fit, slugify)

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
#: The card holds this many shows at most; more than that is two cards.
MOST = 12
#: The page's own measures, in units of a 1080-wide page: the side margin, the dates column, the
#: hall-and-booth column, the largest size of a show's name and a letter's share of that size.
MARGIN, DAYS, AT, NAME, LETTER = 46, 184, 176, 58, 0.53
#: A month's heading, large as on the brand's own card; a crowded season takes the smaller one.
MONTH, MONTH_SMALL, CROWDED = 132, 84, 0.72
DEFAULTS = {"ground": "#ffffff", "ink": "#14161a", "accent": "#8f8f8f", "word": "Agenda"}

PROBE_JS = """(() => {
  const slide = document.querySelector('.slide');
  const box = slide.getBoundingClientRect();
  const frame = slide.querySelector('.agenda-frame').getBoundingClientRect();
  const clipped = [];
  const fonts = new Set();
  for (const el of slide.querySelectorAll('[data-slot]')) {
    const r = el.getBoundingClientRect();
    const what = el.dataset.slot + (el.dataset.row ? ' of ' + el.dataset.row : '');
    if (r.width <= 0 || r.height <= 0) { clipped.push(what + ': empty box'); continue; }
    if (r.left < frame.left - 1 || r.top < frame.top - 1 || r.right > frame.right + 1 || r.bottom > frame.bottom + 1)
      clipped.push(what + ': outside the page');
    if (el.scrollWidth > el.clientWidth + 1) clipped.push(what + ': wider than its column');
    if ((el.textContent || '').trim()) fonts.add(getComputedStyle(el).fontFamily);
  }
  return JSON.stringify({ size: [Math.round(box.width), Math.round(box.height)], clipped, fonts: [...fonts],
    rows: slide.querySelectorAll('.agenda-row').length });
})()"""


def when(dates: str) -> tuple[int, int, str]:
    """A row's dates as the month it starts in, its first day, and the days the card prints."""
    found = re.match(r"\s*(\d{1,2})\s*([A-Za-z]{3,})?\s*(?:[–—-]\s*(\d{1,2})\s*)?([A-Za-z]{3,})?", dates or "")
    month = (found.group(2) or found.group(4) or "") if found else ""
    if not found or month[:3].lower() not in MONTHS:
        raise Stop(f"the dates {dates!r} do not read as days and a month, for example '13-14 October'")
    first, last = int(found.group(1)), found.group(3)
    days = f"{first:02d} – {int(last):02d}" if last else f"{first:02d}"
    return MONTHS.index(month[:3].lower()), first, days


def rows_from(brief: dict, kit: Kit) -> tuple[list[dict], list[str]]:
    """The card's rows: the ask's shows in the folder's own words, sorted by date; and what was left off."""
    year = str(brief.get("year") or "").strip()
    asked = brief.get("fairs")
    if asked is None:
        # No shows named: every calendar row of the year. A row with no name or no dates there is a
        # colour kept for a city, not a show, and is passed over without a word.
        entries = [({}, record) for key, record in kit.fairs.items() if not year or row_year(key, record) == year]
    else:
        entries = []
        for entry in asked:
            own = dict(entry) if isinstance(entry, dict) else {"city": str(entry)}
            entries.append((own, kit.fair_for({"city": own.get("city"), "fair": own.get("name") or own.get("fair"),
                                               "year": year})))
    rows, left = [], []
    for own, record in entries:
        name = str(own.get("name") or own.get("fair") or record.get("name") or "").strip()
        city = str(own.get("city") or record.get("city") or "").strip()
        dates = str(own.get("dates") or record.get("dates") or "").strip()
        if not name or not dates:
            if asked is not None:
                left.append(f"{city or name}: the calendar holds no {'dates' if name else 'show name'} for it")
            continue
        month, first, days = when(dates)
        rows.append({
            "name": name, "city": city, "country": str(own.get("country") or record.get("country") or "").strip(),
            "dates": dates, "days": days, "month": month, "first": first,
            "hall": str(own.get("hall") or record.get("hall") or record.get("zone") or "").strip(),
            "booth": str(own.get("booth") or record.get("booth") or "").strip(),
        })
    if not rows:
        raise Stop("the agenda has no show with a name and dates; name the shows, or give the calendar's year")
    if len(rows) > MOST:
        raise Stop(f"the agenda holds {MOST} shows at most and the ask names {len(rows)}; make two cards")
    for row in rows:
        for key, limit in (("name", 34), ("hall", 14), ("booth", 8)):
            if len(row[key]) > limit:
                raise Stop(f"{row['city'] or row['name']}: the {key} is {len(row[key])} characters; the row holds {limit}: {row[key]!r}")
    rows.sort(key=lambda row: (row["month"], row["first"]))
    return rows, left


def measures(rows: list[dict], canvas: str, shrink: float) -> dict:
    """The size of a unit and of a show's name on this canvas, so every row fits its page."""
    width, height, safe_top, _right, safe_bottom, _left = CANVASES[canvas]
    # A show's name has the row to itself when the show has no hall or booth, and shares it when it has.
    name = NAME
    for row in rows:
        room = 1080 - 2 * MARGIN - DAYS - (AT if row["hall"] or row["booth"] else 0)
        name = min(name, int(room / (LETTER * len(row["name"]))))
    months = len({row["month"] for row in rows})
    base = width / 1080
    room = height - safe_top - safe_bottom - 2 * MARGIN * base
    for month in (MONTH, MONTH_SMALL):
        needed = 60 + 88 + 104 + months * month * 1.37 + len(rows) * (24 * 1.2 + 4 + name * 1.1 + 30)
        fit = min(1.0, room / (needed * base))
        if fit >= CROWDED:
            break
    return {"unit": base * fit * shrink, "name": name, "month": month, "top": safe_top + MARGIN * base,
            "bottom": safe_bottom + MARGIN * base,
            # A story has room above and below its safe area: the card sits in the middle of it.
            "justify": "center" if safe_top or safe_bottom else "flex-start"}


def render_html(kit: Kit, brief: dict, rows: list[dict], tokens: dict, canvas: str, scale: float, shrink: float) -> str:
    from PIL import Image

    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    fit = measures(rows, canvas, shrink)
    wordmark = kit.mark(tokens["wordmark"]) if tokens.get("wordmark") else None
    mark_html, ratio = "", 1.0
    if wordmark:
        with Image.open(wordmark) as image:
            ratio = image.width / image.height
        mark_html = '<div class="agenda-wordmark" data-slot="wordmark"></div>'
    groups, seen = [], None
    for index, row in enumerate(rows, 1):
        if row["month"] != seen:
            seen = row["month"]
            groups.append(f'    <h2 class="agenda-month" data-slot="month">{MONTHS[seen].capitalize()}</h2>')
        place = ", ".join(part for part in (row["city"], row["country"]) if part)
        at = ""
        if row["hall"] or row["booth"]:
            at = ((f'<p class="agenda-mono" data-slot="hall" data-row="{index}">{escape(row["hall"])}</p>' if row["hall"] else
                   '<p class="agenda-mono">&nbsp;</p>')
                  + (f'<p class="agenda-big" data-slot="booth" data-row="{index}">{escape(row["booth"])}</p>' if row["booth"] else ""))
        groups.append(
            f'    <div class="agenda-row{"" if at else " agenda-wide"}">'
            f'<p class="agenda-mono" data-slot="days" data-row="{index}">{escape(row["days"])}</p>'
            f'<div><p class="agenda-mono" data-slot="place" data-row="{index}">{escape(place)}</p>'
            f'<p class="agenda-big" data-slot="name" data-row="{index}">{escape(row["name"])}</p></div>'
            + (f'<div>{at}</div>' if at else "") + '</div>')
    replacements = {
        "__CANVAS__": canvas,
        "__TITLE__": escape(f"{tokens['word']} {brief.get('season') or ''}".strip()),
        "__FONT_FACES__": font_faces(kit.root),
        "__W__": str(width), "__H__": str(height),
        "__U__": f"{fit['unit']:.4f}", "__NAME__": str(fit["name"]), "__AT__": str(AT),
        "__MONTH__": str(fit["month"]), "__JUSTIFY__": fit["justify"],
        "__TOP__": f"{fit['top']:.1f}", "__BOTTOM__": f"{fit['bottom']:.1f}",
        "__GROUND__": tokens["ground"], "__INK__": tokens["ink"], "__ACCENT__": tokens["accent"],
        "__SCALE__": f"{scale:.4f}",
        "__PAGE_W__": f"{width / 96 * 25.4:.3f}", "__PAGE_H__": f"{height / 96 * 25.4:.3f}",
        "__MARK_RATIO__": f"{ratio:.4f}",
        "__WORDMARK__": wordmark.as_uri() if wordmark else "",
        "__MARK__": mark_html,
        "__WORD__": escape(tokens["word"]),
        "__SEASON__": escape(str(brief.get("season") or "").strip()),
        "__GROUPS__": "\n".join(groups),
    }
    html = (HERE / "agenda.html").read_text()
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def build_one(kit: Kit, brief: dict, rows: list[dict], tokens: dict, canvas: str, out: Path, slug: str) -> dict:
    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    scale = screen_fit(canvas)
    pdf, png = out / f"{slug}-{canvas}.pdf", out / f"{slug}-{canvas}.png"
    shrink, layout = 1.0, {}
    with tempfile.TemporaryDirectory(prefix="agenda-") as tmp:
        tmp_path = Path(tmp)
        script = tmp_path / "probe.js"
        script.write_text(PROBE_JS)
        # The type is sized by arithmetic; the page itself has the last word. A row the app measures
        # wider or lower than its page shrinks the whole card a step, four times at most.
        for _attempt in range(5):
            page = tmp_path / "agenda.html"
            page.write_text(render_html(kit, brief, rows, tokens, canvas, scale, shrink))
            shots = tmp_path / "shot"
            answer = print_job(page, pdf=pdf, shots=shots, script=script, width=width, height=height)
            layout = json.loads(answer) if answer.strip() else {}
            if isinstance(layout, str):
                layout = json.loads(layout)
            if not layout.get("clipped"):
                break
            shrink *= 0.93
        shot = shots / "p-01.png"
        if not shot.is_file():
            raise Stop("the app printed no page; the agenda cannot be exported")
        grow(shot, png, (width, height))
    layout["fit_scale"] = scale
    fit = measures(rows, canvas, shrink)
    return {"canvas": canvas, "files": {"png": png.name, "pdf": pdf.name}, "layout": layout,
            "unit": round(fit["unit"], 4), "nameSize": fit["name"], "monthSize": fit["month"], "shrink": round(shrink, 4)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Make a season's agenda card from the brand folder.")
    parser.add_argument("--kit", required=True, help="the brand folder the person pointed the app at")
    parser.add_argument("--agenda", required=True, help="the agenda's brief JSON")
    parser.add_argument("--out", help="where the card goes (default: <kit>/posters/agenda-<season>)")
    parser.add_argument("--canvas", default=["4x5"], type=canvas_list,
                        help="one size, or several in one run with commas between (4x5,9x16)")
    parser.add_argument("--all-canvases", action="store_true", help="4x5, 9x16, 1x1 and a4")
    args = parser.parse_args(argv)

    kit = Kit(Path(args.kit))
    brief = read_json(Path(args.agenda))
    season = str(brief.get("season") or "").strip()
    if not season:
        raise Stop("the agenda needs its season, for example \"season\": \"Fall 2026\"")
    if len(season) > 18:
        raise Stop(f"the season is {len(season)} characters; the title holds 18: {season!r}")
    ask = json.loads(json.dumps(brief))
    rows, left = rows_from(brief, kit)
    tokens = {**DEFAULTS, "wordmark": kit.facts.get("wordmark"), **(kit.facts.get("agenda") or {}),
              **{key: brief[key] for key in ("ground", "ink", "accent", "word") if brief.get(key)}}
    for key in ("ground", "ink", "accent"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(tokens[key])):
            raise Stop(f"the agenda's {key} must be #RRGGBB, not {tokens[key]!r}")
    slug = slugify(f"agenda-{season}")
    out = Path(args.out).resolve() if args.out else (kit.root / "posters" / slug)
    out.mkdir(parents=True, exist_ok=True)

    canvases = SIZES if args.all_canvases else args.canvas
    built = [build_one(kit, brief, rows, tokens, canvas, out, slug) for canvas in canvases]
    manifest = out / f"{slug}.json"
    earlier = []
    if manifest.is_file():
        try:
            before = json.loads(manifest.read_text())
        except ValueError:
            before = {}
        if isinstance(before, dict) and before.get("ask") == ask:
            made = {item["canvas"] for item in built}
            earlier = [item for item in before.get("canvases") or []
                       if isinstance(item, dict) and item.get("canvas") in CANVASES and item["canvas"] not in made
                       and (out / str((item.get("files") or {}).get("png") or "-")).is_file()]
    result = {
        "kind": "agenda", "season": season, "year": str(brief.get("year") or ""),
        # The ask this card was made from, so a later change starts from it.
        "ask": ask,
        "rows": [{key: row[key] for key in ("name", "city", "country", "dates", "days", "hall", "booth")} for row in rows],
        "leftOff": left,
        "wordmark": tokens.get("wordmark"),
        "colours": {key: tokens[key] for key in ("ground", "ink", "accent")},
        "canvases": sorted(earlier + built, key=lambda item: SIZES.index(item["canvas"])),
    }
    manifest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"out": str(out), "rows": len(rows), "leftOff": left, "built": [{
        "canvas": item["canvas"], "png": item["files"]["png"], "pdf": item["files"]["pdf"],
        "clipped": item["layout"].get("clipped"), "fonts": item["layout"].get("fonts"),
    } for item in built]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as stop:
        print(f"STOP {stop}", file=sys.stderr)
        sys.exit(2)
