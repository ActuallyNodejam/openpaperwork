---
name: diagram
description: "A diagram as PDF, SVG and PNG: flowchart, swimlane, org chart, timeline, gantt plan, 2x2 matrix or layer stack. Not charts of numbers, not floor plans."
version: 0.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  domain: operations
  version: "0.1.0"
workflows:
  - id: "diagram"
    arguments: "diagram"
    icon: "workflow"
    menu: "Diagram"
    menu_en: "Diagram"
    gives: "Ett diagram som PDF, SVG och PNG: ett flöde, en organisation, en tidslinje eller en plan"
    gives_en: "A diagram as PDF, SVG and PNG: a flow, an org chart, a timeline or a plan"
    takes: "Skriv en rad: vårt orderflöde från förfrågan till faktura"
    takes_en: "Write one line: our order flow from request to invoice"
---

# Diagram

A diagram a person can put in front of their team: one idea, drawn so nothing clashes, clips or crosses, in the
company's look. The rules are diagram-design's (github.com/cathrynlavery/diagram-design, MIT, Copyright (c) 2025
Cathryn Lavery, version 2.6.74), ported as data, a builder and a check. You write the content; the builder owns
every coordinate.

`SKILL` below is this file's folder. Run every script with `python3`.

## First: should it be a diagram?

The best move is usually deletion (diagram-design, Philosophy). Draw only when a reader learns more from the
picture than from a paragraph or a three-column table. Every box is one idea: two that always travel together are
one box. Every arrow carries something: when the layout already says it, leave the arrow out. A list of things is
a list, not a diagram.

## Pick the type

| The person wants to show | Type |
| --- | --- |
| Steps and decisions, top to bottom: how a request is approved, what happens when | `flowchart` |
| Who does each step and who hands what to whom (people, teams, firms in lanes) | `swimlane` |
| Who owns what, who reports to whom, who to ask | `org-chart` |
| Dated milestones on an honest time scale | `timeline` |
| Phases and tasks with start and end dates | `gantt` |
| Items placed on two axes: value and effort, risk and impact | `quadrant` |
| Levels stacked on one another: policy over rules over routines, a stack of systems | `layers` |

A zone or room flow (lobby to lifts to corridor to rooms) is a `flowchart` of zones, never a drawn plan. Over
more than one floor, give each zone its floor as `group`, and the stair or lift that joins two floors one box in a
group of its own between them (`plan 10`, `stair`, `plan 11`), linked from the floor below and to the floor
above: the floors stand side by side and the drawing fits a slide. Zones with no route between them stand down
their floor's column in the order you list them. Plans print rooms, not routes: when they show no route, draw
none and let only the stair or lift join the floors, under the name each plan prints for it.

## The loop

1. Read the person's own files for the facts: names, roles, dates, steps. Every word on the diagram comes from
   them or from the ask. A fact the files do not give stays off the drawing and is named in the reply.
2. Write `<name>.diagram.json` in the person's folder. Start from the matching file in `SKILL/templates/`
   (`flowchart`, `swimlane`, `org-chart`, `timeline`, `gantt`, `quadrant`, `layers`); keep its shape, replace
   every word. Write in the language of the ask.
3. Build: `python3 SKILL/scripts/diagram.py <name>.diagram.json`. It writes `<name>.html` (the page), and beside
   it `<name>.pdf`, `<name>.svg` and `<name>.png`. If it stops with a message, change the data as it says and build
   again; never edit the HTML or the SVG by hand.
4. Check: `python3 SKILL/../_checks/packcheck.py diagram <name>.pdf`. Fix what a FAIL line names in the data,
   build, check again; three rounds at most, then say plainly what still fails.
5. Look at the PNG once. Then hand back the PDF first, and name the SVG and PNG for placing it elsewhere.
   The data, the page, the SVG and the PNG always stay beside the PDF, also when the person asked only for a
   PDF: the check reads them, a deck or a web page places the PNG, and the data builds it again. Never delete
   or move them.

To put the diagram on a business-deck page, use that deck's `figure` page with `image` set to the PNG
(`SKILL/../business-deck/SKILL.md`), and check that page with `packcheck.py business-deck`: it is a deck page, not
a diagram, so it has no SVG or PNG of its own.

## The data

Every type: `type`, `title` (the subject's short name, 60 characters at most), `description` (one sentence on
what the diagram shows, for a reader who cannot see it), and if useful `eyebrow` (a small label above the title),
`source` (where the facts come from, printed under the drawing), `language` (`en`, `sv`, `nb`, `da`, `de`, `fi`:
month names on a time axis), `legend` (`[{"kind": "focal", "label": "..."}]`, one entry for each box style used).

| Type | What you write |
| --- | --- |
| `flowchart` | `steps`: `id`, `name`, `note` (one short line), `shape` (`start`, `end`, `decision` or none), `focal`, `kind`; `links`: `from`, `to`, `label`, `focal`, `dashed`. Ranks follow the links; `row` (1, 2, ...) pins a step. `group` (a floor, a site, a department) sets steps in columns left to right under that name: list each group's steps together, a link inside a group goes to its next row, a link between groups to the next group. |
| `swimlane` | `lanes` (the people or teams, top to bottom); `steps`: `id`, `name`, `lane`, `note`, `focal`, `kind`; `links` as above, always to a later step. `col` (1, 2, ...) pins a step's column. |
| `org-chart` | `people`: `id`, `name`, `role` (what they own, a few words), `reports_to` (an id; nobody for the top), `focal`, `kind`. |
| `timeline` | `events`: `date` (2026-11-03, 2026-11 or 2026), `name`, `note`, `focal` (the milestone). |
| `gantt` | `tasks`: `phase`, `name`, `start`, `end`, `note`, `focal` (the critical task); `markers`: `date`, `name` (a deadline line). A phase's tasks stand together; a phase of one task that only repeats its name is left out. Every date carries its year: when the files print none, ask, or say which year you took and why. |
| `quadrant` | `x` and `y`: `{"name": "<one word>"}`; `quadrants`: `top_left`, `top_right`, `bottom_left`, `bottom_right` (a short tag each); `items`: `name`, `x`, `y` (0 to 1, never 0.5), `focal`. |
| `layers` | `layers` (top first): `name`, `note`, `tag`, `focal`; `direction` (two or three words for the arrow beside the stack), `flow` (`up`, the default, or `down` when the stack reads from the top layer to the bottom). |

A box's `kind` is its role: `step` (the default), `external` (outside the company), `optional` (only sometimes,
drawn dashed), `approval` (a gate, dashed accent), `store` (a register or archive), `input`. `focal: true` is the
accent.

## The rules (diagram-design, restated)

- **Accent on one or two things at most** (one in an org chart): the decision, handoff, task or layer the
  diagram is about. Accent on five erases the signal.
- **Budget:** 9 boxes and 12 arrows; a swimlane 5 lanes; an org chart 12 people, 4 tiers, 5 under one person; a
  gantt 12 tasks; a quadrant 12 items; a layer stack 4 to 6 layers. Over it, make two diagrams: an overview and a
  detail.
- **Short words.** A box name fits two lines and its note two lines; an arrow label is 14 characters at most
  (the builder sets it in capitals); detail belongs in the box, not on the arrow.
- **Honest time.** Dates sit where they fall; never space events evenly when they are not.
- **One owner a step.** A step drawn in a lane belongs to that lane's person; a step two people do is two steps.
- **Flow reads one way.** Swimlanes left to right, flowcharts top to bottom; reorder steps rather than send an
  arrow back and forth.
- The builder holds the rest: orthogonal arrows with rounded elbows, arrows behind boxes, attach points fanned
  12 px apart, labels on an opaque plate clear of their arrow and of every box, a legend as a strip under the
  drawing, a 4 px grid, the accessible SVG contract, no web font and no outside link.

## The look

The library's one look file, `skills/business-deck/look.json`: its face, its inks and its highlight. A company
pack replaces that file and every diagram, deck and page follows; nothing here sets a colour of its own. Pass
`--look <file>` to use another.

## What the check holds

`DIAG-CONTRACT` (the accessible SVG contract and single-file safety, diagram-design's self_check.py),
`DIAG-OFFLINE` (no web address), `DIAG-GEOMETRY` (its verify-geometry.py: label masks, orthogonal connectors,
ports, stacking), `DIAG-BOUNDS` (nothing past the edge), `DIAG-FIT` (every text inside its box),
`DIAG-OVERLAP` (nothing on top of anything), `DIAG-CONTRAST` (4.5:1 text, 3:1 lines), `DIAG-BUDGET`,
`DIAG-LABEL` (14 characters), `DIAG-EXPORT` (PDF, SVG and PNG made from this page), `DIAG-PNG` (the PNG is
the whole drawing at twice its size, nothing cut at an edge).

## Source and licence

Ported from diagram-design 2.6.74 at commit 7a2e22170ee838e859d8142ba825d83f8b6375e6 (MIT, Copyright (c) 2025
Cathryn Lavery; `LICENSE` in this folder): the philosophy, the type guide, the node treatments, the connector
rules, the complexity budget, the presentation type ramp, the accessible SVG contract and the type references for
flowchart, swimlane, org chart, timeline, gantt, quadrant and layer stack, restated; its self_check.py and
verify-geometry.py ported unchanged as `skills/_checks/diagram_contract.py` and `diagram_geometry.py`. Its other
37 types, dark and motion variants, imports and onboarding are not ported.
