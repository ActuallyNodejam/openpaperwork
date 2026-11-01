#!/usr/bin/env python3
"""Check one fair poster the way a script can, and leave the eye the rest.

Decided here: the canvas, every slot inside the page and filled, the right marks,
the colour that was asked for, the loop closed and moving with the anchor's own
frame count, house fonts only, and the PDF really printed.
Left to the reader: whether it reads as well as the brand's own poster.

    python3 check.py "<poster folder>" [--colour "#RRGGBB"]

Exit 0 when every line passes, 2 when something fails. A failing line says what
to fix; it is never a refusal mid-build.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import colourway as C  # noqa: E402

CANVASES = {"4x5": (1080, 1350), "9x16": (1080, 1920), "1x1": (1080, 1080), "a4": (794, 1123)}
SEAM_ALLOWANCE = 1.5
#: Her own posts move about 14 to 20 mean RGB between thirds of a loop; a clip
#: under this is a still with a tint on it.
MOTION_FLOOR = 8.0
#: A single-colour mark's opaque pixels sit within this spread across channels.
SINGLE_COLOUR_SPREAD = 18
#: Her own GIFs are 800 wide; each canvas keeps its own shape at that width (4:5 is 800x1000).
GIF_WIDTH = 800
#: A still poster must not put the plate's bright highlight behind a line of
#: type: white words on a near-white patch are no words. This is the box's luma
#: ceiling, measured on the plate's own frame with the look's own chain.
TEXT_BOX_LUMA = 195
#: A look with dark words is the other way round: the plate behind a line must
#: stay light enough to carry them.
TEXT_BOX_DARK = 80
#: The jump from a loop's last frame back to its first, on a 270-wide read. A
#: normal frame step in these plates runs 1.1 to 1.3, so the seam must sit at or
#: under a step: bigger is a visible reset, and much smaller means the loop ends
#: on a copy of its own first frame, which the eye reads as a stutter.
LOOP_JUMP = 2.0
#: A GIF over this is no longer a file people post.
GIF_BYTES = 15_000_000
#: Under this, the last frame is a copy of the first and the loop stutters.
LOOP_DUPLICATE = 0.35
#: The PNG is the PDF's page as a picture. Read in horizontal bands at 270 wide, a
#: faithful capture differs by a few points of mean RGB (antialiasing, the PDF's
#: own image compression); a band the capture cut off differs by tens.
PDF_BAND_DRIFT = 10.0
PDF_BANDS = 10
FFMPEG = "ffmpeg"


def decoded_frames(path: Path, size: tuple[int, int], wanted: list[int], step_series: bool = False) -> dict:
    """The clip's frames at the indices asked for, and how much each frame moves.

    Frames are read small: a seam and a step are mean differences, and a full
    size read would spend seconds to measure the same number.
    """
    import numpy as np

    width, height = size
    out: dict = {}
    small = (max(1, width // 8), max(1, height // 8))
    with tempfile.TemporaryDirectory(prefix="poster-check-") as tmp:
        result = subprocess.run(
            [FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(path), "-vf",
             f"scale={small[0]}:{small[1]}", str(Path(tmp) / "f-%05d.png")],
            capture_output=True,
        )
        files = sorted(Path(tmp).glob("f-*.png"))
        if result.returncode != 0 or not files:
            return {}
        from PIL import Image

        count = len(files)
        for index in wanted:
            if 0 <= index < count:
                with Image.open(files[index]) as image:
                    out[index] = np.asarray(image.convert("RGB"))
        if step_series and count > 2:
            previous = None
            steps = []
            for path in files:
                with Image.open(path) as image:
                    frame = np.asarray(image.convert("RGB")).astype(np.int16)
                if previous is not None:
                    steps.append(float(np.abs(frame - previous).mean()))
                previous = frame
            out["series"] = steps
            mid = count // 2
            with Image.open(files[mid]) as image:
                out["middle"] = np.asarray(image.convert("RGB"))
            with Image.open(files[-1]) as image:
                out["last"] = np.asarray(image.convert("RGB"))
        out["count"] = count
    return out


def tinted_anchor(anchor: Path, size: tuple[int, int], colour: str, finish: str = "", crop_y: float = 0.5,
                  frame: int = 0, *, own: float = 0.0, saturation: float = 1.0, wash: bool = False):
    """The anchor's first frame, framed and tinted exactly as the poster's is.

    The window and the look's finish step are the script's own, taken from it
    rather than copied, so a change to the framing cannot leave this check
    measuring a different picture than the one the poster printed.
    """
    import numpy as np
    import poster as P

    width, height = size
    info = P.probe(anchor)
    crop_width, crop_height, crop_x, crop_y_px = P.window_of(info, width, height, crop_y)
    steps = (f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y_px},"
             f"scale={width}:{height}:flags=lanczos")
    with tempfile.TemporaryDirectory(prefix="poster-anchor-") as tmp:
        out = Path(tmp) / "anchor.png"
        result = subprocess.run(
            [FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(anchor), "-vf",
             f"select=eq(n\\,{frame})," + C.filter_for(colour, still=True, prefix=steps, finish=finish, keep=own,
                                                        saturation=saturation, wash=wash),
             "-frames:v", "1", "-fps_mode", "passthrough", "-update", "1", str(out)],
            capture_output=True,
        )
        if result.returncode != 0 or not out.is_file():
            return None, steps
        from PIL import Image

        with Image.open(out) as image:
            if image.size != (width, height):
                return None, steps
            return np.asarray(image.convert("RGB")), steps


def gif_jump(path: Path):
    """The mean difference between a GIF's last frame and its first, and its own median step."""
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        frames = []
        for index in range(image.n_frames):
            image.seek(index)
            frames.append(np.asarray(image.convert("RGB").resize((216, 270), Image.LANCZOS)).astype(np.float32))
    if len(frames) < 2:
        return None
    steps = [float(np.abs(one - two).mean()) for one, two in zip(frames, frames[1:])]
    return float(np.abs(frames[0] - frames[-1]).mean()), float(np.median(steps))


def mark_spread(path: Path):
    """How far a mark's opaque pixels sit from one flat colour, 0 to 255.

    A single-colour mark — the version a dark look takes — has every opaque
    pixel on one ink, so its channels differ by almost nothing. A full-colour
    mark spreads across the wheel and reads well over 18.
    """
    import numpy as np
    from PIL import Image

    if not path.is_file():
        return None
    with Image.open(path) as image:
        rgba = np.asarray(image.convert("RGBA"))
    opaque = rgba[rgba[:, :, 3] > 128][:, :3].astype(float)
    if not len(opaque):
        return None
    spread = opaque.max(axis=1) - opaque.min(axis=1)
    return int(round(float(spread.mean())))


def pdf_page(path: Path, size: tuple[int, int]):
    """The PDF's first page rendered at the PNG's own size, or None when it cannot be read."""
    import numpy as np
    from PIL import Image

    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    document = pdfium.PdfDocument(str(path))
    try:
        page = document[0]
        width, _ = page.get_size()
        picture = page.render(scale=size[0] / width).to_pil()
    finally:
        document.close()
    return np.asarray(picture.convert("RGB").resize(size, Image.LANCZOS))


def band_drift(png, page) -> list[float]:
    """Mean RGB difference between the PNG and the PDF's page, one number per horizontal band."""
    import numpy as np
    from PIL import Image

    small = (270, max(PDF_BANDS, round(270 * png.shape[0] / png.shape[1])))
    a = np.asarray(Image.fromarray(png).resize(small, Image.BOX)).astype(float)
    b = np.asarray(Image.fromarray(page).resize(small, Image.BOX)).astype(float)
    edges = np.linspace(0, small[1], PDF_BANDS + 1).astype(int)
    return [float(np.abs(a[y0:y1] - b[y0:y1]).mean()) for y0, y1 in zip(edges, edges[1:])]


def find_kit(folder: Path) -> Path:
    """The brand folder a poster belongs to: the nearest folder above it with a poster.json."""
    for candidate in [folder, *folder.parents]:
        if (candidate / "poster.json").is_file():
            return candidate
    return folder.parent


def tile_of(frame, u: float, v: float, w: float = 0.04, h: float = 0.04):
    """Mean colour of a small tile at (u, v) of a picture, both as fractions of it."""
    import numpy as np

    height, width = frame.shape[:2]
    x0 = min(max(int(u * width), 0), max(width - 2, 0))
    y0 = min(max(int(v * height), 0), max(height - 2, 0))
    x1 = min(x0 + max(int(w * width), 2), width)
    y1 = min(y0 + max(int(h * height), 2), height)
    return tuple(frame[y0:y1, x0:x1].reshape(-1, 3).astype(float).mean(axis=0))


#: A caption is posted with the poster; LinkedIn holds this many characters.
CAPTION_MOST = 3000
#: A number standing on its own in a caption: a date, a booth, an hour, a share. A number inside a word
#: (T2T, CO2, a hashtag) is part of a name.
NUMBER = re.compile(r"(?<![\w#@])\d+(?:[.,:]\d+)*(?:\s?%)?(?![\w])")


def caption_lines(folder: Path, stem: str, data: dict, kit: Path, ok, fail) -> None:
    """The caption beside a poster (<poster>-caption.txt), when there is one: it may state no number the
    poster, the ask and the folder's own claims do not hold, and an announcement says the dates and the booth."""
    path = folder / f"{stem}-caption.txt"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        fail(f"{path.name} is empty")
        return
    if len(text) > CAPTION_MOST:
        fail(f"{path.name} is {len(text)} characters; a post holds {CAPTION_MOST}")
    slots = data.get("slots") or {}
    facts = [str(value) for value in slots.values() if isinstance(value, str)]
    facts += [str(value) for value in (data.get("ask") or {}).values() if isinstance(value, (str, int, float))]
    try:
        house = json.loads((kit / "poster.json").read_text())
    except (OSError, ValueError):
        house = {}
    facts += [str(house.get("claim") or "")] + [str(line) for line in house.get("claims") or []]
    known = {found.replace(" ", "") for fact in facts for found in NUMBER.findall(fact)}
    # A range on the poster (13-14, 11:45-13:00) is two numbers a caption may say apart.
    known |= {part for fact in facts for part in re.findall(r"\d+(?::\d+)?", fact)}
    # An hour (15:00) and a day of the month or a small count (up to 31) may stand: a talk's time and a
    # date said in words are the person's to give. What is caught is a share, a large count or a year
    # that nobody gave.
    plain = lambda number: bool(re.fullmatch(r"\d{1,2}[:.]\d{2}", number)  # noqa: E731
                                or (re.fullmatch(r"\d{1,2}", number) and int(number) <= 31))
    strange = sorted(number for number in {found.replace(" ", "") for found in NUMBER.findall(text)} - known
                     if not plain(number))
    if strange:
        fail(f"{path.name} states {', '.join(strange[:5])}, which the poster, the ask and the folder's claims do not hold; "
             "say only what was given")
    else:
        ok(f"{path.name}: no share, count or year in it that the poster, the ask and the folder's claims do not hold")
    if not (data.get("ask") or {}).get("thanks"):
        days = re.findall(r"\d+", str(slots.get("band") or ""))
        if days and not all(re.search(rf"(?<!\d){day}(?!\d)", text) for day in days):
            fail(f"{path.name} does not say the dates {slots.get('band')}")
        tag = str(slots.get("tag") or "").strip()
        if tag and not all(part.lower() in text.lower() for part in tag.split()):
            fail(f"{path.name} does not say where to find the stand ({tag})")
        elif tag and days:
            ok(f"{path.name}: the dates and {tag} are in it")


def agenda_lines(folder: Path, data: dict) -> int:
    """An agenda card's own checks: its pages whole and printed, every show on the page, house fonts only."""
    import numpy as np
    from PIL import Image

    lines: list[str] = []
    ok = lambda text: lines.append(f"ok   {text}")  # noqa: E731
    fail = lambda text: lines.append(f"FAIL {text}")  # noqa: E731
    rows = data.get("rows") or []
    if not rows:
        fail("the agenda holds no show")
    for row in rows:
        if not str(row.get("name") or "").strip() or not str(row.get("dates") or "").strip():
            fail(f"a show on the agenda has no name or no dates: {row}")
    colours = data.get("colours") or {}
    try:
        luma = lambda value: sum(w * int(value[i:i + 2], 16) for w, i in ((0.2126, 1), (0.7152, 3), (0.0722, 5)))  # noqa: E731
        apart = abs(luma(colours["ink"]) - luma(colours["ground"]))
        if apart < 110:
            fail(f"the words ({colours['ink']}) and the paper ({colours['ground']}) are {apart:.0f} apart in lightness; they must read")
        else:
            ok(f"the words {colours['ink']} read on the paper {colours['ground']}")
    except (KeyError, ValueError, TypeError):
        fail("the agenda's manifest holds no ink and paper colour")
    canvases = data.get("canvases") or []
    if not canvases:
        fail("the agenda's manifest holds no built canvas")
    for built in canvases:
        canvas = built.get("canvas")
        if canvas not in CANVASES:
            fail(f"{canvas}: not a canvas this skill makes")
            continue
        size = CANVASES[canvas]
        files = built.get("files") or {}
        png = folder / str(files.get("png") or "-")
        if not png.is_file():
            fail(f"{canvas}: {files.get('png')} is missing")
            continue
        with Image.open(png) as image:
            if image.size != size:
                fail(f"{canvas}: the PNG is {image.size[0]}x{image.size[1]}, want {size[0]}x{size[1]}")
                continue
            still = np.asarray(image.convert("RGB"))
        ok(f"{canvas}: canvas {size[0]}x{size[1]}")
        pdf = folder / str(files.get("pdf") or "-")
        if not pdf.is_file():
            fail(f"{canvas}: {files.get('pdf')} is missing")
        elif pdf.stat().st_size < 8000:
            fail(f"{canvas}: the PDF is {pdf.stat().st_size} bytes; the page did not print")
        else:
            page = pdf_page(pdf, size)
            if page is None:
                fail(f"{canvas}: the PDF's page could not be rendered to compare with the PNG (needs pypdfium2)")
            else:
                drift = max(band_drift(still, page))
                if drift > PDF_BAND_DRIFT:
                    fail(f"{canvas}: the PNG differs from the PDF's page by {drift:.1f} mean RGB; the capture cut or moved the page")
                else:
                    ok(f"{canvas}: the PNG is the PDF's whole page (worst band drift {drift:.1f} of {PDF_BAND_DRIFT})")
        layout = built.get("layout") or {}
        clipped = layout.get("clipped") or []
        if clipped:
            fail(f"{canvas}: off the page or wider than its column: {', '.join(str(item) for item in clipped[:4])}")
        else:
            ok(f"{canvas}: every row inside the page")
        if layout.get("rows") != len(rows):
            fail(f"{canvas}: the page shows {layout.get('rows')} shows and the agenda holds {len(rows)}")
        else:
            ok(f"{canvas}: {len(rows)} shows on the page")
        strange = sorted({name for name in layout.get("fonts") or []
                          if not re.search(r"Inter|Signal Mono|Noto Sans SC|Instrument Serif", str(name))})
        if strange:
            fail(f"{canvas}: a line is set in {', '.join(strange)}")
        else:
            ok(f"{canvas}: house fonts only")
    for line in data.get("leftOff") or []:
        ok(f"left off the card, to say in the reply: {line}")
    if not any(line.startswith("FAIL") for line in lines):
        ok(f"agenda {data.get('season')}: {len(rows)} shows")
    for line in lines:
        print(line)
    return 2 if any(line.startswith("FAIL") for line in lines) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check one fair poster folder.")
    parser.add_argument("folder", help="the poster folder poster.py wrote")
    parser.add_argument("--colour", help="the fair's colour; the poster here must carry exactly it")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--kit", help="the brand folder, when the poster does not sit inside it")
    args = parser.parse_args(argv)

    global FFMPEG
    FFMPEG = args.ffmpeg
    folder = Path(args.folder).resolve()
    lines: list[str] = []

    def ok(text: str) -> None:
        lines.append(f"ok   {text}")

    def fail(text: str) -> None:
        lines.append(f"FAIL {text}")

    manifests = [path for path in sorted(folder.glob("*.json")) if not path.name.startswith(".")]
    if not manifests:
        print(f"FAIL no poster manifest in {folder}; run poster.py first")
        return 2
    data = json.loads(manifests[0].read_text())
    kit = Path(args.kit).resolve() if args.kit else find_kit(folder)
    try:
        house_partner = json.loads((kit / "poster.json").read_text()).get("partner")
    except (OSError, ValueError):
        house_partner = None
    if data.get("kind") == "agenda":
        return agenda_lines(folder, data)
    canvases = data.get("canvases") or []
    if not canvases:
        print(f"FAIL {manifests[0].name} holds no built canvas")
        return 2

    colour = args.colour or canvases[0]["colour"]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", colour or ""):
        print(f"FAIL the colour {colour!r} is not #RRGGBB")
        return 2

    # A photo look's plate is made beside the poster; every other look's anchor is the kit's.
    plate = canvases[0].get("anchorFile")
    anchor = folder / plate if plate else kit / "anchors" / canvases[0]["anchor"]
    if not anchor.is_file():
        fail(f"the anchor {anchor.name} is not in {anchor.parent}")

    for built in canvases:
        canvas = built["canvas"]
        if canvas not in CANVASES:
            fail(f"{canvas}: not a canvas this skill makes")
            continue
        size = CANVASES[canvas]
        width, height = size
        files = built["files"]

        from PIL import Image
        import numpy as np

        png = folder / files["png"]
        if not png.is_file():
            fail(f"{canvas}: {files['png']} is missing")
            continue
        with Image.open(png) as image:
            if image.size != size:
                fail(f"{canvas}: the PNG is {image.size[0]}x{image.size[1]}, want {width}x{height}")
                continue
            still = np.asarray(image.convert("RGB"))
        ok(f"{canvas}: canvas {width}x{height}")

        for key in ("pdf", "mp4", "gif", "loop", "background"):
            if built.get("still") and key in ("mp4", "gif", "loop"):
                continue
            if not (folder / files[key]).is_file() and not (folder / ".work" / files[key]).is_file():
                fail(f"{canvas}: {files[key]} is missing")
        if not (folder / files["pdf"]).is_file():
            continue
        pdf_bytes = (folder / files["pdf"]).stat().st_size
        if pdf_bytes < 8000:
            fail(f"{canvas}: the PDF is {pdf_bytes} bytes; the page did not print")
        else:
            ok(f"{canvas}: PDF {round(pdf_bytes / 1024)} kB")
            # The PNG must show the whole page the PDF printed: a capture cut by its
            # window loses the bottom of the poster while the PDF keeps it.
            page = pdf_page(folder / files["pdf"], size)
            if page is None:
                fail(f"{canvas}: the PDF's page could not be rendered to compare with the PNG (needs pypdfium2)")
            else:
                drift = band_drift(still, page)
                worst = max(range(len(drift)), key=drift.__getitem__)
                if drift[worst] > PDF_BAND_DRIFT:
                    fail(f"{canvas}: the PNG differs from the PDF's page by {drift[worst]:.1f} mean RGB in band "
                         f"{worst + 1} of {len(drift)} ({round(worst / len(drift) * 100)}% down); the capture "
                         "cut or moved the page, so fix the capture, not the layout")
                else:
                    ok(f"{canvas}: the PNG is the PDF's whole page (worst band drift {drift[worst]:.1f} of {PDF_BAND_DRIFT})")

        layout = built.get("layout") or {}
        empty = layout.get("empty") or []
        if empty:
            fail(f"{canvas}: empty slots reported: {', '.join(str(item) for item in empty[:4])}")
        clipped = layout.get("clipped") or []
        if clipped:
            fail(f"{canvas}: clipped or empty slots: {', '.join(str(item) for item in clipped[:4])}")
        else:
            ok(f"{canvas}: every slot inside the page and filled")
        fonts = layout.get("fonts") or []
        strange = sorted({name for name in fonts if not re.search(r"Inter|Signal Mono|Noto Sans SC|Instrument Serif", str(name))})
        if strange:
            fail(f"{canvas}: a slot is set in {', '.join(strange)}")
        else:
            ok(f"{canvas}: house fonts only")
        measured = layout.get("size")
        scale = float(layout.get("fit_scale") or 1.0) or 1.0
        if measured:
            page = (round(measured[0] / scale), round(measured[1] / scale))
            if abs(page[0] - width) > 2 or abs(page[1] - height) > 2:
                fail(f"{canvas}: the page measured {page} in the app, want {[width, height]}")
            else:
                ok(f"{canvas}: the page laid out at {page[0]}x{page[1]} and was captured at {round(scale, 3)} of it")

        # The colour, the way it was made: the same chain, over the anchor's own first frame.
        # The film: the same length as the loop, and built inside its own time limit.
        motion_info = built.get("motion") or {}
        limit = motion_info.get("buildLimitSeconds")
        built_seconds = motion_info.get("builtSeconds")
        if limit and built_seconds is not None:
            if built_seconds > limit:
                fail(f"{canvas}: the film pass took {built_seconds} s, over its {limit} s limit")
            else:
                ok(f"{canvas}: film built in {built_seconds} s of a {limit} s limit")
        seconds = motion_info.get("seconds")
        loop_seconds = (built.get("loop") or {}).get("seconds")
        if seconds is not None and loop_seconds:
            if abs(seconds - loop_seconds) > 0.2:
                fail(f"{canvas}: the film runs {seconds} s, the loop {loop_seconds} s")
            else:
                ok(f"{canvas}: film runs {seconds} s, the loop's own length")

        # The still's frame: the plate's highlight must be clear of every text box.
        rects = layout.get("rects") or {}
        still_frame = int(layout.get("stillFrame") or 0)
        if rects and anchor.is_file():
            import numpy as np

            plate = tinted_anchor(anchor, size, colour, str(built.get("finish") or ""),
                                  float(built.get("cropY", 0.5)), still_frame,
                                  own=float(built.get("keep") or 0.0), saturation=float(built.get("saturation") or 1.0),
                                  wash=bool(built.get("wash")))[0]
            if plate is None:
                fail(f"{canvas}: the still's frame {still_frame} did not decode")
            else:
                luma = np.asarray(Image.fromarray(plate).convert("L")).astype(float)
                dark = bool(built.get("darkType"))
                worst, where = (255.0 if dark else 0.0), ""
                for slot, box in rects.items():
                    u, v, w, h = box
                    patch = luma[int(v * height):int((v + h) * height), int(u * width):int((u + w) * width)]
                    if not patch.size:
                        continue
                    value = float(patch.mean())
                    if (value < worst) if dark else (value > worst):
                        worst, where = value, slot
                if dark and worst < TEXT_BOX_DARK:
                    fail(f"{canvas}: the still's frame {still_frame} puts a dark patch behind the {where} "
                         f"(luma {worst:.0f} under a {TEXT_BOX_DARK} floor); pick a frame where the dark words sit on the light")
                elif dark:
                    ok(f"{canvas}: still taken at frame {still_frame}, every text box on the light "
                       f"(darkest {worst:.0f} over a {TEXT_BOX_DARK} floor)")
                elif worst > TEXT_BOX_LUMA:
                    fail(f"{canvas}: the still's frame {still_frame} puts a bright patch behind the {where} "
                         f"(luma {worst:.0f} of a {TEXT_BOX_LUMA} ceiling); pick a frame where the highlight is clear")
                else:
                    ok(f"{canvas}: still taken at frame {still_frame}, every text box clear of the highlight "
                       f"(worst {worst:.0f} of a {TEXT_BOX_LUMA} ceiling)")

        # The colour is read on the poster's own background, where nothing covers it.
        background = folder / files.get("background", "")
        subject = np.asarray(Image.open(background).convert("RGB")) if background.is_file() else still
        if anchor.is_file():
            expected_frame, window = tinted_anchor(anchor, size, colour, str(built.get("finish") or ""),
                                                   float(built.get("cropY", 0.5)), still_frame,
                                  own=float(built.get("keep") or 0.0), saturation=float(built.get("saturation") or 1.0),
                                  wash=bool(built.get("wash")))
            if expected_frame is None:
                fail(f"{canvas}: the anchor {anchor.name} did not decode at {size[0]}x{size[1]}")
            else:
                worst = 0
                for u, v in ((0.06, 0.28), (0.78, 0.14), (0.62, 0.58), (0.12, 0.88)):
                    expected = tile_of(expected_frame, u, v)
                    got = tile_of(subject, u, v)
                    worst = max(worst, max(abs(got[channel] - expected[channel]) for channel in range(3)))
                if worst <= 4:
                    ok(f"{canvas}: colour {colour} exact, the anchor's own tones with it (worst drift {worst} of 255)")
                else:
                    fail(f"{canvas}: the picture drifts {worst} of 255 from the same chain over the anchor; the anchor was not recoloured")

        frames = {} if built.get("still") else decoded_frames(folder / files["loop"], size, [0, 1, 2], step_series=True)
        count = int(frames.get("count") or 0)
        if built.get("still"):
            # A photo look is posted still, the way the brand posts its city photos.
            moving = sorted(path.name for path in folder.glob(f"*-{canvas}-motion.*"))
            if moving:
                fail(f"{canvas}: {', '.join(moving)} sits beside a still poster; a photo look makes no MP4 or GIF")
            else:
                ok(f"{canvas}: a still poster (PNG and PDF); nothing moves the photo")
        elif count < 3 or "series" not in frames:
            fail(f"{canvas}: the loop did not decode")
        else:
            import numpy as np

            first = frames[0].astype(float)
            last = frames["last"].astype(float)
            series = frames["series"]
            seam = float(np.abs(first - last).mean())
            step = float(np.median(series))
            motion = float(np.abs(first - frames["middle"].astype(float)).mean())
            # A look may set its own floor: a still photo pushed in moves fewer pixels than a ribbon,
            # and a calm photo (sky, water) fewer still, while a still in a clip stays near 0.
            floor = float(built.get("motionFloor") or MOTION_FLOOR)
            if motion < floor:
                fail(f"{canvas}: the loop barely moves ({motion:.2f} mean RGB between the first frame and the middle; "
                     f"the look's floor is {floor:g})")
            allowance = min(max(1.0, SEAM_ALLOWANCE * step), LOOP_JUMP)
            # A pale or slow look steps less than the floor on every frame; its wrap is a held picture
            # only when it moves far less than the loop's own step.
            held = seam < LOOP_DUPLICATE and seam < 0.5 * step
            if seam <= allowance and not held:
                ok(f"{canvas}: loop closed (seam {seam:.2f} against a median step of {step:.2f})")
            elif held:
                fail(f"{canvas}: the loop ends on a copy of its first frame (seam {seam:.2f}); "
                     "it must end one frame before the plate repeats, or the wrap holds the same picture twice")
            else:
                fail(f"{canvas}: the loop jumps at its seam ({seam:.2f} against a median step of {step:.2f})")
            if motion >= floor:
                ok(f"{canvas}: the loop moves ({motion:.2f} mean RGB across half of it)")
            else:
                fail(f"{canvas}: the loop does not move; it is a still in a clip")
            if built["loop"]["frames"] != count:
                fail(f"{canvas}: the loop holds {count} frames, the anchor {built['loop']['frames']}; a recolour keeps every frame")
            else:
                ok(f"{canvas}: {count} frames, the anchor's own")

        # The fair's colour is the folder's own value for that fair.
        calendar_colour = built.get("calendarColour")
        if calendar_colour:
            if built.get("colour", "").lower() != calendar_colour.lower():
                fail(f"{canvas}: the poster is {built.get('colour')} but the folder's calendar says {calendar_colour} for this fair")
            else:
                ok(f"{canvas}: the fair's own colour {calendar_colour}, the folder's value")
        else:
            ok(f"{canvas}: no calendar colour for this fair; the ask's {built.get('colour')} was used")

        # On a dark look the fair's mark is one flat colour, never full colour.
        if data.get("partner") and built.get("look") == "blue-diagonal":
            spread = mark_spread(kit / "marks" / data["partner"])
            if spread is None:
                fail(f"{canvas}: the fair's mark {data['partner']} could not be read")
            elif spread > SINGLE_COLOUR_SPREAD:
                fail(f"{canvas}: the fair's mark {data['partner']} is full colour (channel spread {spread}); a dark look takes the single-colour version")
            else:
                ok(f"{canvas}: the fair's mark is single-colour on the dark look (spread {spread})")

        images = set(layout.get("images") or [])
        # The GIF's own loop point, measured on the file that ships.
        gif_path = folder / files["gif"] if files.get("gif") else None
        if gif_path and gif_path.is_file():
            read = gif_jump(gif_path)
            if read is None:
                fail(f"{canvas}: the GIF's frames could not be read")
            else:
                # A GIF shows fewer frames a second than the film, so each of its steps is bigger: the wrap
                # is a reset only when it is bigger than the GIF's own steps.
                jump, own_step = read
                ceiling = max(LOOP_JUMP, SEAM_ALLOWANCE * own_step)
                if jump > ceiling:
                    fail(f"{canvas}: the GIF jumps {jump:.2f} from its last frame back to its first "
                         f"(its own step is {own_step:.2f}, ceiling {ceiling:.2f})")
                else:
                    ok(f"{canvas}: the GIF closes (jump {jump:.2f}, its own step {own_step:.2f}, ceiling {ceiling:.2f})")
            size = gif_path.stat().st_size
            if size > GIF_BYTES:
                fail(f"{canvas}: the GIF is {size / 1e6:.1f} MB, over the {GIF_BYTES // 1_000_000} MB a GIF can be and still be posted")
            else:
                ok(f"{canvas}: GIF {size / 1e6:.1f} MB, a size people post")

        gif = folder / files["gif"] if files.get("gif") else None
        if gif and gif.is_file():
            with Image.open(gif) as made:
                want = (GIF_WIDTH, round(height * GIF_WIDTH / width))
                if made.size != want:
                    fail(f"{canvas}: the GIF is {made.size[0]}x{made.size[1]}, want {want[0]}x{want[1]}")
                else:
                    ok(f"{canvas}: GIF {want[0]}x{want[1]}, her width at the canvas's own shape")
        if not data.get("partner") and house_partner is False:
            ok(f"{canvas}: no fair mark, as the kit says (a kit started from a logo and a photo)")
        elif not data.get("partner"):
            fail(f"{canvas}: the fair's own mark is missing")
        elif data["partner"] not in images:
            fail(f"{canvas}: the fair mark {data['partner']} is not on the page")
        else:
            ok(f"{canvas}: fair mark {data['partner']} on the page")
        if data.get("wordmark") and data["wordmark"] not in images:
            fail(f"{canvas}: the wordmark {data['wordmark']} is not on the page")
        for name in data.get("marks") or []:
            if name not in images:
                fail(f"{canvas}: the strip mark {name} is not on the page")
        for name in data.get("marks") or []:
            if not (kit / "marks" / name).is_file():
                fail(f"{canvas}: the strip mark {name} is not in the kit")
        if data.get("marks") and all(name in images for name in data["marks"]):
            ok(f"{canvas}: {len(data['marks'])} certification marks on the page")

    for slot in ("headline", "venue", "band"):
        if not str((data.get("slots") or {}).get(slot) or "").strip():
            fail(f"the {slot} slot is empty")
    caption_lines(folder, manifests[0].stem, data, kit, ok, fail)
    if not any(line.startswith("FAIL") for line in lines):
        ok(f"{data.get('fair')} {data.get('year') or ''}: {data.get('look')} in {colour}")
    for line in lines:
        print(line)
    return 2 if any(line.startswith("FAIL") for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
