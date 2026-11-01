#!/usr/bin/env python3
"""The look of a trade page: an invoice, a credit note, a quotation, an order, a delivery note, a pro forma.

    Where      The letter sheet of letter.py beside this file, on the layout of the country the page is sent
               from. Nothing here moves the address window, the information block or a margin: those are the
               layout's own and the pack checks measure them. This file sets type, spacing and rules, and
               puts the closing block at the foot of a page that has room.
    Tokens     The library's look file, skills/business-deck/look.json: the inks, the face and the letter
               spacing the deck has, the long-form type scale in its "text" block and what only these pages
               need in its "trade" block. A company that replaces that one file restyles its deck, its
               reports and its trade pages together. A pack that travels without the deck prints the open
               default, kept in step with the file by a test.
    Hierarchy  By size and space, in one ink and one weight: the document's name and number (text.h1), the
               sender's name (text.h2), the total (text.lead), rows, notes and the closing block (trade.body), and one
               size of small print for the information block, the column heads, the company details at the
               foot and the running line (trade.small). Nothing is bold unless the look file asks
               (face.title_weight).
    Grid       The footer's columns, the totals and the payment block's values stand on one grid of twelve
               columns between the layout's margins (grid.columns, trade.gutter).

Standard library only.
"""
import json
import re
from pathlib import Path

import letter

HERE = Path(__file__).resolve().parent
LOOK_FILE = HERE.parent / "business-deck" / "look.json"

# The open default, for a pack that travels without the look file. skills/trade-documents/tests holds these
# numbers to the file's.
DEFAULT = {
    "name": "Open default",
    "face": {"name": "Arial", "weight": 400, "title_weight": 400},
    "ink": {"ground": "FFFFFF", "ink": "1A1C1F", "second": "6A6B6D", "hairline": "E3E3E4", "rule": "1A1C1F"},
    "tracking": {"em": -0.02, "from_pt": 14},
    "grid": {"columns": 12},
    "text": {"body": [11, 16], "small": [9, 12], "lead": [14, 20], "h1": [22, 27], "h2": [16, 21], "h3": [12, 16],
             "para_gap": 8, "heading_gap": [24, 8]},
    "trade": {"body": [10, 15], "small": [8.5, 12], "row_air": 6, "rule": 0.75, "hairline": 0.5, "title_gap": 20,
              "gutter": 5, "footer_columns": [3, 4, 5], "totals_columns": 6, "key_columns": 3, "foot_gap": 6,
              "tight": 0.6},
}
PAGE_BLOCKS = ("face", "ink", "tracking", "grid", "text", "trade")
TOTAL = "lead"      # the step of the text scale the total takes


def load(path=None):
    """The look: the file's blocks over the open default, so a look file that leaves a key out still prints."""
    try:
        data = json.loads(Path(path or LOOK_FILE).read_text())
    except (OSError, ValueError):
        data = {}
    look = {"name": data.get("name") or DEFAULT["name"]}
    for block in PAGE_BLOCKS:
        given = data.get(block) if isinstance(data.get(block), dict) else {}
        look[block] = dict(DEFAULT[block], **{k: v for k, v in given.items() if k != "about"})
    return look


def _n(value):
    """A number as CSS writes it: 10, 8.5, -0.02."""
    return ("%.3f" % float(value)).rstrip("0").rstrip(".")


def _type(look, entry, tracked=True):
    """font-size and line-height for a [size, line pitch] entry; large type takes the look's letter spacing."""
    size, pitch = entry
    out = "font-size:%spt;line-height:%spt" % (_n(size), _n(pitch))
    track = look["tracking"]
    if tracked and track.get("em") and size >= track.get("from_pt", 14):
        out += ";letter-spacing:%sem" % _n(track["em"])
    return out


def _span(count, columns, gutter):
    """The width of `count` of the grid's columns, as a share of the text's width less its part of the gutters."""
    return "calc(%s%% - %smm)" % (_n(100.0 * count / columns), _n(gutter * (columns - count) / columns))


def text_width(layout=None, paper="A4"):
    """mm between the margins: the layout's own, or DIN 5008 Form B's 25 and 20."""
    g = letter.GEOMETRY
    left, right = (layout["left"], layout["right"]) if layout else (g["left"], g["right"])
    return left, round(letter.PAPER_MM[paper][0] - left - right, 2)


def css(look=None, layout=None, paper="A4"):
    """The page's type, spacing and rules, to stand after the sheet's and the layout's own CSS."""
    look = look or load()
    ink, face, text, trade = look["ink"], look["face"], look["text"], look["trade"]
    c = {k: "#" + str(v).lstrip("#") for k, v in ink.items()}
    cols, gut = int(look["grid"].get("columns") or 12), trade["gutter"]
    left, width = text_width(layout, paper)
    weight, title_weight = face.get("weight", 400), face.get("title_weight", face.get("weight", 400))
    body, small = _type(look, trade["body"]), _type(look, trade["small"])
    air, rule, hair = _n(trade["row_air"]), _n(trade["rule"]), _n(trade["hairline"])
    foot = " ".join(_span(k, cols, gut) for k in trade["footer_columns"])
    tight = float(trade.get("tight") or 1)
    v = {
        "name": look["name"], "face": str(face["name"]).replace('"', ""), "weight": weight, "tw": title_weight,
        "ink": c["ink"], "second": c["second"], "hair": c["hairline"], "rule": c["rule"],
        "body": body, "small": small, "h1": _type(look, text["h1"]), "h2": _type(look, text["h2"]),
        "total": _type(look, text[TOTAL]),
        "air": air, "head_air": _n(trade["row_air"] - 1), "rw": rule, "hw": hair,
        "col_gap": _n(trade["row_air"] * 2), "snug_gap": _n(trade["row_air"] * 4 / 3.0),
        "dense_gap": _n(trade["row_air"] * 2 / 3.0),
        "title_gap": _n(trade["title_gap"]), "gap": _n(text["heading_gap"][0]), "para": _n(text["para_gap"]),
        "half": _n(text["heading_gap"][0] / 2.0), "gut": _n(gut), "foot_cols": foot,
        "totals": _span(trade["totals_columns"], cols, gut), "key": _span(trade["key_columns"], cols, gut),
        "left": _n(left), "width": _n(width),
        "t_air": _n(trade["row_air"] * tight), "t_title": _n(trade["title_gap"] * tight),
        "t_gap": _n(text["heading_gap"][0] * tight), "t_para": _n(text["para_gap"] * tight),
        "t_half": _n(text["heading_gap"][0] / 2.0 * tight),
    }
    return """
/* look: %(name)s (skills/_shared/page_look.py) */
body{font-family:"%(face)s","Liberation Sans",Arial,Helvetica,sans-serif;color:%(ink)s;%(body)s;font-weight:%(weight)s}
b,strong{font-weight:%(weight)s}
.mark{border-top-color:%(second)s}
.head .name{%(h2)s;font-weight:%(tw)s}
.return{color:%(second)s}
.return span{border-bottom:%(hw)spt solid %(second)s}
.info{%(small)s}
.info div{font-size:inherit;line-height:inherit}
.info dt{color:%(second)s}
h1{%(h1)s;font-weight:%(tw)s;margin:0 0 %(title_gap)spt}
.k{color:%(second)s}
.extra{%(body)s;margin:0 0 %(half)spt}
.lines{border-collapse:separate;border-spacing:0}
.lines th{%(small)s;color:%(second)s;font-weight:%(weight)s;border-bottom:%(rw)spt solid %(rule)s;padding:0 0 %(head_air)spt}
.lines td{%(body)s;border-bottom:%(hw)spt solid %(hair)s;padding:%(air)spt 0}
.lines th+th,.lines td+td{padding-left:%(col_gap)spt}
.lines th,.lines td{width:1px}
.lines .d{width:auto}
.lines.tight th,.lines.tight td{white-space:nowrap}
.lines.tight .d{white-space:normal}
.lines.snug th+th,.lines.snug td+td{padding-left:%(snug_gap)spt}
.lines.dense td{%(small)s}
.lines.denser th+th,.lines.denser td+td{padding-left:%(dense_gap)spt}
.sum{margin-top:%(para)spt;margin-left:auto;width:auto;min-width:%(totals)s}
.sum td{border:none;padding:1.5pt 0;%(body)s}
.sum td:first-child{color:%(second)s;padding-right:%(col_gap)spt}
.sum tr:nth-last-child(2) td{padding-bottom:%(air)spt}
.sum .gross td{border-top:%(rw)spt solid %(rule)s;padding-top:%(air)spt;padding-bottom:0;%(total)s;font-weight:%(tw)s;color:%(ink)s;white-space:nowrap}
.note,.legal{margin-top:%(gap)spt;%(body)s;color:%(ink)s}
.note+.note,.note+.legal,.legal+.note{margin-top:%(para)spt}
.close{margin-top:%(gap)spt;break-inside:avoid}
.pay{display:grid;grid-template-columns:minmax(%(key)s,max-content) minmax(0,1fr);column-gap:%(gut)smm;border-top:%(hw)spt solid %(hair)s;padding-top:%(air)spt;%(body)s}
.pay .k{white-space:nowrap}
.pay .v{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.sign{margin-top:%(gap)spt;%(body)s}
.pay+.sign{margin-top:%(gap)spt}
footer{width:%(width)smm;border-top:%(hw)spt solid %(hair)s;padding-top:%(air)spt;grid-template-columns:%(foot_cols)s;gap:0 %(gut)smm;%(small)s;color:%(second)s}
.compact h1{margin-bottom:%(t_title)spt}
.compact .extra{margin-bottom:%(t_half)spt}
.compact .lines td{padding-top:%(t_air)spt;padding-bottom:%(t_air)spt}
.compact .sum{margin-top:%(t_para)spt}
.compact .sum tr:nth-last-child(2) td{padding-bottom:%(t_air)spt}
.compact .sum .gross td{padding-top:%(t_air)spt}
.compact .note,.compact .legal,.compact .close,.compact .sign{margin-top:%(t_gap)spt}
.compact .note+.note,.compact .note+.legal,.compact .legal+.note{margin-top:%(t_para)spt}
.compact .pay{padding-top:%(t_air)spt}
.run{position:absolute;left:%(left)smm;width:%(width)smm;display:flex;justify-content:space-between;%(small)s;color:%(second)s}
""" % v


# What the page works out once it is laid out, in this order:
#   1. The room kept clear above the foot of every page follows the footer's real height, never less than the
#      sheet's own (letter.PAGE_FOOT), so a footer of seven lines is cleared as a footer of three is.
#   2. The description takes the table's spare width and every other column is as wide as what it holds. A
#      table whose columns all fit on one line each keeps them so (tight), as long as the description keeps
#      its share of the table (DESCRIPTION_SHARE); in one that does not, the columns stand closer and a cell
#      may wrap as the sheet lets it (snug); a table that still runs wide is set in small print (dense),
#      and one wider still stands its columns closer (denser).
#   3. A document that misses one page by a little gives up part of its air (trade.tight) when that brings it
#      back onto one page; a document that runs to a second page anyway keeps its air.
#   4. The closing block: when the whole document stands on one page it goes down to the foot, above the
#      footer, so a short page has its white in the middle; on a page that runs on it stays after the notes.
SCRIPT = """<script>
(function(){const mm=96/25.4,H=%(page_h)s*mm,q=s=>document.querySelector(s),foot=q('footer'),sec=q('.body'),cell=q('.flow>tbody>tr>td');
const reserve=gap=>{let k=%(page_foot)s*mm;
if(foot){const h=foot.getBoundingClientRect().height+parseFloat(getComputedStyle(foot).bottom)+gap*mm;if(h>k)k=h}
document.querySelectorAll('.flow .foot').forEach(e=>{e.style.height=k+'px'});return k};
let keep=reserve(%(foot_gap)s);
const cs=getComputedStyle(sec),width=sec.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
document.querySelectorAll('table.lines').forEach(t=>{const wide=()=>t.getBoundingClientRect().width>width+0.5,d=t.querySelector('th.d');
t.classList.add('tight');
if(wide()||(d&&d.getBoundingClientRect().width<width*%(share)s)){t.classList.remove('tight');t.classList.add('snug')}
if(wide())t.classList.add('dense');if(wide())t.classList.add('denser')});
const end=()=>cell.getBoundingClientRect().bottom+window.scrollY,fits=()=>end()<=H-keep-mm;
if(!fits()){document.body.classList.add('compact');keep=reserve(%(foot_gap_tight)s);
if(!fits()){document.body.classList.remove('compact');keep=reserve(%(foot_gap)s)}}
const close=q('.close');
if(close&&fits())close.style.marginTop=(parseFloat(getComputedStyle(close).marginTop)+H-keep-mm-end())+'px'})();
</script>"""
DESCRIPTION_SHARE = 0.38    # the share of the table's width a description keeps


def script(look=None, paper="A4"):
    look = look or load()
    trade = look["trade"]
    return SCRIPT % {"page_h": _n(letter.PAPER_MM[paper][1]), "page_foot": letter.PAGE_FOOT,
                     "foot_gap": _n(trade["foot_gap"]), "share": DESCRIPTION_SHARE,
                     "foot_gap_tight": _n(trade["foot_gap"] * float(trade.get("tight") or 1))}


def dress(html, layout=None, paper="A4", look=None):
    """The sheet's page in the look: the CSS after the sheet's and the layout's own, the script after the
    sheet's own (which puts the heading under the window and the information block)."""
    look = look or load()
    html = html.replace("</style>", css(look, layout, paper) + "</style>", 1)
    return html.replace("</body>", script(look, paper) + "\n</body>", 1)


def _esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def closing(rows, after="", value=_esc):
    """The closing block of a page: rows of key and value on one grid (the terms, the due date, how to pay),
    then what else closes it (a delivery note's signature line). rows: [(key, value or list of lines)]; a row
    without a value is left out. after: finished HTML. value: how a value is escaped."""
    cells = []
    for key, val in rows:
        lines = [x for x in (val if isinstance(val, (list, tuple)) else [val]) if x not in (None, "")]
        if lines:
            cells.append('<div class="k">%s</div><div class="v">%s</div>' % (_esc(key), "<br>".join(value(x) for x in lines)))
    if not cells and not after:
        return ""
    return '<div class="close">%s%s</div>' % ('<div class="pay">%s</div>' % "".join(cells) if cells else "", after)


# ---- a document of more than one page ---------------------------------------------------------------
# Every page after the first carries one small running line: the document's name and number on the left,
# the page of the pages on the right (2 / 3: figures, so it reads the same in every language the packs
# write). The printer alone knows where the pages break, so the page is printed, its pages are counted, and
# a document of more than one page is printed once more with the lines in place. They stand outside the
# flow, in the room every following page keeps clear at its top, and move nothing.

RUN_TOP = letter.GEOMETRY["head_top"]      # mm from the top of a following page, where page 1 has the sender's name


def page_count(pdf):
    """How many pages a printed PDF has (Chromium writes each page object in the open); 0 when unreadable."""
    try:
        return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", Path(pdf).read_bytes()))
    except OSError:
        return 0


def running(html, pages, paper="A4"):
    """The page with a running line for each of its pages after the first."""
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    name = title.group(1) if title else ""
    height = letter.PAPER_MM[paper][1]
    lines = "".join('<div class="run" style="top:%smm"><span>%s</span><span>%d / %d</span></div>'
                    % (_n(height * (k - 1) + RUN_TOP), name, k, pages) for k in range(2, pages + 1))
    return html.replace("<footer>", lines + "<footer>", 1)


def print_pages(html, pdf, paper, printer):
    """Print the page; when it runs to more than one page, print it again with its running lines.
    printer(html, pdf, paper) prints and says how. Returns what the printer said."""
    how = printer(html, pdf, paper)
    pages = page_count(pdf)
    if pages > 1:
        page = Path(html)
        plain = page.read_text()
        page.write_text(running(plain, pages, paper))
        printer(html, pdf, paper)
        if page_count(pdf) != pages:        # a running line never adds a page; if one did, the page as it was
            page.write_text(plain)
            printer(html, pdf, paper)
    return how
