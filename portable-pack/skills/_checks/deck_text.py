"""How wide a line of text sets, so a deck's builder and its check agree on what fits a box.

The widths are the advance widths of Helvetica (1/1000 em), which Arial and Liberation Sans share
glyph for glyph, so one table serves the faces a system-safe deck is set in. A look with another
face names its own factor (`advance`), and letter spacing is added per character as PowerPoint adds it.

    measure(text, size)            width of one line in points
    wrap(text, size, width)        the lines the text takes in a box that wide
    height(paragraphs, width)      the height a list of (text, size, pitch, after, indent) needs
"""

_CHARS = (
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    "åäöÅÄÖéèüÜøØæÆß–—·…’‘“”•€£×°§«»"
)
_W = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
      556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278,
      500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469,
      556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500,
      278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 556, 556, 556, 667, 667, 778, 556, 556, 556, 722,
      556, 778, 889, 1000, 611, 556, 1000, 278, 1000, 222, 222, 333, 333, 350, 556, 556, 584, 400, 556, 556, 556]
WIDTHS = dict(zip(_CHARS, _W))
# Faces that set wider or narrower than Helvetica's table. Anything unlisted is measured a little
# wide, so a fit that passes here passes on the page.
ADVANCE = {"arial": 1.0, "helvetica": 1.0, "liberation sans": 1.0, "arimo": 1.0, "helvetica neue": 1.05}
UNKNOWN_ADVANCE = 1.04


def advance_of(face):
    return ADVANCE.get(str(face or "").strip().lower(), UNKNOWN_ADVANCE)


def measure(text, size, advance=1.0, spacing=0.0):
    """Width in points of one line at `size` points; `spacing` is letter spacing in points a character."""
    text = str(text)
    return sum(WIDTHS.get(ch, 556) for ch in text) / 1000.0 * size * advance + spacing * len(text)


def wrap(text, size, width, advance=1.0, spacing=0.0):
    """Greedy word wrap as PowerPoint and LibreOffice do it. A line break (\\n or \\v) starts a new line."""
    lines = []
    for para in str(text).replace("\v", "\n").split("\n"):
        line = ""
        for word in para.split(" "):
            trial = (line + " " + word) if line else word
            if line and measure(trial, size, advance, spacing) > width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def height(paragraphs, width, advance=1.0):
    """Height in points of paragraphs given as (text, size, pitch, after, indent, spacing)."""
    total, last_after = 0.0, 0.0
    for text, size, pitch, after, indent, spacing in paragraphs:
        total += len(wrap(text, size, max(1.0, width - indent), advance, spacing)) * pitch + after
        last_after = after
    return total - last_after if paragraphs else 0.0


def widest_word(text, size, advance=1.0, spacing=0.0):
    words = str(text).replace("\v", " ").replace("\n", " ").split()
    return max([measure(w, size, advance, spacing) for w in words] or [0.0])
