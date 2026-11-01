#!/usr/bin/env python3
"""Build the library's plugins from skills/: one per department and one with everything.

  python3 scripts/build-portable-pack.py           write every plugin and the marketplace
  python3 scripts/build-portable-pack.py --check   exit 1 when a plugin differs from what skills/ builds

The shape is anthropics/skills' marketplace (one marketplace, several plugins) with anthropics/
financial-services' sync and drift check: skills/ is the one source, the plugins are copies.

- plugins/<domain>/ holds the packs whose pack.json names that domain (finance, sales, legal, hr,
  operations, marketing, engineering, academic, formats). portable-pack/ holds every pack and is the
  openpaperwork plugin, the one most people install and the one install.sh links for Codex and Gemini CLI.
- A pack imports check modules from skills/_checks, the shared letter from skills/_shared, and a few
  checks read a sibling pack's files (the letter check reads business-letter/scripts). Each plugin
  carries copies of exactly those files, found by reading the imports, so it works installed on its own:
  Claude Code refuses a path out of a plugin.
- Each plugin has a Claude Code manifest (.claude-plugin/plugin.json) and an Agent Plugins 1.0.0
  manifest (plugin.json, agent-plugins.org) for Codex, Cursor, Copilot, Kiro and VS Code.
- The root .claude-plugin/marketplace.json lists the plugins.
- Each plugin has a command per base workflow its packs declare (front matter `workflows:`, the list the app's
  starter cards read): commands/<id>.md, typed as /<plugin>:<id>. The shape is Cowork's knowledge-work-plugins
  (commands the person picks beside skills the agent draws on); the person names the outcome, so the agent
  never guesses the pack, and the command holds the run to one go and the reply to the file and what is open.
- Each plugin has a Claude Code Stop hook (hooks/hooks.json running hooks/pack_stop.py): a turn may not
  end while a pack's check is red over a file it wrote, three bounces at most, as in the app. Beside it
  is hooks/pack_agents.py, the same rule for Codex, Gemini CLI, Cursor CLI and other agents, which
  portable-pack/install.py writes into those agents' own hook files.
- Each plugin has a SessionStart hook (hooks/first_use.py) that sets the plugin's own Python up, once,
  in Claude Code's plugin data folder (CLAUDE_PLUGIN_DATA): a virtual environment with requirements.txt
  and Playwright's Chromium, skipped when a version marker matches; the Stop hook's check and the
  packs' scripts then run on that Python.
- Each plugin has a prompt-time hint (hooks/pack_route.py on UserPromptSubmit): when the ask names a kind
  of file one of the plugin's packs makes, one line says which skill to load. Its table is
  hooks/routes.json, built here from the `asks` list in each pack's pack.json (what people call each kind
  of file, by language); it holds only the packs the plugin carries. The pack.json is the one source (the
  app reads the same list), so nothing is added here: instead every title a pack's own page prints for a
  kind is held against the hint, and a title it would not route to its pack stops the build, naming the
  word to add to that pack's asks. So the table and the pages cannot drift. --check covers the file.

Hand-written files stay in portable-pack/ and are copied where a plugin needs them: the every-file and
brand-kit-deck skills (they exist only for agents outside the app), the MCP server, NOTICE,
requirements.txt and the installers (install.py, with install.sh and install-codex.sh in front of it).
Run from the repository root.
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
EVERYTHING = ROOT / "portable-pack"
PLUGINS = ROOT / "plugins"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
VERSION = "0.1.0"
AUTHOR = {"name": "OpenPaperwork"}
AGENT_PLUGINS = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AGENT_MCP = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

# The countries the library covers, in the order the everything text names them. This is the one list:
# the everything text is built from it, a department that covers fewer names its own, and
# standards/test_library.py holds every text and every row below against what each pack's own starters
# and tables cover.
COUNTRIES = {"DE": "Germany", "FR": "France", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
             "GB": "the UK", "US": "the US", "CA": "Canada", "AU": "Australia", "BE": "Belgium",
             "NL": "the Netherlands", "AT": "Austria", "IE": "Ireland", "ES": "Spain", "IT": "Italy", "PL": "Poland"}
# Pack, the countries it covers. A pack with no row is the same in every country.
PACK_COUNTRIES = {
    "e-invoice": "DE FR SE NO DK FI GB US CA AU BE NL AT IE ES IT PL",
    "annual-accounts": "SE",
    "trade-documents": "DE FR SE NO DK FI GB US CA AU BE NL AT IE ES IT PL",
    "employment-statement": "SE NO DK FI GB US CA AU BE NL AT IE ES IT PL",
    "business-letter": "DE SE NO DK FI GB US CA AU BE NL AT IE ES IT PL",
    "meeting-minutes": "SE NO DK FI GB US CA AU BE NL AT IE ES IT PL",
}


def named(codes):
    """The codes' names in the list's order, joined the way a text writes them (A, B and C)."""
    want = set(codes)
    words = [COUNTRIES[code] for code in COUNTRIES if code in want]
    return words[0] if len(words) == 1 else "%s and %s" % (", ".join(words[:-1]), words[-1])


# Department, plugin description. The order is the README's and the Library's. The words are the words
# desk's (2026-10-10): what gets done first, the documents by name, the kinds of file only in formats.
DOMAINS = {
    "finance": "Finance: invoices and credit notes with the file each country takes (Factur-X / ZUGFeRD and "
               "XRechnung for Germany and France; Peppol BIS 3 for Norway, Denmark, Finland, the UK, Belgium, the "
               "Netherlands (or SI-UBL), Austria (or ebInterface) and Ireland; Facturae for Spain, FatturaPA for "
               "Italy, the KSeF invoice for Poland), tax invoices for Australia, Canada and the US, and a smaller "
               "Swedish company's annual report (K2), each with its scripted check.",
    "sales": "Sales: quotations, order confirmations, delivery notes, pro forma invoices and purchase orders "
             "for Sweden, Norway, Denmark, Finland, Germany, Austria, the Netherlands, Belgium, France, Spain, Italy, "
             "Poland, the UK, Ireland, the US, Canada and Australia, each with the company details its own law "
             "asks for and a scripted check.",
    "legal": "Legal: an NDA, a DPA or a cloud service agreement drafted on Common Paper's standard terms, and "
             "the other side's agreement reviewed and handed back with tracked changes, each with a drafting "
             "check; not legal advice.",
    "hr": "HR: the written terms of employment for the EU, the UK, Ireland, Sweden, Norway, Denmark, Finland, "
          "Belgium, the Netherlands, Austria, Spain, Italy, Poland, Canada, Ontario and Australia, and a US "
          "offer letter, with a check of every item the law asks for; not legal advice.",
    "operations": "Operations: business letters for Germany and Sweden (DIN 5008), Norway, Denmark, Finland, "
                  "the US, the UK, Canada, Australia, Belgium, the Netherlands, Austria, Ireland, Spain, Italy "
                  "and Poland, meeting minutes and company board and general-meeting minutes for the same "
                  "countries except Germany, and decisions read out of a WhatsApp export.",
    "marketing": "Marketing: business decks handed back as a PDF, built to consulting structure, with an editable "
                 "PowerPoint file with native charts and tables when asked, and fair and event posters made from a "
                 "folder's own words and marks, each with its check.",
    "engineering": "Engineering: requirements specifications with numbered shall statements, verification "
                   "and SI units, with a check that flags vague words.",
    "academic": "Academic: IEEE and ACM papers, reference lists in APA 7, IEEE and Vancouver style with their "
                "check, literature search and a Zotero library (the paper pack needs a TeX engine, tectonic, "
                "on PATH).",
    "formats": "Formats: Word, Excel, PowerPoint and PDF files, decks from a brand kit, and the floor every "
               "document, workbook and deck should pass (no cut-off text, no formula errors), with the same "
               "check as an MCP tool.",
}
EVERYTHING_TEXT = ("OpenPaperwork's whole library, from invoices to board minutes: finance, sales, legal, HR, "
                   "operations, marketing, engineering, academic and the formats, for %s, with their scripted "
                   "checks." % named(code for codes in PACK_COUNTRIES.values() for code in codes.split()))
TITLES = {"finance": "Finance", "sales": "Sales", "legal": "Legal", "hr": "HR", "operations": "Operations",
          "marketing": "Marketing", "engineering": "Engineering", "academic": "Academic", "formats": "Formats"}

# Files a pack's tree never carries into a plugin: caches and the pack's own unit tests.
SKIP = {"__pycache__", "tests", ".pytest_cache"}
# Hand-written parts of the portable side, kept in portable-pack/ and copied where they belong.
OWN_SKILLS = {
    "every-file": ["SKILL.md", "scripts/check_file.py"],
    "brand-kit-deck": ["SKILL.md", "scripts/check_file.py"],
}
OWN_FILES = ["NOTICE", "requirements.txt"]
# The hook files every plugin carries, hand-written in portable-pack/hooks/: the Stop hook and its adapter
# for the other agents. The hooks.json below runs the first in Claude Code.
HOOK_FILES = ["hooks/pack_stop.py", "hooks/pack_agents.py", "hooks/pack_route.py", "hooks/first_use.py"]
HOOKS = {"description": "OpenPaperwork: the plugin's own Python set up once in the plugin's data folder, a "
                        "hint when an ask names a kind of file a pack makes, and the pack check over the "
                        "files this turn wrote; a red check sends the agent back to fix the file, three "
                        "times at most.",
         "hooks": {"SessionStart": [{"hooks": [{"type": "command",
                                                "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/first_use.py\"",
                                                "timeout": 600}]}],
                   "UserPromptSubmit": [{"hooks": [{"type": "command",
                                                    "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/pack_route.py\"",
                                                    "timeout": 10}]}],
                   "Stop": [{"hooks": [{"type": "command",
                                        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/pack_stop.py\"",
                                        "timeout": 600}]}]}}
# The languages a pack's `asks` may be written in: the ones hooks/pack_route.py knows the endings of.
ASK_LANGUAGES = ("en", "de", "fr", "nl", "sv", "nb", "da", "fi", "es", "it", "pl")
ASK_GROUPS = ("words", "weak", "with", "unless", "not_after")
# Files from elsewhere in the repository that the hand-written parts run.
EXTRA = {
    "every-file": {
        "skills/every-file/scripts/office_properties.py": "skills/powerpoint/scripts/office_properties.py",
    },
    "brand-kit-deck": {
        "skills/brand-kit-deck/scripts/pptx_from_kit.py": "skills/powerpoint/scripts/pptx_from_kit.py",
        "skills/brand-kit-deck/templates/standard-16x9.pptx": "skills/powerpoint/templates/standard-16x9.pptx",
    },
}
# The check_file.py scripts run mcp/server.py, which loads these.
MCP = {"mcp/checks/floor.py": "standards/checks/floor.py",
       "mcp/checks/brandkit.py": "standards/checks/brandkit.py"}
LICENSES = ["licenses/officecli-apache-2.0.txt", "licenses/common-paper-cc-by-4.0.txt",
            "licenses/mike-workflows-mit.txt", "licenses/factur-x-bsd-3.txt",
            "licenses/fnfe-france-rfe-apache-2.0.txt", "licenses/fr-official-texts-etalab-2.0.txt",
            "licenses/xrechnung-schematron-apache-2.0.txt", "licenses/rea-mit.txt", "LICENSE"]


def files_under(base):
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if p.is_file() and not SKIP.intersection(rel.parts) and p.suffix != ".pyc":
            yield rel.as_posix()


def front_matter(text):
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    return m.group(1) if m else ""


def meta(fm, key):
    m = re.search(r"^  %s:\s*\"?([^\"\n]+)\"?\s*$" % key, fm, re.M)
    return m.group(1).strip() if m else None


def description(fm):
    m = re.search(r"^description:\s*(.*?)(?=^\S[\w-]*:|\Z)", fm, re.S | re.M)
    return re.sub(r"\s+", " ", m.group(1)).strip().strip("\"'") if m else ""


WORKFLOW_KEYS = ("id", "menu_en", "gives_en", "takes_en")


def workflows(fm):
    """The base workflows a pack declares in its front matter, in the shape the app's starter cards read:
    `workflows:` then one `- id: ...` entry per workflow with arguments, icon, menu, menu_en, gives, gives_en,
    takes and takes_en, each value a JSON string."""
    m = re.search(r"^workflows:[ \t]*\n((?:[ \t]+.*(?:\n|$))*)", fm, re.M)
    out = []
    for line in (m.group(1).splitlines() if m else []):
        item = re.match(r"\s*(-\s+)?([\w-]+):\s*(.*?)\s*$", line)
        if not item:
            continue
        if item.group(1) or not out:
            out.append({})
        value = item.group(3)
        out[-1][item.group(2)] = json.loads(value) if value.startswith('"') else value
    return out


# A command and a skill of the same name in one plugin are one name to Claude Code, and the command wins: the paper
# and diagram skills could not be loaded at all, and Haiku took the command for the skill and printed the paper its
# own way (timed run c18, 2026-10-25). So the command names its skill's file, which Claude Code finds under
# ${CLAUDE_PLUGIN_ROOT} wherever the plugin is installed.
# "Leave a marked field" alone (2026-10-25, first rounds) had a brand deck add a date the notes never asked for as
# "[DATE]" and ask for it, a follow-up the command exists to spare: what the file can do without stays off it.
# "Name the file first" alone still had seven of 21 timed replies retell the page under "What it holds", "Innehåll"
# or "Inhalt" (pass 3, 2026-10-25), so the command says the reply never does.
COMMAND = """---
description: %(gives)s
argument-hint: %(takes)s
---

Load the %(pack)s skill and follow it: read ${CLAUDE_PLUGIN_ROOT}/skills/%(pack)s/SKILL.md first, since this
command is not the skill. The person gets %(gets)s.

What the person wrote: $ARGUMENTS

Their material is what they attached or named, and the notes, orders, lists or earlier files in the working
folder. Read it first.

Make it in one go. Ask only when the file cannot be made without the answer; take the plainest default for
everything else and say so in the reply. Never invent a name, number, address, date or bank detail, and add
none the person did not ask for. One the file needs and their material does not give is left the way the
skill says, empty or marked, and named in the reply.

Hand back the finished file in the working folder. The pack's check runs before the turn ends; fix a red
check first.

Reply in the language the person wrote in, or with no words in the language of their files. Name the file
first, then what is still open for them, one short line each: each assumption, each field to fill. Never
retell what the file holds: they open it. Say nothing about the skill, the check or the steps.
"""


def commands(members, library):
    """commands/<id>.md for every workflow the members declare, in member order."""
    out = {}
    for pack in members:
        for flow in workflows(front_matter(library[pack][1])):
            missing = [key for key in WORKFLOW_KEYS if not str(flow.get(key) or "").strip()]
            if missing:
                raise SystemExit("%s: a workflow in its SKILL.md has no %s" % (pack, ", ".join(missing)))
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", flow["id"]):
                raise SystemExit("%s: workflow id %r is not lower-case words joined by -" % (pack, flow["id"]))
            path = "commands/%s.md" % flow["id"]
            if path in out:
                raise SystemExit("%s: workflow id %r is taken by another pack in the same plugin" % (pack, flow["id"]))
            gives = flow["gives_en"].rstrip(".")
            gets = gives if gives[1:2].isupper() else gives[:1].lower() + gives[1:]   # mid-sentence, an NDA stays an NDA
            out[path] = (COMMAND % {"gives": gives, "gets": gets, "takes": flow["takes_en"].rstrip("."),
                                    "pack": pack}).encode()
    return out


def packs():
    """Every pack in the library: name -> (domain, its SKILL.md text)."""
    out = {}
    for folder in sorted(p for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        skill = folder / "SKILL.md"
        own = EVERYTHING / "skills" / folder.name / "SKILL.md"
        source = skill if skill.is_file() else own if folder.name in OWN_SKILLS else None
        if source is None:
            continue
        text = source.read_text()
        domain = meta(front_matter(text), "domain")
        if domain is None and (folder / "pack.json").is_file():
            domain = json.loads((folder / "pack.json").read_text()).get("domain")
        if domain not in DOMAINS:
            raise SystemExit("skills/%s names no department (%s); set metadata.domain in its SKILL.md" % (folder.name, domain))
        if (folder / "pack.json").is_file() and json.loads((folder / "pack.json").read_text()).get("retired"):
            continue        # a pack another pack has taken over ("retired": its name) is in no plugin
        out[folder.name] = (domain, text)
    for name in OWN_SKILLS:
        if name not in out:
            text = (EVERYTHING / "skills" / name / "SKILL.md").read_text()
            out[name] = (meta(front_matter(text), "domain"), text)
    return out


# --- What a plugin's packs import -------------------------------------------------------------------

def _packcheck_tables():
    text = (SKILLS / "_checks" / "packcheck.py").read_text()
    space = {}
    for name in ("SKILL_RULES", "MODULES"):
        m = re.search(r"^%s = (\{.*?^\})" % name, text, re.S | re.M)
        space[name] = eval(m.group(1), {})  # a literal dict in our own file
    return space["SKILL_RULES"], space["MODULES"]


def needed(members):
    """The files outside the members' own folders that they need, as paths under skills/."""
    rules_of, module_of = _packcheck_tables()
    checks = {p.stem for p in (SKILLS / "_checks").glob("*.py")}
    shared = {p.stem for p in (SKILLS / "_shared").glob("*.py")}
    # Files a check opens or runs by name: locales.json, fill-eval.js, measure_fill.py. Not the folders' own
    # SKILL.md, which is there only so `npx skills add` installs them beside the packs.
    data = [p.name for d in ("_checks", "_shared") for p in (SKILLS / d).iterdir()
            if p.is_file() and p.suffix != ".pyc" and p.name != "SKILL.md"]
    siblings = [p.name for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))]
    want = {"_checks/packcheck.py"}
    # packcheck checks every Word, Excel and PowerPoint file on the every-file floor as well as on its own pack
    # (floor.py, and the layout.py it imports). Only the formats plugin had it, and the legal plugin's check
    # stopped on the missing module, so the agent went looking for floor.py across the computer (timed run
    # c09, 2026-10-25).
    for rule in rules_of.get("every-file") or []:
        want.add("_checks/%s.py" % module_of[rule.split("-")[0]])
    for pack in members:
        rules = rules_of.get(pack) or []
        own = {}
        pj = SKILLS / pack / "pack.json"
        if pj.is_file():
            spec = json.loads(pj.read_text())
            rules = rules or spec.get("rules") or []
            own = spec.get("modules") or {}
        for rule in rules:
            prefix = rule.split("-")[0]
            if prefix in module_of:
                want.add("_checks/%s.py" % module_of[prefix])
            elif prefix not in own:
                raise SystemExit("%s: rule %s has no check module" % (pack, rule))
    queue = list(want) + ["%s/%s" % (pack, f) for pack in members if (SKILLS / pack).is_dir()
                          for f in files_under(SKILLS / pack) if f.endswith(".py")]
    seen = set()
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        path = SKILLS / rel
        if not path.is_file() or path.suffix != ".py":
            continue
        text = path.read_text()
        found = set()
        for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+?)(?:\s+as\s+\w+)?\s*(?:#.*)?$)", text, re.M):
            for name in (m.group(1) or m.group(2) or "").replace(" ", "").split(","):
                name = name.split(".")[0]
                if name in checks:
                    found.add("_checks/%s.py" % name)
                if name in shared:
                    found.add("_shared/%s.py" % name)
        for m in re.finditer(r"__import__\(\s*[\"'](\w+)[\"']", text):
            if m.group(1) in checks:
                found.add("_checks/%s.py" % m.group(1))
        for name in data:
            if re.search(r"[\"'/]%s[\"']" % re.escape(name), text):
                found.update("%s/%s" % (d, name) for d in ("_checks", "_shared") if (SKILLS / d / name).is_file())
        # A check that reads a sibling pack's folder: HERE.parent / "business-letter" / "scripts", or
        # a path string such as "html-deck/scripts/build_deck.py". packcheck.py names packs only in its
        # messages, so it is left out of this.
        if rel != "_checks/packcheck.py":
            for sib in siblings:
                if sib in members:
                    continue
                for m in re.finditer(r"[\"']%s[\"']\s*/\s*[\"']([\w.-]+)[\"']|[\"']%s/([\w.-]+)/" % (re.escape(sib), re.escape(sib)), text):
                    sub = m.group(1) or m.group(2)
                    base = SKILLS / sib / sub
                    if base.is_dir():
                        found.update("%s/%s/%s" % (sib, sub, f) for f in files_under(base))
                    elif base.is_file():
                        found.add("%s/%s" % (sib, sub))
        for f in found - seen:
            want.add(f)
            queue.append(f)
    return sorted(f for f in want if f.split("/")[0] not in members or f.startswith(("_checks/", "_shared/")))


# --- The routes table: what people call each kind of file -------------------------------------------

def page_titles():
    """The title each pack's own page prints for a kind of file: (pack, kind id, language, title).

    Trade documents keep theirs in skills/_checks/trade_words.json (words.<locale>.title.<kind>); the
    invoice page keeps `"invoice": ..., "credit_note": ...` beside each locale in its two page tables."""
    found = []
    words = json.loads((SKILLS / "_checks" / "trade_words.json").read_text(encoding="utf-8"))["words"]
    for locale, own in words.items():
        for ident, title in (own.get("title") or {}).items():
            found.append(("trade-documents", ident, locale[:2], title))
    for name in ("build_page.py", "country_page.py"):
        text = (SKILLS / "e-invoice" / "page" / name).read_text(encoding="utf-8")
        for m in re.finditer(r'"([a-z]{2})-[A-Z]{2}":\s*\{"invoice":\s*"([^"]+)",\s*"credit_note":\s*"([^"]+)"', text):
            found.append(("e-invoice", "invoice", m.group(1), m.group(2)))
            found.append(("e-invoice", "credit_note", m.group(1), m.group(3)))
    return [row for row in found if row[2] in ASK_LANGUAGES]


def weak_words(kind, language):
    return [word.casefold() for word in (kind.get("weak") or {}).get(language) or []]


def routes(members):
    """hooks/routes.json for a plugin: each of its packs that names `asks`, each kind with its words by
    language as lists. Nothing is added to what the pack.json says: the app reads the same list."""
    out = []
    for pack in members:
        path = SKILLS / pack / "pack.json"
        spec = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        kinds = []
        for ask in spec.get("asks") or []:
            if not isinstance(ask.get("kind"), str) or not ask.get("words"):
                raise SystemExit("skills/%s/pack.json: every entry of asks needs a kind and words" % pack)
            kind = {"id": ask.get("id") or "", "kind": ask["kind"]}
            for group in ASK_GROUPS:
                for language, words in (ask.get(group) or {}).items():
                    if language not in ASK_LANGUAGES or not isinstance(words, str):
                        raise SystemExit("skills/%s/pack.json: asks.%s.%s must be a comma-separated string in one "
                                         "of %s" % (pack, group, language, ", ".join(ASK_LANGUAGES)))
                    kind.setdefault(group, {})[language] = [w.strip() for w in words.split(",") if w.strip()]
            kinds.append(kind)
        if kinds:
            out.append({"skill": pack, "checks": bool(spec.get("check")), "kinds": kinds})
    return {"note": "What people call each kind of file this plugin's packs make. Built by "
                    "scripts/build-portable-pack.py from the asks list in each pack's pack.json and the titles "
                    "the packs' own pages print; change it there, never here. Read by hooks/pack_route.py.",
            "routes": out}


def unrouted(table):
    """The page titles the hint would not send to their own pack, as lines; none when the table holds. A
    title the pack lists as weak is an ordinary word elsewhere ("avoir") and is let be."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pack_route", EVERYTHING / "hooks" / "pack_route.py")
    route = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(route)
    carried = {entry["skill"] for entry in table["routes"]}
    lost = []
    weak = {(entry["skill"], kind["id"], language): weak_words(kind, language)
            for entry in table["routes"] for kind in entry["kinds"] for language in ASK_LANGUAGES}
    for pack, ident, language, title in page_titles():
        if pack not in carried or title.casefold() in weak.get((pack, ident, language), ()):
            continue
        found = [(entry["skill"], names) for entry, names in route.asked(title, table["routes"])]
        if not found or found[0][0] != pack:
            lost.append("the %s page title %r (%s, %s) is not routed to %s (the hint finds %s): add it to "
                        "asks in skills/%s/pack.json"
                        % (pack, title, ident, language, pack, [name for name, _ in found] or "nothing", pack))
    return lost


# --- The plugins ------------------------------------------------------------------------------------

def dumps(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


def plugin(name, text, members, library, mcp):
    """Every file of one plugin: relative path -> bytes (source files are read lazily as Paths)."""
    out = {}
    for pack in members:
        if (SKILLS / pack).is_dir():
            for f in files_under(SKILLS / pack):
                out["skills/%s/%s" % (pack, f)] = SKILLS / pack / f
        for f in OWN_SKILLS.get(pack, []):
            out["skills/%s/%s" % (pack, f)] = EVERYTHING / "skills" / pack / f
        for dst, src in EXTRA.get(pack, {}).items():
            out[dst] = ROOT / src
    for f in needed([p for p in members if (SKILLS / p).is_dir()]):
        out["skills/%s" % f] = SKILLS / f
    if mcp:
        out.update({dst: ROOT / src for dst, src in MCP.items()})
        out["mcp/server.py"] = EVERYTHING / "mcp" / "server.py"
        out[".mcp.json"] = EVERYTHING / ".mcp.json"
        out["mcp.json"] = dumps({"$schema": AGENT_MCP, "mcpServers": {"openpaperwork-checks": {
            "type": "stdio", "command": "python3", "args": ["${PLUGIN_ROOT}/mcp/server.py"], "cwd": "${PLUGIN_ROOT}"}}})
    for lic in LICENSES:
        out[lic] = ROOT / lic
    for f in OWN_FILES:
        out[f] = EVERYTHING / f
    for f in HOOK_FILES:
        out[f] = EVERYTHING / f
    out["hooks/hooks.json"] = dumps(HOOKS)
    table = routes([p for p in members if (SKILLS / p).is_dir()])
    lost = unrouted(table)
    if lost:
        raise SystemExit("%s: %s" % (name, "; ".join(lost[:8])))
    out["hooks/routes.json"] = dumps(table)
    out.update(commands(members, library))
    domains = sorted({library[p][0] for p in members}, key=list(DOMAINS).index)
    out[".claude-plugin/plugin.json"] = dumps({"name": name, "description": text, "version": VERSION,
                                               "author": AUTHOR, "license": "Apache-2.0", "keywords": domains})
    out["plugin.json"] = dumps({"$schema": AGENT_PLUGINS, "name": name, "version": VERSION, "description": text,
                                "author": AUTHOR, "license": "Apache-2.0", "keywords": domains})
    return out


def readme(domain, members, library):
    rows = []
    for pack in members:
        desc = description(front_matter(library[pack][1]))
        first = re.split(r"(?<=[.:])\s", desc, maxsplit=1)[0].rstrip(":.")
        rows.append("| `skills/%s` | %s |" % (pack, first.replace("|", "/")))
    return ("""# OpenPaperwork %s

%s

| Pack | What it is for |
| --- | --- |
%s
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

%s
Install it in Claude Code with `/plugin install openpaperwork-%s@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
""" % (TITLES[domain], DOMAINS[domain].split(": ", 1)[1], "\n".join(rows), command_table(domain, members, library),
       domain)).encode()


def command_table(domain, members, library):
    """The README's list of the plugin's commands: what each gives and what to drop or type."""
    rows = ["| `/openpaperwork-%s:%s` | %s | %s |" % (domain, flow["id"], flow["gives_en"].rstrip("."),
                                                     flow["takes_en"].rstrip("."))
            for pack in members for flow in workflows(front_matter(library[pack][1]))]
    if not rows:
        return ""
    return ("""## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
%s
""" % "\n".join(rows))


def build():
    library = packs()
    plan = {}
    for domain in DOMAINS:
        members = [p for p, (d, _) in library.items() if d == domain]
        if not members:
            raise SystemExit("no pack names the %s department" % domain)
        files = plugin("openpaperwork-%s" % domain, DOMAINS[domain], members, library,
                       mcp=any(p in OWN_SKILLS for p in members))
        files["README.md"] = readme(domain, members, library)
        plan["plugins/%s" % domain] = files
    everything = plugin("openpaperwork", EVERYTHING_TEXT, list(library), library, mcp=True)
    # portable-pack/ keeps its own README, installers, MCP server and tests: only the copies are built.
    for own in OWN_FILES + HOOK_FILES + [".mcp.json", "mcp/server.py"] + ["skills/%s/%s" % (s, f) for s, fs in OWN_SKILLS.items() for f in fs]:
        everything.pop(own, None)
    plan["portable-pack"] = everything
    market = {"name": "openpaperwork", "owner": AUTHOR,
              "metadata": {"description": "OpenPaperwork's library of standards packs: the whole library as one "
                                          "plugin, or one department only.", "version": VERSION},
              # The whole library comes first: it is the one most people install (a founder, 2026-11-01).
              "plugins": [{"name": "openpaperwork", "source": "./portable-pack", "description": EVERYTHING_TEXT,
                           "version": VERSION, "category": "everything"}]
              + [{"name": "openpaperwork-%s" % d, "source": "./plugins/%s" % d, "description": DOMAINS[d],
                  "version": VERSION, "category": d} for d in DOMAINS]}
    return plan, dumps(market)


def portable_own():
    """portable-pack/'s hand-written files, which the build never writes or removes."""
    keep = set(OWN_FILES) | set(HOOK_FILES) | {"README.md", "install.py", "install.sh", "install-codex.sh", "doctor.sh", ".mcp.json",
                                               "mcp/server.py"}
    keep |= {"skills/%s/%s" % (s, f) for s, fs in OWN_SKILLS.items() for f in fs}
    keep |= {"tests/" + f for f in files_under(EVERYTHING / "tests")} if (EVERYTHING / "tests").is_dir() else set()
    return keep


def on_disk(base):
    return {p.relative_to(base).as_posix() for p in base.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"} if base.is_dir() else set()


def main(argv):
    check = "--check" in argv
    plan, market = build()
    drifted = []
    count = 0
    for target, files in plan.items():
        base = ROOT / target
        extra = on_disk(base) - set(files) - (portable_own() if target == "portable-pack" else set())
        for rel in sorted(extra):
            if check:
                drifted.append("%s/%s has no source any more" % (target, rel))
            else:
                (base / rel).unlink()
        for rel, src in sorted(files.items()):
            data = src.read_bytes() if isinstance(src, Path) else src
            dst = base / rel
            count += 1
            if check:
                if not dst.is_file() or dst.read_bytes() != data:
                    drifted.append("%s/%s differs from its source" % (target, rel))
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.is_file() or dst.read_bytes() != data:
                dst.write_bytes(data)
                if isinstance(src, Path):
                    shutil.copymode(src, dst)
        if not check:
            for d in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
                if not any(d.iterdir()):
                    d.rmdir()
    if check:
        if not MARKETPLACE.is_file() or MARKETPLACE.read_bytes() != market:
            drifted.append(".claude-plugin/marketplace.json differs from what the build writes")
    else:
        MARKETPLACE.parent.mkdir(exist_ok=True)
        MARKETPLACE.write_bytes(market)
    if drifted:
        print("\n".join(drifted[:60]) + ("\n... and %d more" % (len(drifted) - 60) if len(drifted) > 60 else ""))
        print("Run python3 scripts/build-portable-pack.py and commit the result.")
        return 1
    print("library plugins %s: %d plugins, %d files" % ("in step" if check else "built", len(plan), count))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
