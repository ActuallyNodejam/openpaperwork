#!/usr/bin/env python3
"""Make one fair poster by code, from the brand folder and a fair brief.

The layout is fixed (poster.html, ported from the old app's social pack 0.3
`event` page). This script fills its slots and moves the picture:

  anchor clip -> three-stop tint in the fair's colour -> the fair's loop
  loop + fixed layout -> PNG, PDF, MP4 and GIF beside the originals

No model draws anything. The loop is its family's approved anchor recoloured by
arithmetic, the same tint the old app's `motion recolour` ran.

    python3 poster.py --kit "<the brand folder>" --fair "<fair.json>" [--out DIR]

`--fair` is a small JSON file; the keys are in SKILL.md and in the kit's
README.md. A missing optional slot is left off the page, never faked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import colourway as C  # noqa: E402

CANVASES = {
    "4x5": (1080, 1350, 0, 0, 0, 0),
    "9x16": (1080, 1920, 250, 0, 340, 0),
    "1x1": (1080, 1080, 0, 0, 0, 0),
    "a4": (794, 1123, 0, 0, 0, 0),
}
FPS = 25
GIF_WIDTH = 800
#: How long any one child may run. An encode of a six-second loop on this box
#: takes seconds; ten minutes means something is wrong and the run stops.
ENCODE_SECONDS = 600
#: How long the whole film pass may take: one capture per frame, each a print.
FILM_SECONDS = 1800
#: How long one print may take. The app answers in seconds; a dead app must not
#: leave the skill waiting on a socket that will never reply.
PRINT_SECONDS = 180
#: The GIF is the sharing size: half the loop's rate, the same length.
GIF_FPS = 25 / 3
#: A GIF over this is no longer a file people post. The first colour count that fits is used.
GIF_BYTES = 15_000_000
GIF_COLOURS = (64, 48, 32)
#: A photo look's plate width: the plate keeps the photo's own shape, so each canvas takes the
#: widest window the photo has, and it is wide enough that a 9:16 window of a 4:5 photo is not enlarged.
PHOTO_WIDTH = 1440

FONTS = [
    ("Inter", 400, "normal", "inter-400-latin.woff2", "inter-400-latin-ext.woff2"),
    ("Inter", 700, "normal", "inter-700-latin.woff2", "inter-700-latin-ext.woff2"),
    ("Instrument Serif", 400, "normal", "instrument-serif-400-latin.woff2", "instrument-serif-400-latin-ext.woff2"),
    ("Instrument Serif", 400, "italic", "instrument-serif-400-italic-latin.woff2", "instrument-serif-400-italic-latin-ext.woff2"),
    ("Noto Sans SC", 400, "normal", "noto-sans-sc-400-sc.woff2", None),
    ("Noto Sans SC", 700, "normal", "noto-sans-sc-700-sc.woff2", None),
    ("Signal Mono", 400, "normal", "ibm-plex-mono-400-latin.woff2", "ibm-plex-mono-400-latin-ext.woff2"),
]

def row_year(key: str, record: dict) -> str:
    """A calendar row's year: its own field, else the year in its key (munich-2026)."""
    found = re.search(r"(?:19|20)\d{2}", key)
    return str(record.get("year") or (found.group(0) if found else ""))


class Stop(Exception):
    """Something the person has to fix; the sentence says what."""


# ------------------------------------------------------------------ the kit


def read_json(path: Path):
    if not path.is_file():
        raise Stop(f"{path} is missing")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise Stop(f"{path} is not valid JSON: {error}") from error


class Kit:
    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise Stop(f"the brand folder {self.root} is not there")
        self.marks = {}
        for entry in read_json(self.root / "marks" / "manifest.json").get("assets", []):
            self.marks[entry["file"]] = entry
            if entry.get("name"):
                self.marks[entry["name"].lower()] = entry
        self.facts = read_json(self.root / "poster.json") if (self.root / "poster.json").is_file() else {}
        if not self.facts:
            raise Stop(f"{self.root} has no poster.json; the folder must say which wordmark and claim it uses")
        fairs_file = self.facts.get("fairs") or "fairs.json"
        loaded = read_json(self.root / fairs_file) if (self.root / fairs_file).is_file() else {}
        # The calendar file carries a note beside its rows; only the rows are fairs.
        self.fairs = {key: row for key, row in (loaded.get("fairs") or loaded).items() if isinstance(row, dict)}
        self.looks = {look["name"]: look for look in read_json(self.root / (self.facts.get("looks") or "looks.json"))["looks"]}
        self.anchors = self.root / "anchors"

    def mark(self, name: str) -> Path:
        """A mark by file name or by manifest name, case-insensitive."""
        key = str(name).strip()
        entry = self.marks.get(key) or self.marks.get(key.lower())
        if entry is None:
            for candidate_key, candidate in self.marks.items():
                if candidate_key.lower() == key.lower():
                    entry = candidate
                    break
        if entry is not None:
            path = self.root / "marks" / entry["file"]
            if not path.is_file():
                raise Stop(f"the mark file {path} is missing")
            return path
        allowed = {".png", ".svg", ".jpg", ".jpeg", ".webp"}
        for candidate in sorted((self.root / "marks").glob("*")):
            if candidate.is_file() and candidate.suffix.lower() in allowed and candidate.name.lower() == key.lower():
                return candidate
        near = sorted({path.name for path in (self.root / "marks").glob("*.png") if key.split("-")[0].lower() in path.name})
        hint = f" Closest in the kit: {', '.join(near[:6])}." if near else ""
        raise Stop(f"the kit's marks folder has no {name!r}.{hint}")

    def anchor(self, look: dict, spare: bool = False) -> Path:
        name = look["spare"] if spare else look["anchor"]
        path = self.anchors / name
        if not path.is_file():
            raise Stop(f"the anchor clip {path} is missing from the kit")
        return path

    def fair_for(self, brief: dict) -> dict:
        """The fair's own row in the folder's calendar, when the brand has one.

        Matched on the fair's name or the city, and on the year when the ask
        gives one, so "the Portland poster" finds the Portland row with its
        venue, its zone and its booth without the person repeating them.
        """
        slug = slugify(brief.get("city") or brief.get("fair") or "")
        season = str(brief.get("year") or "")
        if not slug:
            return {}
        rows = [(row_year(key, record), record) for key, record in self.fairs.items() if slug in slugify(key)]
        # A city the brand shows in every year has a row per year (munich-2025, munich-2026):
        # the ask's year picks its own row, an undated row serves any year, and with no year
        # asked the newest row is the fair's current one.
        if season:
            rows = [row for row in rows if row[0] == season] or [row for row in rows if not row[0]]
        else:
            rows.sort(key=lambda row: row[0], reverse=True)
        if rows:
            return rows[0][1]
        for key, record in self.fairs.items():
            if slug and slug in slugify(record.get("name") or ""):
                return record
        return {}

    def look_for(self, brief: dict) -> dict:
        """The ask's look, else the fair's own look from the calendar, else by colour."""
        wanted = brief.get("look")
        record = self.fair_for(brief)
        if record and not wanted and record.get("look") in self.looks:
            return self.looks[record["look"]]
        if record and wanted and record.get("look") == wanted and wanted in self.looks:
            return self.looks[wanted]
        if wanted:
            for name, look in self.looks.items():
                if name == wanted or look.get("family") == wanted:
                    return look
            raise Stop(f"the folder has no look called {wanted!r}; it has {', '.join(sorted(self.looks))}")
        # No look named and no calendar row: the folder's own first look, never a
        # guessed one. The model may name another in the ask.
        return next(iter(self.looks.values()))


def dark_type(look: dict) -> bool:
    """A look with dark words sits on a light plate: the danger behind a line is a dark patch, not a bright one."""
    ink = str(look.get("ink") or "")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", ink):
        return False
    red, green, blue = C.parse_hex_color(ink)
    return 0.299 * red + 0.587 * green + 0.114 * blue < 0.5


# Letters a mark cannot be taken off: the rest lose theirs (å, ä and ö become a, a and o).
FOLD = str.maketrans({"ß": "ss", "æ": "ae", "ø": "o", "œ": "oe", "ł": "l", "đ": "d", "ð": "d", "þ": "th"})


def slugify(value: str) -> str:
    """A name for a file: "Resemässan Göteborg" is resemassan-goteborg, never resem-ssan-g-teborg (a real run,
    2026-10-25)."""
    plain = unicodedata.normalize("NFKD", (value or "").lower().translate(FOLD))
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


def font_faces(root: Path) -> str:
    fonts = root / "fonts"
    # A kit with no faces of its own (one started from a logo and a photo) takes the skill's open ones.
    if not fonts.is_dir():
        fonts = HERE / "fonts"
    rules = []
    for family, weight, style, latin, latin_ext in FONTS:
        for file in (latin, latin_ext):
            if not file or not (fonts / file).is_file():
                continue
            rules.append(
                '@font-face { font-family: "%s"; font-style: %s; font-weight: %d; src: url("%s") format("woff2"); }'
                % (family, style, weight, (fonts / file).as_uri())
            )
    if not rules:
        raise Stop(f"the kit has no fonts in {fonts}")
    return "\n".join(rules)


# ------------------------------------------------------------------ the slots


def slots_from(brief: dict, kit: Kit) -> dict:
    """The page's words: the ask first, the folder's calendar second, nothing invented."""
    record = kit.fair_for(brief)
    fair = str(brief.get("fair") or record.get("name") or "").strip()
    city = str(brief.get("city") or record.get("city") or "").strip()
    if not fair or not city:
        raise Stop("the ask needs a fair name and a city, and the folder's calendar has no row for it")
    country = str(brief.get("country") or record.get("country") or "").strip()
    # A thank-you is its own post after the fair: the same page, thanking the city.
    thanks = bool(brief.get("thanks"))
    headline = str(brief.get("headline") or (f"Thank you, {city}" if thanks else f"See you soon in {city}")).strip()
    # An announcement says the way to the hall; a thank-you only names the place.
    venue = str(brief.get("venue") or ("" if thanks else record.get("venue")) or f"{city}, {country}".strip(", ")).strip()
    if len(headline) > 40:
        raise Stop(f"the headline is {len(headline)} characters; the slot holds 40: {headline!r}")
    if len(venue) > 64:
        raise Stop(f"the venue is {len(venue)} characters; the slot holds 64: {venue!r}")
    band = str(brief.get("dates") or record.get("dates") or "").strip()
    if not band:
        raise Stop("the ask needs the dates, for example '13-14 October', and the calendar has none for this fair")
    if len(band) > 20:
        raise Stop(f"the dates are {len(band)} characters; the slot holds 20: {band!r}")
    # The visit corner: the hall and the booth, the zone and the booth, or whatever
    # the ask words itself. A fair with none of them leaves the corner off the page.
    # After the fair nobody is asked to visit, so a thank-you leaves the corner off unless the ask words it.
    tag = str(brief.get("booth") or ("" if thanks else " ".join(
        part for part in (record.get("hall") or record.get("zone"), record.get("booth")) if part
    ))).strip()
    slots = {
        "headline": headline,
        "venue": venue,
        "year": str(brief.get("year") or record.get("year") or "").strip(),
        "band": band,
        "cue": str(brief.get("cue") or ("VISIT US AT" if tag else "")).strip(),
        "tag": tag,
        "claim": str(brief.get("claim") or kit.facts.get("claim") or "").strip(),
        # The line under the booth, where the fair names its part of the hall.
        "area": str(brief.get("area") or record.get("area") or "").strip(),
    }
    for key, limit in (("year", 12), ("cue", 16), ("tag", 20), ("claim", 64), ("area", 24)):
        if len(slots[key]) > limit:
            raise Stop(f"the {key} is {len(slots[key])} characters; the slot holds {limit}: {slots[key]!r}")
    wordmark = brief.get("wordmark") or kit.facts.get("wordmark")
    slots["wordmark"] = kit.mark(wordmark) if wordmark else None
    partner = brief.get("mark") or record.get("mark")
    slots["partner"] = kit.mark(partner) if partner else None
    slots["marks"] = [kit.mark(name) for name in brief.get("marks") or record.get("marks") or []]
    if not slots["partner"] and not brief.get("no-partner") and kit.facts.get("partner") is not False:
        raise Stop(f"the ask names no mark for {fair}; give \"mark\": \"<the fair's file in marks/>\"")
    # A photo look draws the fair's own picture: the ask's, else the calendar row's.
    slots["photo"] = str(brief.get("photo") or record.get("photo") or kit.facts.get("photo") or "").strip()
    slots["photoTop"] = str(brief.get("photoTop") or record.get("photoTop") or "").strip()
    slots["calendarColour"] = str(record.get("colour") or "").strip()
    slots["calendarMark"] = str(record.get("mark") or "").strip()
    slots["calendarName"] = str(record.get("name") or "").strip()
    slots["colour"] = str(brief.get("colour") or record.get("colour") or kit.facts.get("colour") or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", slots["colour"]):
        raise Stop(f"the fair's colour must be #RRGGBB, and the ask gives {slots['colour']!r}")
    return slots


def label(slot: str, text: str) -> str:
    """A small mono label, left off the page when it has nothing to say."""
    if not text.strip():
        return ""
    return f'<p class="social-fair-label" data-slot="{slot}">{escape(text)}</p>'


def at_cell(slots: dict) -> str:
    """The visit corner: the cue over the booth, and nothing at all without them.

    The brand's own posters leave that corner out when a fair has not given a
    hall, so an ask without one reads as the brand's page, not as a page with a
    gap in it.
    """
    cue, tag, area = slots["cue"].strip(), slots["tag"].strip(), slots.get("area", "").strip()
    if not cue and not tag:
        return ""
    return (
        '<div class="social-fair-cell social-fair-at">'
        + (f'<p class="social-fair-label" data-slot="cue">{escape(cue)}</p>' if cue else "")
        + (f'<p class="social-fair-big" data-slot="tag">{escape(tag)}</p>' if tag else "")
        + (f'<p class="social-fair-label social-fair-area" data-slot="area">{escape(area)}</p>' if tag and area else "")
        + "</div>"
    )


def claim_block(claim: str) -> str:
    if not claim.strip():
        return ""
    return f'<p class="social-fair-claim" data-slot="claim">{escape(claim)}</p>'


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html(kit: Kit, look: dict, slots: dict, canvas: str, background: Path | None,
                scale: float = 1.0, mask: str | None = None, motion: bool = False,
                faces_in: str = "") -> str:
    width, height, safe_top, safe_right, safe_bottom, safe_left = CANVASES[canvas]
    html = (HERE / "poster.html").read_text()
    # The film pass renders the same page without re-reading the kit, so the
    # fonts it already chose are handed in.
    faces = faces_in or font_faces(kit.root)
    if background and motion:
        background_html = (
            f'<video class="social-bg" data-slot="background" muted playsinline preload="auto" loop '
            f'src="{background.as_uri()}"></video>'
        )
    else:
        background_html = (
            f'<img class="social-bg" data-slot="background" alt="" src="{background.as_uri()}">' if background else ""
        )
    marks_html = ""
    if slots["marks"]:
        items = "".join(f'<li class="social-mark"><img alt="" src="{path.as_uri()}"></li>' for path in slots["marks"])
        marks_html = f'<ul class="social-marks social-fair-marks" data-slot="marks">{items}</ul>'
    partner_html = f'<img class="social-fair-partner" data-slot="partner" alt="" src="{slots["partner"].as_uri()}">' if slots["partner"] else ""
    replacements = {
        "__CANVAS__": canvas,
        "__TITLE__": escape(f"{slots['headline']} — {slots['band']}"),
        "__FONT_FACES__": faces,
        "__W__": str(width),
        "__H__": str(height),
        "__CANVAS_TOKENS__": (
            f"--nj-canvas-w: {width}px; --nj-canvas-h: {height}px; --nj-safe-top: {safe_top}px; "
            f"--nj-safe-right: {safe_right}px; --nj-safe-bottom: {safe_bottom}px; --nj-safe-left: {safe_left}px; "
            f"--social-m: {round(width * 0.0583)}px; --social-sp-2: {round(width * 0.0222)}px; "
            f"--social-sp-3: {round(width * 0.037)}px; --social-wordmark-h: {round(width * 0.0444)}px; "
            f"--social-mark-h: {round(width * 0.0667)}px; --social-mark-gap: {round(width * 0.0407)}px; "
            f"--social-t-fair-head: {round(width * 0.0611)}px; --social-t-fair-small: {round(width * 0.0278)}px; "
            f"--social-t-fair-big: {round(width * 0.0648)}px; --social-t-fair-claim: {round(width * 0.0444)}px; "
            f"--social-fair-wordmark-h: {round(width * float(look['wordmark'])) if look.get('wordmark') else look.get('wordmarkH', round(width * 0.0741))}px; "
            f"--social-fair-partner-h: {round(width * float(look['partner'])) if look.get('partner') else look.get('partnerH', round(width * 0.088))}px; "
            f"--social-fair-mark-h: {look.get('markH', round(width * 0.0444))}px;"
            # A look may move the head down and the dates up, and set its own small type,
            # each as a share of the canvas so every canvas keeps the same proportions.
            f"--look-pad-top: {round(height * float(look.get('padTop', 0)))}px; "
            f"--look-pad-bottom: {round(height * float(look.get('padBottom', 0)))}px; "
            f"--look-venue-w: {look.get('venueWidth', '72%')};"
            + (f" --social-t-fair-small: {round(width * float(look['small']))}px;" if look.get("small") else "")
            + (f" --social-t-fair-head: {round(width * float(look['head']))}px;" if look.get("head") else "")
            + (f" --look-at-align: {look['atAlign']};" if look.get("atAlign") else "")
        ),
        "__GROUND__": look["ground"] if background else look["groundDark"],
        "__GROUND_DARK__": look["groundDark"],
        "__INK__": look["ink"],
        "__SOFT__": look["soft"],
        "__LINE__": look["line"],
        "__SCRIM_HEAD__": look["scrimHeadDark"] if background else look["scrimHeadLight"],
        "__SCRIM_FOOT__": look["scrimFootDark"] if background else look["scrimFootLight"],
        "__CLEAR__": look["clear"],
        "__ON__": look["on"],
        "__MARK__": look.get("markFilter") or look.get("mark") or "none",
        "__BACKGROUND_STATE__": "image" if background else "none",
        "__SCALE__": f"{scale:.4f}",
        "__MASK__": f' data-mask="{mask}"' if mask else "",
        "__PAGE_W__": f"{width / 96 * 25.4:.3f}",
        "__PAGE_H__": f"{height / 96 * 25.4:.3f}",
        "__BACKGROUND__": background_html,
        "__HEADLINE__": escape(slots["headline"]),
        "__VENUE__": escape(slots["venue"]),
        "__BAND__": escape(slots["band"]),
        "__YEAR_LABEL__": label("year", slots["year"]),
        "__AT_CELL__": at_cell(slots),
        "__CLAIM_BLOCK__": claim_block(slots["claim"]),
        "__WORDMARK__": (
            f'<img class="social-fair-wordmark" data-slot="wordmark" alt="" src="{slots["wordmark"].as_uri()}">'
            if slots.get("wordmark") else ""
        ),
        "__PARTNER__": partner_html,
        "__MARKS__": marks_html,
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


# ------------------------------------------------------------------ rendering


def run(command: list[str], timeout: int = ENCODE_SECONDS, **kwargs) -> subprocess.CompletedProcess:
    """Run one child with a hard time limit.

    A filter graph that loops a still image never ends on its own, and an
    unbounded encode can hold a whole machine for hours. Every ffmpeg call here
    carries a limit, and the calls that draw a still over a clip also state the
    length they want, so neither the graph nor the wall clock can run away.
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        raise Stop(
            f"{Path(command[0]).name} ran longer than {timeout} s and was stopped; "
            "the picture or the clip it was given is not the one it expected"
        ) from None
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-4:]
        raise Stop(f"{Path(command[0]).name} failed: {' | '.join(tail)}")
    return result


def print_job(html: Path, *, pdf: Path | None = None, shots: Path | None = None, width: int = 1080,
              height: int = 1350, script: Path | None = None, url_suffix: str = "", frames: int = 0,
              timeout: int = PRINT_SECONDS) -> str:
    """Print the page with the app's own Chromium, or with Playwright's when no app is around the agent;
    `frames` films it in one load. Both answer alike."""
    if os.environ.get("NODEJAM_PRINT"):
        command = ["nodejam-print", str(html) + url_suffix]
    else:
        command = [sys.executable, str(HERE / "print_page.py"), str(html) + url_suffix]
    if pdf:
        command.append(str(pdf))
    if shots:
        command += ["--shots", str(shots)]
    if script:
        command += ["--eval", str(script)]
    command += ["--width", str(width), "--height", str(height)]
    if frames:
        command += ["--frames", str(frames)]
    return run(command, timeout=timeout).stdout


def find_ffmpeg() -> str:
    override = os.environ.get("NODEJAM_FFMPEG")
    found = override or shutil.which("ffmpeg")
    if not found:
        raise Stop(
            "ffmpeg is needed to recolour the anchor and write the MP4. "
            "Install it (brew install ffmpeg) or set NODEJAM_FFMPEG to the binary."
        )
    return found


def probe(path: Path) -> dict:
    ffmpeg = find_ffmpeg()
    result = run([
        ffmpeg.replace("ffmpeg", "ffprobe") if ffmpeg.endswith("ffmpeg") else "ffprobe",
        "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames,r_frame_rate,duration",
        "-of", "json", str(path),
    ])
    stream = json.loads(result.stdout)["streams"][0]
    rate = stream.get("r_frame_rate", "25/1")
    numerator, _, denominator = rate.partition("/")
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frames": int(stream.get("nb_frames") or 0),
        "fps": float(numerator) / float(denominator or 1),
        "seconds": float(stream.get("duration") or 0),
    }


def closing_window(anchor: Path, ffmpeg: str, colour: str, canvas: str, finish: str = "",
                   crop_position: float = 0.5, even: bool = True, keep: float = 0.7,
                   own: float = 0.0, saturation: float = 1.0, wash: bool = False) -> dict:
    """The window of the plate that loops: it ends one frame before the cycle repeats.

    The clip is read through the very chain the poster uses — its window, its
    tint, its look's finish — at a size where a moving highlight can be seen. The
    loop must END BEFORE the plate returns to its first state: an end frame that
    matches the first frame means the viewer sees the same picture twice at the
    wrap, a one-frame stutter. So every pair (start, end) that keeps most of the
    clip is scored by how well the frame AFTER its end matches its start, the
    longest window first, and the loop runs from start to end inclusive. The
    span is kept even when asked, because the GIF reads every second frame and
    must land on the loop's own last frame.
    """
    import numpy as np
    from PIL import Image

    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    info = probe(anchor)
    crop_width, crop_height, crop_x, crop_y = window_of(info, width, height, crop_position)
    small = (270, max(2, int(round(270 * height / width))))
    with tempfile.TemporaryDirectory(prefix="close-") as tmp:
        run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(anchor), "-vf",
             f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},"
             + C.filter_for(colour, still=True, finish=finish, keep=own, saturation=saturation, wash=wash)
             + f",scale={small[0]}:{small[1]}",
             str(Path(tmp) / "f-%05d.png")])
        files = sorted(Path(tmp).glob("f-*.png"))
        if len(files) < 8:
            raise Stop(f"the anchor {anchor.name} gave no frames to read")
        frames = [np.asarray(Image.open(path).convert("RGB")).astype(np.float32) for path in files]

    count = len(frames)
    steps = np.array([float(np.abs(frames[i] - frames[i + 1]).mean()) for i in range(count - 1)])
    median = float(np.median(steps)) if len(steps) else 0.0
    shortest = max(8, int(count * keep))
    best = None
    for begin in range(0, count - shortest):
        for last in range(begin + shortest - 1, count - 1):
            span = last - begin
            if even and span % 2:
                continue
            # how naturally the loop continues: the frame after the end, against the start
            wrap = float(np.abs(frames[last + 1] - frames[begin]).mean())
            key = (round(wrap, 4), -span, begin)
            if best is None or key < best[0]:
                best = (key, begin, last, wrap)
    if best is None:
        raise Stop(f"the anchor {anchor.name} has no window long enough to loop")
    _key, begin, last, wrap = best
    return {"start": begin, "frame": last, "frames": last - begin + 1,
            "seam": round(float(np.abs(frames[last] - frames[begin]).mean()), 3),
            "wrapStep": round(wrap, 3), "medianStep": round(median, 3),
            "limit": round(max(0.35, 1.5 * median), 3),
            "closes": bool(wrap <= max(0.35, 1.5 * median)), "scanned": count}


#: H.264 in yuv420p needs even sides; A4 (794x1123) films get one repeated row at the
#: foot. The PNG and PDF keep the canvas exactly.
EVEN = "pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0"


def photo_plate(photo: Path, out: Path, top: float = 1.0) -> Path:
    """The fair's own photo as the look's plate: one still picture at the photo's own shape.

    A photo look is a still poster, the way the brand posts its city photos. Nothing
    moves a still photo (a push-in, a pan or words sliding over it reads as a cheap
    trick), so a photo look has no loop, no MP4 and no GIF; a moving poster comes from
    a look whose loop really moves. `top` keeps only that share of the photo from its
    top edge, so a shop sign at the foot never reaches the page.
    """
    if out.is_file() and out.stat().st_mtime >= photo.stat().st_mtime:
        return out
    ffmpeg = find_ffmpeg()
    from PIL import Image

    with Image.open(photo) as image:
        photo_w, photo_h = image.size
    plate_w = PHOTO_WIDTH
    plate_h = int(round(plate_w * photo_h * min(top, 1.0) / photo_w / 2)) * 2
    run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(photo), "-vf",
         (f"crop=iw:trunc(ih*{top:.3f}/2)*2:0:0," if top < 1 else "")
         + f"scale={plate_w}:{plate_h}:force_original_aspect_ratio=increase:flags=lanczos,crop={plate_w}:{plate_h}",
         "-frames:v", "1", "-update", "1", str(out)])
    return out


def tint_clip(anchor: Path, out: Path, colour: str, canvas: str, finish: str = "",
              crop_position: float = 0.5, own: float = 0.0, saturation: float = 1.0, wash: bool = False) -> dict:
    """Recolour the anchor into the fair's colour and frame it for the canvas.

    One ffmpeg pass does the framing and the tint, so the clip keeps every frame
    it came with and a closed loop stays closed: the tint is a pure function of
    each pixel and the crop is the same on every frame.
    """
    ffmpeg = find_ffmpeg()
    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    info = probe(anchor)
    crop_width, crop_height, crop_x, crop_y = window_of(info, width, height, crop_position)
    # A window of the plate at the canvas' own shape, then one even scale: the
    # geometry of the approved plate survives, which a squash does not.
    steps = (f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},"
             f"scale={width}:{height}:flags=lanczos")
    close = closing_window(anchor, ffmpeg, colour, canvas, finish, crop_position, own=own, saturation=saturation,
                           wash=wash)
    run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(anchor), "-vf",
         C.filter_for(colour, prefix=steps, finish=finish, keep=own, saturation=saturation, wash=wash)
         # The loop runs to the frame before the plate repeats itself, so the
         # wrap continues the motion instead of holding the same picture twice.
         + f",trim=start_frame={close['start']}:end_frame={close['frame'] + 1},setpts=PTS-STARTPTS," + EVEN,
         # A keyframe every ten frames: the film pass seeks this clip once per frame, and a seek
         # decodes from the keyframe before it. At the encoder's own spacing the film took half as long again.
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-g", "10", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(out)])
    made = probe(out)
    return {"frames": made["frames"], "width": made["width"], "height": made["height"],
            "seconds": made["seconds"], "colour": colour, "finish": finish,
            "close": close, "filter": C.wash_chain(colour) if wash else C.chain(colour)}


def still_ends(command: list[str]) -> list[str]:
    """Give a graph that holds a still image its own end, and its own limit.

    A still image read into a filter graph is an endless stream unless the
    output states how long it wants. Every ffmpeg call in this skill passes
    through here first, so a later change cannot reintroduce an encode that
    never finishes.
    """
    if "-loop" in command and "-t" not in command and "-shortest" not in command:
        raise Stop("a still image was about to be looped into a clip with no end; the call needs -t or -shortest")
    return command


def page_matte(kit: "Kit", look: dict, slots: dict, canvas: str, scale: float, work: Path):
    """Everything the page lays over its picture, read off two prints: the page over black and over white.

    Over black the print is the page's own light. The difference between the two prints is how much
    of the picture shows through at each pixel, per channel, so soft type edges and the scrim's
    gradient come out exact. A film frame is then `over black + through * the clip's frame`: what the
    browser would have drawn over that frame, without a print per frame.
    """
    import numpy as np
    from PIL import Image

    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    prints = []
    for name, colour in (("black", (0, 0, 0)), ("white", (255, 255, 255))):
        flat = work / f"matte-{name}.png"
        Image.new("RGB", (16, 16), colour).save(flat)
        page = work / f"matte-{name}.html"
        page.write_text(render_html(kit, look, slots, canvas, flat, scale))
        shots = work / f"matte-{name}-shot"
        print_job(page, shots=shots, width=width, height=height)
        shot = shots / "p-01.png"
        if not shot.is_file():
            raise Stop("the app printed no page to lay over the film")
        with Image.open(shot) as image:
            image = image.convert("RGB")
            if image.size != (width, height):
                image = image.resize((width, height), Image.LANCZOS)
            prints.append(np.asarray(image).astype(np.float32))
    over_black, over_white = prints
    through = np.clip((over_white - over_black) / 255.0, 0.0, 1.0)
    return over_black, through


def compose_over(loop: Path, matte, mp4: Path, info: dict, width: int, height: int, ffmpeg: str) -> float | None:
    """The film as the page laid over every frame of the loop, in seconds; None when it could not be made."""
    import numpy as np

    over_black, through = matte
    started = time.monotonic()
    fps = info["fps"] or FPS
    count = info["frames"] or 150
    read_width, read_height = info["width"], info["height"]
    size = read_width * read_height * 3
    decode = encode = None
    try:
        decode = subprocess.Popen([ffmpeg, "-nostdin", "-v", "error", "-i", str(loop), "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        encode = subprocess.Popen([ffmpeg, "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                   "-s", f"{width}x{height}", "-framerate", str(fps), "-i", "-", "-vf", EVEN, "-an",
                                   "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                                   "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
        written = 0
        while written < count:
            if time.monotonic() - started > FILM_SECONDS:
                raise Stop("the film took too long to lay together")
            raw = decode.stdout.read(size)
            if len(raw) < size:
                break
            # The loop may carry one repeated row or column to keep its sides even; the page does not.
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(read_height, read_width, 3)[:height, :width]
            page = over_black + through * frame.astype(np.float32)
            encode.stdin.write(np.clip(page + 0.5, 0, 255).astype(np.uint8).tobytes())
            written += 1
        encode.stdin.close()
        ended = encode.wait(timeout=ENCODE_SECONDS)
        if written != count or ended != 0 or not mp4.is_file():
            return None
        return time.monotonic() - started
    except (OSError, ValueError, subprocess.SubprocessError, Stop):
        return None
    finally:
        for child in (decode, encode):
            if child is not None and child.poll() is None:
                child.kill()


def compose_motion(film_html: Path, loop: Path, out_dir: Path, animate: str, canvas: str, matte=None) -> dict:
    """The moving poster: the app captures the finished page once per frame.

    The loop is laid UNDER the page instead of being cut out of it: the poster
    page is rendered with the recoloured clip as its background video, the app
    parks the clip on one frame and captures the whole poster — type, marks,
    scrim and moving picture together, the same layout the still has. The clip
    keeps its own frame count and seam.
    """
    from PIL import Image, ImageChops, ImageStat

    ffmpeg = find_ffmpeg()
    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    info = probe(loop)
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4 = out_dir / f"{animate}.mp4"
    gif = out_dir / f"{animate}.gif"

    # The page is laid over each frame of the loop by arithmetic: two prints instead of one per frame,
    # and the picture keeps the loop's own sharpness. The app films the page frame by frame only when
    # that could not be done.
    built_seconds = compose_over(loop, matte, mp4, info, width, height, ffmpeg) if matte is not None else None
    filmed_by = "laid over the loop" if built_seconds is not None else "captured frame by frame"
    if built_seconds is None:
        with tempfile.TemporaryDirectory(prefix="poster-frame-") as tmp:
            root = Path(tmp)
            frames = root / "frames"
            frames.mkdir()
            seek = root / "seek.js"
            shots = root / "shot"
            started = time.monotonic()
            count = info["frames"] or 150
            park = PARK_JS.replace("__FPS__", str(info["fps"] or FPS))
            # One page load for the whole film when the app can film; an older app prints a page per frame.
            seek.write_text(park)
            try:
                print_job(film_html, shots=shots, width=width, height=height, script=seek, frames=count,
                          timeout=FILM_SECONDS)
            except Stop:
                pass
            filmed = sorted(shots.glob("f-*.png")) if shots.is_dir() else []
            if len(filmed) == count:
                for index, shot in enumerate(filmed):
                    grow(shot, frames / f"f-{index:05d}.png", (width, height))
            else:
                for index in range(count):
                    if time.monotonic() - started > FILM_SECONDS:
                        raise Stop(
                            f"the film pass took longer than {FILM_SECONDS // 60} minutes at frame {index} "
                            f"of {info['frames']}; the app is not keeping up, so the poster stops here"
                        )
                    seek.write_text(f"({park})({index})")
                    print_job(film_html, shots=shots, width=width, height=height, script=seek)
                    grow(shots / "p-01.png", frames / f"f-{index:05d}.png", (width, height))
            built_seconds = time.monotonic() - started
            seconds = (info["frames"] or 150) / (info["fps"] or FPS)
            run(still_ends([ffmpeg, "-nostdin", "-v", "error", "-y", "-framerate", str(info["fps"] or FPS),
                 "-i", str(frames / "f-%05d.png"), "-vf", EVEN, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                 # The length is stated, never inferred: a still or an endless input
                 # in the graph can then neither extend the film nor keep it running.
                 "-t", f"{seconds:.3f}", "-shortest",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)]))

    with tempfile.TemporaryDirectory(prefix="poster-gif-") as tmp:
        gif_size = (GIF_WIDTH, round(height * GIF_WIDTH / width))
        # About eight frames a second, spread evenly over the loop's own frames, so the wrap back to
        # the first frame is one more even step and never a reset. A poster is one hue and its ink:
        # few colours, an ordered dither and a hold on pixels that did not change keep the file a size
        # people post. The same film as a full-colour GIF at twelve frames a second ran 30 to 65 MB.
        total = info["frames"] or 150
        seconds_long = total / (info["fps"] or FPS)
        wanted = max(8, min(total, round(seconds_long * GIF_FPS)))
        picks = sorted({min(total - 1, round(index * total / wanted)) for index in range(wanted)})
        # The hold reads the frames before each one, and a loop's first frame follows its last: the
        # film is read twice, the end of the first pass warms the hold, and only the second pass is kept.
        # Without that the first frame alone is unheld and the GIF pops where it wraps.
        lead = picks[-min(6, len(picks)):]
        select = "+".join(f"eq(n\\,{pick})" for pick in lead + [pick + total for pick in picks])
        rate = len(picks) / seconds_long
        for colours in GIF_COLOURS:
            run([ffmpeg, "-nostdin", "-v", "error", "-y", "-stream_loop", "1", "-i", str(mp4), "-vf",
                 f"select='{select}',scale={gif_size[0]}:{gif_size[1]}:flags=lanczos,hqdn3d=0:0:5:5,"
                 f"trim=start_frame={len(lead)},setpts=N/({rate:.4f})/TB,"
                 f"split[njk_a][njk_b];[njk_a]palettegen=max_colors={colours}:stats_mode=full[njk_p];"
                 "[njk_b][njk_p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                 "-r", f"{rate:.4f}", str(gif)])
            if gif.is_file() and 0 < gif.stat().st_size <= GIF_BYTES:
                break
        if not gif.is_file() or not gif.stat().st_size:
            raise Stop("the moving poster produced no frames for its GIF")
        with Image.open(gif) as made:
            frames_in_gif = made.n_frames

    with tempfile.TemporaryDirectory(prefix="poster-seam-") as tmp:
        run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(mp4), "-vf", "scale=270:338",
             str(Path(tmp) / "f-%05d.png")])
        files = sorted(Path(tmp).glob("f-*.png"))
        if len(files) < 3:
            raise Stop("the moving poster produced too few frames to read")
        images = []
        for index in sorted({0, 1, 2, len(files) // 2, len(files) - 1}):
            with Image.open(files[index]) as image:
                images.append(image.convert("RGB"))
        difference = lambda a, b: sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3
        seam = difference(images[0], images[-1])
        step = max(difference(images[0], images[1]), difference(images[1], images[2]))
        moved = difference(images[0], images[len(images) // 2])
    # Read the film back: the same frame count and the length that was asked for.
    made = probe(mp4)
    expected_seconds = (info["frames"] or 150) / (info["fps"] or FPS)
    if made["frames"] != (info["frames"] or 150):
        raise Stop(f"the film holds {made['frames']} frames, the loop {info['frames']}")
    if abs(made["seconds"] - expected_seconds) > 0.2:
        raise Stop(f"the film runs {made['seconds']:.2f} s, the loop {expected_seconds:.2f} s")
    return {
        "mp4": mp4.name, "gif": gif.name, "frames": made["frames"], "fps": info["fps"],
        "seconds": round(made["seconds"], 3), "builtSeconds": round(built_seconds, 1), "filmedBy": filmed_by,
        "buildLimitSeconds": FILM_SECONDS,
        "seam_mean_rgb": round(seam, 3), "step_mean_rgb": round(step, 3), "motion_mean_rgb": round(moved, 3),
        "gif_frames": frames_in_gif, "gif_width": GIF_WIDTH, "gif_bytes": gif.stat().st_size,
    }


def choose_still_frame(anchor: Path, info: dict, width: int, height: int, crop_position: float,
                       rects: dict, ffmpeg: str, only: int | None = None, dark: bool = False) -> dict:
    """The plate's frame whose bright highlight is clear of every text block.

    A still poster is read once, so it must not put the plate's brightest patch
    behind a line of type: white words on a white highlight are no words. Every
    candidate frame is measured inside the boxes the page itself reported for its
    slots, and the frame whose worst box is darkest wins. `only` measures that one frame
    instead: a photo look's still is the photo at its widest, the way the brand posts it.
    """
    import numpy as np
    from PIL import Image

    boxes = {slot: box for slot, box in (rects or {}).items() if slot in ("headline", "venue", "band", "tag", "cue", "claim", "year")}
    if not boxes:
        return {"frame": 0, "worstLuma": None, "slots": {}, "candidates": 0}
    crop_width, crop_height, crop_x, crop_y = window_of(info, width, height, crop_position)
    scan_width = 240
    scan_height = max(2, int(round(scan_width * height / width)))
    with tempfile.TemporaryDirectory(prefix="still-frame-") as tmp:
        run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(anchor), "-vf",
             f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale={scan_width}:{scan_height}",
             "-fps_mode", "passthrough", str(Path(tmp) / "s-%05d.png")])
        files = sorted(Path(tmp).glob("s-*.png"))
        if not files:
            return {"frame": 0, "worstLuma": None, "slots": {}, "candidates": 0}
        best = None
        for index in ([only] if only is not None else range(0, len(files), 5)):
            with Image.open(files[index]) as image:
                luma = np.asarray(image.convert("L")).astype(float)
            per_slot = {}
            for slot, (u, v, w, h) in boxes.items():
                y0, y1 = int(v * scan_height), max(int((v + h) * scan_height), int(v * scan_height) + 1)
                x0, x1 = int(u * scan_width), max(int((u + w) * scan_width), int(u * scan_width) + 1)
                patch = luma[max(y0, 0):min(y1, scan_height), max(x0, 0):min(x1, scan_width)]
                per_slot[slot] = round(float(patch.mean()) if patch.size else 0.0, 1)
            # White words want the darkest plate behind every line, dark words the lightest.
            worst = (min if dark else max)(per_slot.values()) if per_slot else 0.0
            if best is None or (worst > best["worstLuma"] if dark else worst < best["worstLuma"]):
                best = {"frame": index, "worstLuma": worst, "slots": per_slot, "candidates": len(files)}
    return best


def _probe_script(root: Path) -> Path:
    """The layout probe, written where the print job can reach it."""
    script = root / "probe.js"
    script.write_text(PROBE_JS)
    return script


def screen_fit(canvas: str) -> float:
    """How far the page must shrink to fit the screen the app captures on.

    A hidden capture window cannot be taller than the display, and a page taller
    than the window is cut. The whole page is scaled by one factor instead, and
    the picture is grown back to the canvas afterwards. On a normal Mac screen
    the factor is 1 and nothing changes.
    """
    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    if not os.environ.get("NODEJAM_PRINT"):
        return 1.0  # Playwright's headless page has no screen to fit: the page prints as it is shot
    limit_width, limit_height = 1080, 1200
    scale = min(1.0, limit_width / width, limit_height / height)
    return round(scale, 4)


def grow(source: Path, out: Path, size: tuple[int, int]) -> None:
    """The captured page at its own canvas size, whatever the capture window allowed."""
    from PIL import Image

    with Image.open(source) as image:
        if image.size == size:
            image.convert("RGB").save(out)
            return
        image.convert("RGB").resize(size, Image.LANCZOS).save(out)


def build_one(kit: Kit, brief: dict, slots: dict, look: dict, args, canvas: str, out: Path) -> dict:
    """One canvas of one poster: the loop, the stills, the PNG, PDF, MP4 and GIF."""
    # A photo look is a still poster: the fair's own photo, recoloured, never moved.
    still_only = bool(look.get("photo"))
    if still_only:
        # The plate lives with the poster, never in the person's folder.
        (out / ".work").mkdir(exist_ok=True)
        top = float(slots.get("photoTop") or 1.0)
        anchor = photo_plate(kit.root / slots["photo"], out / ".work" / f"{slug_of(brief)}-photo-{round(top * 100)}.png", top)
        # A moving file left by an earlier run would sit beside the still as if it belonged to it.
        for stale in (f"{slug_of(brief)}-{canvas}-motion.mp4", f"{slug_of(brief)}-{canvas}-motion.gif",
                      f"{slug_of(brief)}-{canvas}-loop.mp4"):
            (out / stale).unlink(missing_ok=True)
    else:
        anchor = kit.anchor(look, spare=args.spare_anchor)
    loop = out / f"{slug_of(brief)}-{canvas}-loop.mp4"
    finish = str(look.get("finish") or "")
    crop_position = float(look.get("cropY", 0.5))
    # A photo look keeps part of the photo's own colour; every other look is a full recolour.
    own, saturation = float(look.get("keep") or 0.0), float(look.get("saturation") or 1.0)
    # A light look takes the colour as a wash over white paper; every other look takes the three-stop tint.
    wash = bool(look.get("wash"))
    loop_info = None if still_only else tint_clip(anchor, loop, slots["colour"], canvas, finish, crop_position, own, saturation,
                                                  wash=wash)

    work = out / ".work"
    work.mkdir(exist_ok=True)
    background = out / f"{slug_of(brief)}-{canvas}-background.png"
    fit = {"scale": screen_fit(canvas)}

    # First pass: the page with the plate's own first frame, to learn where its
    # slots sit. Second pass: the same page with the frame that keeps the plate's
    # highlight clear of every one of them.
    with tempfile.TemporaryDirectory(prefix="poster-probe-") as probe_tmp:
        probe_dir = Path(probe_tmp)
        tint_still(anchor, background, slots["colour"], canvas, finish, crop_position, own=own, saturation=saturation,
                   wash=wash)
        probe_html = probe_dir / "probe.html"
        probe_html.write_text(render_html(kit, look, slots, canvas, background, fit["scale"]))
        layout = json.loads(print_job(probe_html, shots=probe_dir / "shot", script=_probe_script(probe_dir),
                                      width=CANVASES[canvas][0], height=CANVASES[canvas][1]) or "{}")
        if isinstance(layout, str):
            layout = json.loads(layout)
        if not isinstance(layout, dict):
            layout = {"probe": layout}

    still = choose_still_frame(anchor, probe(anchor), CANVASES[canvas][0], CANVASES[canvas][1],
                               crop_position, layout.get("rects") or {}, find_ffmpeg(),
                               only=0 if look.get("photo") else None, dark=dark_type(look))
    tint_still(anchor, background, slots["colour"], canvas, finish, crop_position, still["frame"],
               own=own, saturation=saturation, wash=wash)

    with tempfile.TemporaryDirectory(prefix="poster-") as tmp:
        tmp_path = Path(tmp)
        full_html = tmp_path / "poster.html"
        full_html.write_text(render_html(kit, look, slots, canvas, background, fit["scale"]))
        pdf = out / f"{slug_of(brief)}-{canvas}.pdf"
        png = out / f"{slug_of(brief)}-{canvas}.png"
        shots = tmp_path / "shot"
        script = tmp_path / "probe.js"
        script.write_text(PROBE_JS)
        probe_out = print_job(
            full_html, pdf=pdf, shots=shots, script=script,
            width=CANVASES[canvas][0], height=CANVASES[canvas][1],
        )
        shot = shots / "p-01.png"
        if not shot.is_file():
            raise Stop("no page was printed; the poster cannot be exported")
        grow(shot, png, (CANVASES[canvas][0], CANVASES[canvas][1]))
        final = json.loads(probe_out) if probe_out.strip() else {}
        if isinstance(final, str):
            final = json.loads(final)
        if isinstance(final, dict):
            layout.update({key: value for key, value in final.items() if key != "rects"})
            layout.setdefault("rects", final.get("rects") or {})
        layout["fit_scale"] = fit["scale"]
        layout["stillFrame"] = still["frame"]
        layout["stillSlots"] = still["slots"]
        layout["stillWorstLuma"] = still["worstLuma"]
        layout["stillCandidates"] = still["candidates"]

        # The film page lives beside the poster's own files: the frames are
        # captured after this block closes, so it cannot sit in a temp folder.
        film_html = work / "film.html"
        if not still_only:
            film_html.write_text(render_html(kit, look, slots, canvas, loop, fit["scale"], motion=True,
                                             faces_in=font_faces(kit.root)))
    matte = None
    if not still_only:
        try:
            matte = page_matte(kit, look, slots, canvas, fit["scale"], work)
        except Stop:
            matte = None
    motion = None if still_only else compose_motion(film_html, loop, out, f"{slug_of(brief)}-{canvas}-motion", canvas, matte)
    return {
        "canvas": canvas, "look": look["name"], "family": look.get("family"), "colour": slots["colour"],
        "calendarColour": slots.get("calendarColour"), "calendarMark": slots.get("calendarMark"),
        "cropY": crop_position,
        "calendarName": slots.get("calendarName"), "finish": finish, "keep": own, "saturation": saturation,
        "wash": wash,
        "motionFloor": look.get("motionFloor"), "still": still_only, "darkType": dark_type(look),
        "anchor": anchor.name, "loop": loop_info, "motion": motion, "layout": layout,
        "anchorFile": str(anchor.relative_to(out)) if anchor.is_relative_to(out) else None,
        "files": {"png": png.name, "pdf": pdf.name, "background": background.name,
                  **({} if still_only else {"mp4": motion["mp4"], "gif": motion["gif"], "loop": loop.name})},
    }


def slug_of(brief: dict) -> str:
    # A moving poster keeps its own folder and names beside the fair's still poster.
    # The same fair in another of the folder's moving looks is named for that look.
    tail = f"-{brief['movingIn']}" if brief.get("movingIn") else ("-moving" if brief.get("moving") else "")
    # A thank-you is a post of its own, so it never lands on the announcement it follows.
    thanks = "-thanks" if brief.get("thanks") else ""
    return (slugify(f"{brief.get('fair')}-{brief.get('year') or ''}") or "poster") + thanks + tail


SIZES = ["4x5", "9x16", "1x1", "a4"]


def canvas_list(value: str) -> list[str]:
    """One size or several with commas, each once, in the order asked."""
    names = [part.strip() for part in value.split(",") if part.strip()]
    if not names or any(name not in CANVASES for name in names):
        raise argparse.ArgumentTypeError(f"give one or more of {', '.join(SIZES)}, with commas between")
    return list(dict.fromkeys(names))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Make one fair poster from the brand folder.")
    parser.add_argument("--kit", required=True, help="the brand folder the person pointed the app at")
    parser.add_argument("--fair", required=True, help="the fair's brief JSON")
    parser.add_argument("--out", help="where the poster goes (default: <kit>/posters/<fair>-<year>)")
    parser.add_argument("--canvas", default=["4x5"], type=canvas_list,
                        help="one size, or several in one run with commas between (4x5,9x16)")
    parser.add_argument("--all-canvases", action="store_true", help="4x5, 9x16, 1x1 and a4, each its own set")
    parser.add_argument("--spare-anchor", action="store_true", help="use the look's spare anchor")
    args = parser.parse_args(argv)

    kit = Kit(Path(args.kit))
    brief = read_json(Path(args.fair))
    slots = slots_from(brief, kit)
    look = kit.look_for(brief)
    if brief.get("moving"):
        # The moving version of a fair: the ask's look, else the one the calendar row names for it,
        # in the row's own colour. A still photo never moves, so a photo look cannot be it.
        name = brief.get("look") or kit.fair_for(brief).get("moving")
        found = kit.looks.get(name) or next((l for l in kit.looks.values() if l.get("family") == name), None)
        if not found:
            raise Stop("the calendar names no moving look for this fair; name a look whose loop moves "
                       f"({', '.join(n for n, l in kit.looks.items() if not l.get('photo'))})")
        if found.get("photo"):
            raise Stop(f"the {found['name']} look is a still photo; a moving poster needs a look whose loop moves")
        look = found
        if found["name"] != kit.fair_for(brief).get("moving") and kit.fair_for(brief).get("moving"):
            brief["movingIn"] = found["name"]
    # A fair's row may hold its colour in a look other than its own: a pale look and a deep one
    # rarely share one. The ask's own colour still wins on the page.
    look_colour = str((kit.fair_for(brief).get("colours") or {}).get(look["name"]) or "").strip()
    if look_colour:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", look_colour):
            raise Stop(f"the calendar's colour for the {look['name']} look must be #RRGGBB, not {look_colour!r}")
        slots["calendarColour"] = look_colour
        if not brief.get("colour"):
            slots["colour"] = look_colour
    if look.get("photo"):
        if not slots["photo"]:
            raise Stop(f"the {look['name']} look draws the fair's own photo, and neither the ask nor the calendar names one")
        if not (kit.root / slots["photo"]).is_file():
            raise Stop(f"the photo {slots['photo']} is not in {kit.root}")
    # Her photo posts carry no claim line; a look says so, and an ask can still give one.
    if look.get("claim") is False and not brief.get("claim"):
        slots["claim"] = ""
    # A look whose posts carry no certification strip keeps it off the page, whatever the brief lists.
    if look.get("marks") is False:
        slots["marks"] = []
    # The look's own word over the booth (her photo posts say VISIT US), unless the ask gives one.
    if look.get("cue") and slots["tag"] and not brief.get("cue"):
        slots["cue"] = str(look["cue"])
    out = Path(args.out).resolve() if args.out else (kit.root / "posters" / slug_of(brief))
    out.mkdir(parents=True, exist_ok=True)

    canvases = SIZES if args.all_canvases else args.canvas
    built = [build_one(kit, brief, slots, look, args, canvas, out) for canvas in canvases]
    ask = {key: value for key, value in brief.items() if key != "movingIn"}
    # A later run for another size of the same ask adds to the folder: the manifest keeps the sizes made
    # before, so the check still reads every one of them. A changed ask starts the manifest over.
    manifest = out / f"{slug_of(brief)}.json"
    earlier = []
    if manifest.is_file():
        try:
            before = json.loads(manifest.read_text())
        except ValueError:
            before = {}
        if isinstance(before, dict) and before.get("ask") == ask and before.get("look") == look["name"]:
            made = {item["canvas"] for item in built}
            earlier = [item for item in before.get("canvases") or []
                       if isinstance(item, dict) and item.get("canvas") in CANVASES and item["canvas"] not in made
                       and (out / str((item.get("files") or {}).get("png") or "-")).is_file()]
    result = {
        "fair": brief.get("fair"), "city": brief.get("city"), "country": brief.get("country"),
        "year": brief.get("year"), "look": look["name"],
        # The ask this poster was made from, so a later change starts from it and nothing is searched for.
        "ask": ask,
        "slots": {key: (str(value) if not isinstance(value, list) else [p.name for p in value])
                  for key, value in slots.items() if key not in ("wordmark", "partner")},
        "wordmark": slots["wordmark"].name if slots.get("wordmark") else None,
        "partner": slots["partner"].name if slots["partner"] else None,
        "marks": [path.name for path in slots["marks"]],
        "canvases": sorted(earlier + built, key=lambda item: SIZES.index(item["canvas"])),
    }
    manifest.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"out": str(out), "built": [{
        "canvas": item["canvas"], "png": item["files"]["png"], "pdf": item["files"]["pdf"],
        "mp4": item["files"].get("mp4"), "gif": item["files"].get("gif"),
        "clipped": item["layout"].get("clipped"), "fonts": item["layout"].get("fonts"),
    } for item in built]}, indent=2))
    return 0


def window_of(info: dict, width: int, height: int, position: float = 0.5) -> tuple[int, int, int, int]:
    """The largest window of the plate at the canvas' shape, at `position` down it.

    A 9:16 plate on a 4:5 page has room for a 4:5 window and nothing more; taking
    that window keeps every shape the plate drew, while scaling the whole plate
    down the page squashes the picture and drags its dark band through the middle.
    `position` is where the window sits: 0 the top, 0.5 the middle, 1 the foot.
    """
    plate_width, plate_height = info["width"], info["height"]
    crop_height = min(plate_height, int(round(plate_width * height / width)))
    crop_width = min(plate_width, int(round(crop_height * width / height)))
    crop_width -= crop_width % 2
    crop_height -= crop_height % 2
    x = max(0, (plate_width - crop_width) // 2)
    y = int(round(max(0.0, min(1.0, position)) * (plate_height - crop_height)))
    return crop_width, crop_height, x, y


def tint_still(anchor: Path, out: Path, colour: str, canvas: str, finish: str = "",
               crop_position: float = 0.5, frame: int = 0, own: float = 0.0, saturation: float = 1.0,
               wash: bool = False) -> dict:
    """The first frame of the anchor, framed and tinted the same way the loop is."""
    ffmpeg = find_ffmpeg()
    width, height = CANVASES[canvas][0], CANVASES[canvas][1]
    info = probe(anchor)
    crop_width, crop_height, crop_x, crop_y = window_of(info, width, height, crop_position)
    steps = (f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},"
             f"scale={width}:{height}:flags=lanczos")
    # The plate is read at the frame the still poster wants, then framed and
    # finished exactly like the moving poster's own frames.
    run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(anchor), "-vf",
         f"select=eq(n\\,{frame})," + C.filter_for(colour, still=True, prefix=steps, finish=finish, keep=own,
                                                    saturation=saturation, wash=wash),
         "-frames:v", "1", "-fps_mode", "passthrough", "-update", "1", str(out)])
    return {"width": width, "height": height, "frame": frame}


#: Parks the page on one frame of the film: the clip seeked and painted. The app calls it once per
#: frame in a single page load (`--frames`), or an older app runs it as `(PARK_JS)(n)` per print.
PARK_JS = """(frame) => (async () => {
  const clip = document.querySelector('video[data-slot=background]')
  if (!clip) return 'no clip on the page'
  // Frame 0 needs decoded data, not only metadata: a seek to where the clip already stands
  // can resolve before anything is painted, and the film's first frame came out black.
  if (clip.readyState < 2) await new Promise((done) => clip.addEventListener('loadeddata', done, { once: true }))
  clip.pause()
  const wanted = Math.min(frame / __FPS__, Math.max((clip.duration || 0) - 0.001, 0))
  // The first frame after a load waits for the clip to paint (it came out black once); later frames in the
  // same page are painted by the two animation frames below, and the wait would cost half a second each.
  const painted = clip.requestVideoFrameCallback && frame === 0
    ? Promise.race([new Promise((done) => clip.requestVideoFrameCallback(() => done())), new Promise((done) => setTimeout(done, 500))])
    : Promise.resolve()
  await new Promise((done) => {
    clip.addEventListener('seeked', done, { once: true })
    clip.currentTime = wanted
  })
  await painted
  await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))
  return 'frame ' + frame + ' of ' + (clip.duration || 0).toFixed(3)
})()"""


PROBE_JS = """(() => {
  const slide = document.querySelector('.slide');
  const box = slide.getBoundingClientRect();
  const clipped = [];
  for (const el of slide.querySelectorAll('[data-slot]')) {
    const r = el.getBoundingClientRect();
    const text = (el.textContent || '').trim();
    const image = el.tagName === 'IMG';
    if (r.width <= 0 || r.height <= 0) { clipped.push(`${el.dataset.slot}: empty box`); continue; }
    if (r.left < box.left - 1 || r.top < box.top - 1 || r.right > box.right + 1 || r.bottom > box.bottom + 1)
      clipped.push(`${el.dataset.slot}: outside the page`);
    if (!image && el.scrollWidth > el.clientWidth + 1) clipped.push(`${el.dataset.slot}: wider than its column`);
    if (!image && el.scrollHeight > el.clientHeight + 6) clipped.push(`${el.dataset.slot}: taller than its line`);
    if (image && (!el.complete || el.naturalWidth === 0)) clipped.push(`${el.dataset.slot}: image did not load`);
    if (!image && !text && !el.querySelector('img')) clipped.push(`${el.dataset.slot}: empty`);
  }
  const fonts = new Set();
  for (const el of slide.querySelectorAll('[data-slot]')) if (el.tagName !== 'IMG') fonts.add(getComputedStyle(el).fontFamily);
  const images = [...slide.querySelectorAll('img')].map((el) => (el.getAttribute('src') || '').split('/').pop());
  const rects = {};
  for (const el of slide.querySelectorAll('[data-slot]')) {
    const r = el.getBoundingClientRect();
    if (el.tagName === 'IMG' || r.width <= 0) continue;
    rects[el.dataset.slot] = [r.left / box.width, r.top / box.height, r.width / box.width, r.height / box.height];
  }
  return JSON.stringify({ size: [Math.round(box.width), Math.round(box.height)], images, rects, clipped, fonts: [...fonts],
    empty: [...slide.querySelectorAll('[data-slot]')]
      .filter((el) => el.tagName !== 'IMG' && !(el.textContent || '').trim() && !el.querySelector('img'))
      .map((el) => el.dataset.slot) });
})()"""


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as stop:
        print(f"STOP {stop}", file=sys.stderr)
        sys.exit(2)
