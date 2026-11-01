#!/usr/bin/env python3
"""Build a deck from a brand kit and a list of slides. The kit owns the look; you write the words.

Usage: pptx_from_kit.py kit.json slides.json out.pptx

kit.json (only "fonts" and "palette" are required):
{
  "brand": "Northwind Studio",
  "slide_ratio": "16:9",
  "fonts": {"heading": "Liberation Sans", "body": "Liberation Serif"},
  "palette": ["#0B1F3A", "#F2B705", "#FFFFFF", "#5A6B7B"],
  "colours": {"ink": "#0B1F3A", "accent": "#F2B705", "paper": "#FFFFFF", "muted": "#5A6B7B"},
  "limits": {"max_words_per_slide": 40, "max_body_paragraphs": 4, "min_font_pt": 18},
  "footer": "Northwind Studio · Confidential",
  "logo": "logo.png",
  "style": {"bold_titles": false, "title_rule": false}
}
Without "colours" the roles are read off the palette: the darkest is ink, the lightest is paper,
the most saturated of the rest is the accent and what remains is muted.

slides.json:
{
  "properties": {"title": "Deck title", "language": "en-GB"},
  "slides": [
    {"role": "title", "title": "A new visitor route", "subtitle": "Opening May 2027"},
    {"role": "content", "title": "The problem", "bullets": ["One short line", "Another"]},
    {"role": "chart", "title": "Visitors", "bullets": ["Optional short note"],
     "chart": {"type": "bar", "categories": ["2023", "2025"], "series": {"Visitors": [82000, 64000]},
               "alt": "Bar chart: visitors fell from 82,000 to 64,000"}},
    {"role": "picture", "title": "The new screen", "bullets": ["One short line"],
     "picture": {"path": "screen.png", "alt": "The new booking screen with a filled form"}}
  ]
}
A picture or a chart takes the right part of the slide and the text keeps the left, so neither
covers the other. A picture keeps its own proportions and needs "alt". Place pictures only this
way; a picture added by hand afterwards is not kept clear of the text.

Every text run gets a kit font, a palette colour and a set size. Body text is the ink colour and
one size on every slide: the largest that fits the fullest slide, never below the kit minimum.
Short slides are centred in their text area. Nothing decorative is drawn: no rule under the title,
no shadow, no shape that carries no information, unless the kit's "style" asks for a title rule.
The kit logo, when given, sits top right on every slide. The footer goes on every slide, charts get
alternative text and palette colours, and the deck gets a title. A slide over the kit's word or
paragraph limit, or text that cannot fit at the minimum size, stops the build with exit 1 and a
JSON list of what to shorten, so the limits are met by rewriting, never by shrinking.
"""
import argparse
import json
import os
import sys

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

CHARTS = {"bar": XL_CHART_TYPE.COLUMN_CLUSTERED, "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(c):
    out = []
    for v in c:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = luminance(rgb(a)), luminance(rgb(b))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def roles(kit):
    if kit.get("colours"):
        return {k: v.upper().lstrip("#") for k, v in kit["colours"].items()}
    pal = [p.upper().lstrip("#") for p in kit["palette"]]
    by_lum = sorted(pal, key=lambda p: luminance(rgb(p)))
    ink, paper = by_lum[0], by_lum[-1]
    rest = [p for p in pal if p not in (ink, paper)] or [ink]
    sat = lambda p: max(rgb(p)) - min(rgb(p))
    accent = max(rest, key=sat)
    muted = next((p for p in rest if p != accent), ink)
    return {"ink": ink, "paper": paper, "accent": accent, "muted": muted}


def readable(colour, paper, fallback, large):
    """A text colour must reach 4.5:1 on the paper (3:1 for large text); otherwise fall back to the ink."""
    return colour if contrast(colour, paper) >= (3.0 if large else 4.5) else fallback


def lines_needed(text, size_pt, width_pt):
    count, width = 1, 0.0
    for ch in text:
        cw = size_pt * 0.55
        if width + cw > width_pt and width > 0:
            count, width = count + 1, cw
        else:
            width += cw
    return count


def fit_size(paragraphs, width_emu, height_emu, largest, smallest):
    """Largest size from largest down to smallest whose estimated height fits the box, or None."""
    w = width_emu / 12700.0 - 14.4
    h = height_emu / 12700.0 - 7.2
    size = largest
    while size >= smallest:
        need = sum(lines_needed(p, size, w) for p in paragraphs) * size * 1.2
        if need <= h:
            return size
        size -= 2
    return None


def run(paragraph, text, face, size, colour, bold=False):
    r = paragraph.add_run()
    r.text = text
    r.font.name, r.font.size, r.font.bold = face, Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(colour)
    return r


def words(slide_spec):
    parts = [slide_spec.get("title", ""), slide_spec.get("subtitle", "")] + list(slide_spec.get("bullets", []))
    return sum(len(p.split()) for p in parts if p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a deck from a brand kit and a slide list.")
    ap.add_argument("kit"); ap.add_argument("slides"); ap.add_argument("output")
    args = ap.parse_args(argv)
    with open(args.kit, encoding="utf-8") as fh:
        kit = json.load(fh)
    with open(args.slides, encoding="utf-8") as fh:
        spec = json.load(fh)
    limits = kit.get("limits", {})
    max_words, max_paras, min_pt = limits.get("max_words_per_slide", 40), limits.get("max_body_paragraphs", 4), limits.get("min_font_pt", 18)
    col = roles(kit)
    heading, body = kit["fonts"]["heading"], kit["fonts"].get("body", kit["fonts"]["heading"])
    footer = kit.get("footer")
    problems = []
    for i, s in enumerate(spec.get("slides", []), 1):
        if words(s) > max_words:
            problems.append({"slide": i, "problem": "has %d words, the kit allows %d" % (words(s), max_words)})
        if len(s.get("bullets", [])) + (1 if s.get("subtitle") else 0) > max_paras:
            problems.append({"slide": i, "problem": "has %d body paragraphs, the kit allows %d" % (len(s.get("bullets", [])), max_paras)})
        if not s.get("title"):
            problems.append({"slide": i, "problem": "has no title"})
        if s.get("chart") and not (s["chart"].get("alt") or s["chart"].get("title")):
            problems.append({"slide": i, "problem": "its chart has no alt text"})

    template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "standard-16x9.pptx")
    prs = Presentation(template) if kit.get("slide_ratio", "16:9") == "16:9" and os.path.exists(template) else Presentation()
    if kit.get("slide_ratio", "16:9") == "16:9":
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    W, H = prs.slide_width, prs.slide_height
    margin = Inches(0.7)
    ink = col["ink"]
    text_colour = ink  # body text is the ink colour; muted is for the footer only
    foot_colour = readable(col.get("muted", ink), col["paper"], ink, large=False)
    title_only = prs.slide_layouts[5]
    style = kit.get("style") or {}
    bold_titles = style.get("bold_titles", False)  # one normal weight unless the kit asks for bold
    logo = kit.get("logo")
    if logo and not os.path.isabs(logo):
        logo = os.path.join(os.path.dirname(os.path.abspath(args.kit)), logo)

    def geometry(s):
        role = s.get("role", "content")
        t_top, t_h = (Inches(2.3), Inches(1.6)) if role == "title" else (Inches(0.45), Inches(1.0))
        body_top = t_top + t_h + Inches(0.35)
        body_h = H - body_top - Inches(0.95)
        side = s.get("chart") or s.get("picture")
        body_w = (W - 2 * margin) if not side else int((W - 2 * margin) * 0.42)
        return t_top, t_h, body_top, body_h, body_w

    # One body size for the whole deck: the largest that fits the fullest slide.
    deck_size = 28
    for i, s in enumerate(spec.get("slides", []), 1):
        paras = ([s["subtitle"]] if s.get("subtitle") else []) + list(s.get("bullets", []))
        if not paras:
            continue
        _, _, _, body_h, body_w = geometry(s)
        size = fit_size(paras, body_w, body_h, 28, min_pt)
        if size is None:
            problems.append({"slide": i, "problem": "the text does not fit at %s pt; shorten it" % min_pt})
            size = min_pt
        deck_size = min(deck_size, size)

    for i, s in enumerate(spec.get("slides", []), 1):
        slide = prs.slides.add_slide(title_only)
        bg = slide.background.fill
        bg.solid(); bg.fore_color.rgb = RGBColor.from_string(col["paper"])
        role = s.get("role", "content")
        t = slide.shapes.title
        t.left, t.width = margin, W - 2 * margin
        t.top, t.height, body_top, body_h, body_w = geometry(s)
        t.text_frame.word_wrap = True
        t.text_frame.text = ""
        size = fit_size([s.get("title", "")], t.width, t.height, 44 if role == "title" else 34, max(min_pt, 24))
        if size is None:
            problems.append({"slide": i, "problem": "the title does not fit; shorten it"})
            size = max(min_pt, 24)
        # One left edge for title, bar, body and footer; the layout's centred title would break it.
        t.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        t.text_frame.vertical_anchor = MSO_ANCHOR.BOTTOM
        t.text_frame.margin_left = 0
        run(t.text_frame.paragraphs[0], s.get("title", ""), heading, size, ink, bold=bold_titles)
        # No decoration by default: a rule under the title carries no information. A company kit may ask
        # for one with "style": {"title_rule": true}.
        if style.get("title_rule"):
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, margin, t.top + t.height + Inches(0.05), Inches(1.4), Inches(0.07))
            bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor.from_string(col["accent"]); bar.line.fill.background()
            bar._element.nvSpPr.cNvPr.set("descr", "Decorative accent bar")
            bar.shadow.inherit = False  # no theme shadow
        paras = ([s["subtitle"]] if s.get("subtitle") else []) + list(s.get("bullets", []))
        chart = s.get("chart")
        picture = s.get("picture")
        if paras:
            box = slide.shapes.add_textbox(margin, body_top, body_w, body_h)
            box.text_frame.word_wrap = True
            box.text_frame.margin_left = 0
            size = deck_size
            # A short slide is centred in its text area instead of leaving the lower half empty.
            box.text_frame.vertical_anchor = MSO_ANCHOR.TOP if role == "title" else MSO_ANCHOR.MIDDLE
            for k, line in enumerate(paras):
                p = box.text_frame.paragraphs[0] if k == 0 else box.text_frame.add_paragraph()
                p.space_after = Pt(size * 0.4)
                run(p, line, body, size, text_colour)
        if chart:
            data = CategoryChartData()
            data.categories = chart["categories"]
            for name, values in chart["series"].items():
                data.add_series(name, values)
            left = margin + (body_w + Inches(0.3) if paras else 0)
            frame = slide.shapes.add_chart(CHARTS.get(chart.get("type", "bar"), XL_CHART_TYPE.COLUMN_CLUSTERED),
                                           left, body_top, W - margin - left, body_h, data)
            frame._element.nvGraphicFramePr.cNvPr.set("descr", chart.get("alt") or chart.get("title"))
            ch = frame.chart
            ch.font.name, ch.font.size = body, Pt(max(12, min_pt - 4))
            ch.font.color.rgb = RGBColor.from_string(ink)
            ch.has_title = False  # the slide title names the chart; a second title only repeats the series name
            ch.has_legend = len(chart["series"]) > 1
            if ch.has_legend:
                ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.BOTTOM, False
            series_colours = [col["accent"], ink, col.get("muted", ink)]
            if chart.get("type", "bar") != "pie":
                for k, ser in enumerate(ch.plots[0].series):
                    ser.format.fill.solid()
                    ser.format.fill.fore_color.rgb = RGBColor.from_string(series_colours[k % len(series_colours)])
                ch.plots[0].has_data_labels = True
                values = [v for vs in chart["series"].values() for v in vs if isinstance(v, (int, float))]
                places = max([len(repr(float(v)).split(".")[1].rstrip("0")) for v in values] + [0])
                fmt = "#,##0" if places == 0 else "#,##0." + "0" * min(places, 3)
                ch.plots[0].data_labels.number_format = fmt
                ch.plots[0].data_labels.number_format_is_linked = False
                ch.value_axis.tick_labels.number_format = fmt
                ch.value_axis.tick_labels.number_format_is_linked = False
                ch.value_axis.has_major_gridlines = False
                if chart.get("type", "bar") == "bar" and values and min(values) >= 0:
                    ch.value_axis.minimum_scale = 0  # a bar's length is its value; a cut axis overstates the gap
        if picture:
            from PIL import Image
            path = picture["path"] if os.path.isabs(picture["path"]) else os.path.join(os.path.dirname(os.path.abspath(args.slides)), picture["path"])
            if not os.path.exists(path):
                problems.append({"slide": i, "problem": "picture %s was not found" % picture["path"]})
            elif not picture.get("alt"):
                problems.append({"slide": i, "problem": "its picture has no alt text"})
            else:
                left = margin + (body_w + Inches(0.3) if paras else 0)
                box_w, box_h = W - margin - left, body_h
                pw, ph = Image.open(path).size
                k = min(box_w / pw, box_h / ph)  # fit inside the reserved area, proportions kept
                w, h = int(pw * k), int(ph * k)
                pic = slide.shapes.add_picture(path, left + (box_w - w) // 2, body_top + (box_h - h) // 2, w, h)
                pic._element.nvPicPr.cNvPr.set("descr", picture["alt"])
        if logo and os.path.exists(logo):
            from PIL import Image
            lw, lh = Image.open(logo).size
            h = Inches(0.45)
            w = int(lw * h / lh)
            lg = slide.shapes.add_picture(logo, W - margin - w, Inches(0.35), w, h)
            lg._element.nvPicPr.cNvPr.set("descr", (kit.get("brand") or "Brand") + " logo")
        if footer:
            fb = slide.shapes.add_textbox(margin, H - Inches(0.6), W - 2 * margin, Inches(0.35))
            fb.text_frame.margin_left = 0
            fb.text_frame.word_wrap = True
            fb.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
            run(fb.text_frame.paragraphs[0], footer, heading, 12, foot_colour)

    if problems:
        print(json.dumps({"ok": False, "shorten": problems}, ensure_ascii=False))
        return 1
    props = spec.get("properties") or {}
    title = props.get("title") or next((s.get("title") for s in spec.get("slides", []) if s.get("title")), None)
    if title:
        prs.core_properties.title = title
    if props.get("language"):
        prs.core_properties.language = props["language"]
    prs.save(args.output)
    print(json.dumps({"ok": True, "output": args.output, "slides": len(spec.get("slides", [])), "colours": col}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
