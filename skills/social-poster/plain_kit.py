#!/usr/bin/env python3
"""Start a poster kit from a logo and a photo, for a folder that has no kit of its own.

    python3 plain_kit.py --logo "<their logo>" --photo "<their photo>" [--claim "<their line>"] [--kit DIR]

The kit is the brand photo look the skill already draws (the photo toned into one colour, the logo and the
words over it), written to `<the photo's folder>/poster-kit` unless --kit names another place. The logo and
the photo are copied in, never changed; the person's own files stay where they are. The fair's colour is
taken from the photo itself and kept in poster.json, so an ask without a colour still has one. Nothing is
drawn or fetched: no mark, photo or claim the person did not give goes in.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import sys
from pathlib import Path

#: The photo look's page, the same tokens as a brand's own city-photo look: white words over the photo,
#: dark scrims behind them, part of the photo's own colour kept under the fair's, no claim line by default.
LOOK = {
    "name": "photo", "family": "Photo", "anchor": None, "spare": None,
    "ground": "#ffffff", "groundDark": "rgba(0,0,0,0)", "ink": "#ffffff",
    "soft": "rgba(255,255,255,0.85)", "line": "rgba(255,255,255,0.55)", "on": "#ffffff", "mark": "none",
    "scrimHeadDark": "rgba(0,0,0,0.42)", "scrimFootDark": "rgba(0,0,0,0.62)",
    "scrimHeadLight": "rgba(244,237,224,0.86)", "scrimFootLight": "rgba(244,237,224,0.86)",
    "clear": "rgba(0,0,0,0)", "photo": True, "keep": 0.6, "saturation": 0.4,
    "finish": "eq=brightness=-0.06:contrast=0.70:saturation=0.8",
    "wordmark": 0.053, "partner": 0.1, "padTop": 0.06, "padBottom": 0.07, "small": 0.023,
    "venueWidth": "92%", "cue": "VISIT US",
    "when": "a kit started from the person's logo and one photo",
}
IMAGES = {".png", ".svg", ".jpg", ".jpeg", ".webp"}
PHOTOS = {".jpg", ".jpeg", ".png", ".webp"}


class Stop(Exception):
    pass


def picture(path: str, kinds: set, what: str) -> Path:
    found = Path(path).expanduser().resolve()
    if not found.is_file():
        raise Stop(f"the {what} {found} is not there")
    if found.suffix.lower() not in kinds:
        raise Stop(f"the {what} must be one of {', '.join(sorted(kinds))}, not {found.name}")
    return found


def photo_colour(photo: Path) -> str:
    """The photo's own colour, deepened so white words read on it: its mean hue at a poster's depth."""
    try:
        from PIL import Image
    except ImportError:
        return "#44688B"  # no reader: a deep blue-grey, the colour the city-photo posts use most
    with Image.open(photo) as image:
        red, green, blue = image.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    hue, _, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    red, green, blue = colorsys.hls_to_rgb(hue, 0.36, min(max(saturation, 0.18), 0.45))
    return "#%02X%02X%02X" % (round(red * 255), round(green * 255), round(blue * 255))


def dark_logo(logo: Path) -> bool:
    """A logo drawn in dark ink, which would vanish on the darkened photo."""
    if logo.suffix.lower() == ".svg":
        return False
    try:
        from PIL import Image
    except ImportError:
        return False
    with Image.open(logo) as image:
        rgba = image.convert("RGBA")
        rgba.thumbnail((200, 200))
        seen = [(r, g, b) for r, g, b, a in (rgba.get_flattened_data() if hasattr(rgba, "get_flattened_data") else rgba.getdata()) if a > 128]
    if not seen or len(seen) > 0.97 * rgba.width * rgba.height:
        return False  # no see-through ground: a logo on its own tile reads as it is
    light = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in seen) / len(seen) / 255
    return light < 0.45


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start a poster kit from a logo and a photo.")
    parser.add_argument("--logo", required=True, help="the person's logo file")
    parser.add_argument("--photo", required=True, help="their photo: the stand, the product or the city")
    parser.add_argument("--claim", default="", help="their own line, only when they gave one")
    parser.add_argument("--kit", help="where the kit goes (default: poster-kit beside the photo)")
    args = parser.parse_args(argv)

    logo = picture(args.logo, IMAGES, "logo")
    photo = picture(args.photo, PHOTOS, "photo")
    kit = Path(args.kit).expanduser().resolve() if args.kit else photo.parent / "poster-kit"
    if (kit / "poster.json").is_file() and not json.loads((kit / "poster.json").read_text()).get("plain"):
        raise Stop(f"{kit} is already a brand's own kit; use it as it is")
    if len(args.claim) > 64:
        raise Stop(f"the claim is {len(args.claim)} characters; the slot holds 64")
    (kit / "marks").mkdir(parents=True, exist_ok=True)
    (kit / "photos").mkdir(exist_ok=True)
    shutil.copy2(logo, kit / "marks" / logo.name)
    shutil.copy2(photo, kit / "photos" / photo.name)
    (kit / "marks" / "manifest.json").write_text(json.dumps({"assets": [{
        "file": logo.name, "name": "logo", "kind": "image", "tags": ["logo"],
        "description": f"The person's own logo, copied from {logo}."}]}, indent=1) + "\n")
    (kit / "photos" / "credits.json").write_text(json.dumps([{
        "file": f"photos/{photo.name}", "by": "the person's own photo", "page": str(photo), "licence": "their own"}],
        indent=1) + "\n")
    look = dict(LOOK)
    if dark_logo(logo):
        look["markFilter"] = "brightness(0) invert(1)"
    colour = photo_colour(photo)
    (kit / "looks.json").write_text(json.dumps({"looks": [look]}, indent=1) + "\n")
    (kit / "fairs.json").write_text(json.dumps({"fairs": {}}, indent=1) + "\n")
    (kit / "poster.json").write_text(json.dumps({
        "note": "A kit started from the person's logo and one photo (plain_kit.py). Their own files, copied in.",
        "plain": True, "wordmark": logo.name, "claim": args.claim, "partner": False,
        "colour": colour, "photo": f"photos/{photo.name}",
        "looks": "looks.json", "fairs": "fairs.json"}, indent=2) + "\n")
    print(json.dumps({"kit": str(kit), "colour": colour, "logo": logo.name, "photo": f"photos/{photo.name}",
                      "logo_turned_white": "markFilter" in look}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as stop:
        print(f"STOP {stop}", file=sys.stderr)
        sys.exit(2)
