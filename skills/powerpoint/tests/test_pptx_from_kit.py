"""pptx_from_kit.py: the kit owns the look, each slide keeps its own words, nothing decorative is drawn."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "pptx_from_kit.py"
KIT = {"brand": "Example", "fonts": {"heading": "Arial", "body": "Georgia"},
       "palette": ["#0B1F3A", "#F2B705", "#FFFFFF", "#5A6B7B"],
       "limits": {"max_words_per_slide": 40, "max_body_paragraphs": 4, "min_font_pt": 18}, "footer": "Example footer"}
SLIDES = {"slides": [
    {"role": "title", "title": "First title", "subtitle": "First subtitle"},
    {"role": "content", "title": "Second title", "bullets": ["Second one", "Second two"]},
    {"role": "chart", "title": "Third title", "bullets": ["Third note"],
     "chart": {"type": "bar", "categories": ["A", "B"], "series": {"Score": [0.83, 0.934]}, "alt": "Score rose from 0.83 to 0.934"}}]}


def build(tmp_path, kit=KIT, slides=SLIDES):
    (tmp_path / "kit.json").write_text(json.dumps(kit))
    (tmp_path / "slides.json").write_text(json.dumps(slides))
    out = tmp_path / "deck.pptx"
    p = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "kit.json"), str(tmp_path / "slides.json"), str(out)],
                       capture_output=True, text=True)
    return p, out


def auto_shapes(path):
    return [sh for s in Presentation(path).slides for sh in s.shapes if sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]


def test_each_slide_keeps_its_own_text(tmp_path):
    p, out = build(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    for slide, want in zip(Presentation(out).slides, SLIDES["slides"]):
        text = " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
        for piece in [want["title"], want.get("subtitle")] + want.get("bullets", []):
            if piece:
                assert piece in text


def test_no_decorative_shapes_by_default(tmp_path):
    p, out = build(tmp_path)
    assert p.returncode == 0
    assert auto_shapes(out) == []
    titles = [s.shapes.title.text_frame.paragraphs[0].runs[0] for s in Presentation(out).slides]
    assert all(not r.font.bold for r in titles)


def test_title_rule_only_when_the_kit_asks(tmp_path):
    p, out = build(tmp_path, kit=dict(KIT, style={"title_rule": True}))
    assert p.returncode == 0
    assert len(auto_shapes(out)) == len(SLIDES["slides"])


def test_chart_keeps_decimals_and_alt_text(tmp_path):
    p, out = build(tmp_path)
    frame = next(sh for sh in Presentation(out).slides[2].shapes if sh.has_chart)
    assert frame.chart.plots[0].data_labels.number_format == "#,##0.000"
    assert frame._element.nvGraphicFramePr.cNvPr.get("descr")


def test_over_limit_slide_stops_the_build(tmp_path):
    long = {"slides": [{"role": "content", "title": "Too long", "bullets": [" ".join(["word"] * 30), " ".join(["word"] * 30)]}]}
    p, out = build(tmp_path, slides=long)
    assert p.returncode == 1
    assert json.loads(p.stdout)["ok"] is False
    assert not out.exists()
