#!/usr/bin/env python3
"""A hint at the moment the ask arrives: which pack makes the kind of file the person is asking for.

Asked for an invoice or for minutes in one plain sentence, a small model with the whole library loaded
often takes a general skill, or none, and writes a text file. An agent's skill list is capped and may
hold a pack as a bare name, and a description cannot help a run that never reads it. So this hook reads
the ask and, when it names a kind of file a pack in this plugin makes, adds one conditional line to the
turn:

  If this ask is for an invoice, load the e-invoice skill before writing anything: it lays the file out
  and checks it. Hand back a file, not text in the chat. The person's details are in the files in
  this folder: read them before asking for any.

The table is routes.json beside this file. scripts/build-portable-pack.py builds it from the `asks` list
in each pack's pack.json (what people call each kind of file, in every language the pack serves), only
for the packs this plugin carries, and stops when a title one of the packs' own pages prints would not
be routed to its pack, so the table and the pages cannot drift. No model call, no
network, nothing but the standard library; any error ends silent with exit 0, so an ask is never blocked.

How an ask is matched:
- Whole words, without regard to case or accents ("Fakturę", "albaran", "proces-verbal").
- A word with its language's common endings: a stem plus a short suffix, so "Rechnungen", "brevet",
  "laskun", "fakturę" and "fatture" match "Rechnung", "brev", "lasku", "faktura" and "fattura".
- A word of several words is a phrase ("credit note", "bon de commande"), matched in a row.
- `weak` words are ordinary words elsewhere ("brief", "list", "carta", "quote", "presentation"): they
  count only with one of that language's `with` words near them (three words before, four after), or
  when the ask also holds another word of the same pack.
- `unless` phrases take a word out ("capital letter", "on deck", "a la carta"), and `not_after` words
  before it do ("ten minutes of").
- A match inside a longer one of another kind is dropped: a "pro forma invoice" is a trade document,
  not an invoice; an "offer letter" is the terms of employment, not a letter.
- Two packs may match: both are named in the one line, each with what it is for. No match prints nothing.

Claude Code runs it from hooks/hooks.json on UserPromptSubmit, with the hook input on stdin (`prompt`).
Codex and Gemini CLI get the same line through pack_agents.py at their own prompt event;
Cursor CLI's prompt hook cannot add anything to a turn, so it gets none. An app that starts the
agent and gives this hint itself sets OPENPAPERWORK_APP, so the hook stands down there and a person
gets it exactly once.

  python3 pack_route.py --ask "Schreib die Rechnung für Beispiel Druck GmbH"     print the line for an ask
"""
import json
import os
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTES = HERE / "routes.json"
# Set by an app that starts the agent and adds the hint to the turn itself.
APP_ENV = "OPENPAPERWORK_APP"
# How every text the Stop hook sends begins: one that comes back as a prompt is no ask.
OURS = "A pack check "
# The characters of an ask that are read: its kind is named at the start, and a pasted document is not it.
LIMIT = 4000
# How near a `with` word must be to a weak word: this many words before it, this many after.
BEFORE, AFTER = 3, 4

# A word's common endings, by the word's own language (accents already taken off).
ENDINGS = {
    "en": ("s", "es"),
    "de": ("e", "en", "es", "s", "n", "er", "ern"),
    "nl": ("en", "s", "n", "je", "jes"),
    "fr": ("s", "x"),
    "es": ("s", "es"),
    "it": (),
    "sv": ("n", "en", "et", "t", "er", "ar", "r", "na", "s", "ns", "ens", "ets", "erna", "arna", "rna"),
    "nb": ("n", "en", "et", "a", "er", "r", "e", "ene", "ne", "s", "ens", "ets"),
    "da": ("n", "en", "et", "er", "r", "e", "ene", "ne", "s", "ens", "ets", "erne", "rne"),
    "fi": ("n", "a", "t", "ta", "tta", "ja", "jen", "ssa", "sta", "lle", "lla", "lta", "ksi", "na", "an", "en",
           "in", "on", "un", "at", "et", "ut", "een", "aan", "uun", "ni", "si", "nne"),
    "pl": ("u", "em", "y", "ie", "ow", "om", "ami", "ach", "a", "owi", "i"),
}
# Endings that take the place of a word's last vowel: faktura, fakturor, fakturę; fattura, fatture.
SWAP = {
    "sv": ("or", "orna", "ornas"),
    "it": ("a", "e", "i", "o"),
    "pl": ("", "a", "e", "y", "i", "o", "u", "ze", "ie", "om", "ach", "ami", "em", "ow"),
}
VOWELS = "aeiouy"
FOLD = str.maketrans({"ł": "l", "ø": "o", "æ": "ae", "œ": "oe", "đ": "d", "ð": "d", "þ": "th"})


def plain(text):
    """Lower case, no accents: what a person types on a keyboard that has none still matches."""
    text = unicodedata.normalize("NFKD", text.casefold().translate(FOLD))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def words_of(text):
    """The ask as plain words; everything that is no letter or digit parts them."""
    return "".join(ch if ch.isalnum() else " " for ch in plain(text[:LIMIT])).split()


def same(token, word, language):
    """Whether a word of the ask is this table word, as it is or with one of its language's endings."""
    if token == word:
        return True
    if len(word) < 4:
        return False
    if token.startswith(word):
        return token[len(word):] in ENDINGS.get(language, ())
    if len(word) >= 5 and word[-1] in VOWELS and language in SWAP and token.startswith(word[:-1]):
        return token[len(word) - 1:] in SWAP[language]
    return False


def key(token):
    return token[:3]


def listed(group):
    """A {language: [words]} group of the table as (language, the word's own words) pairs."""
    for language, words in (group or {}).items():
        for word in words:
            parts = words_of(word)
            if parts:
                yield language, parts


def table(routes):
    """The table by the first three letters of each entry's first word: (words, language, route, kind, sure)."""
    index = {}
    for r, route in enumerate(routes):
        for k, kind in enumerate(route.get("kinds") or []):
            for group, sure in (("words", True), ("weak", False)):
                for language, parts in listed(kind.get(group)):
                    index.setdefault(key(parts[0]), []).append((parts, language, r, k, sure))
    return index


def spans(tokens, group):
    """Where the phrases of a group stand in the ask: (start, end) pairs."""
    found = []
    for language, parts in listed(group):
        for at in range(len(tokens) - len(parts) + 1):
            if all(same(tokens[at + n], part, language) for n, part in enumerate(parts)):
                found.append((at, at + len(parts)))
    return found


def matches(text, routes):
    """Every place the ask names a kind of file: (start, end, route, kind), in the order they stand."""
    tokens = words_of(text)
    index = table(routes)
    sure, unsure = [], []
    for at, token in enumerate(tokens):
        for parts, language, r, k, strong in index.get(key(token), ()):
            if at + len(parts) > len(tokens):
                continue
            if all(same(tokens[at + n], part, language) for n, part in enumerate(parts)):
                (sure if strong else unsure).append((at, at + len(parts), r, k, language))
    # A weak word counts with a word of its own language beside it, or with a sure word of its pack.
    strong = list(sure)
    for match in unsure:
        start, end, r, k, language = match
        near = set(tokens[max(0, start - BEFORE):start] + tokens[end:end + AFTER])
        signals = {plain(word) for word in ((routes[r]["kinds"][k].get("with") or {}).get(language) or [])}
        if near & signals or any(other[2] == r for other in strong):
            sure.append(match)
    kept = []
    for start, end, r, k, language in sure:
        kind = routes[r]["kinds"][k]
        if any(a < end and start < b for a, b in spans(tokens, kind.get("unless"))):
            continue
        before = tokens[start - 1] if start else ""
        barred = {plain(word) for words in (kind.get("not_after") or {}).values() for word in words}
        if before and (before in barred or ("#" in barred and before.isdigit())):
            continue
        kept.append((start, end, r, k))
    # A match inside a longer one of another kind is that other kind: a pro forma invoice is no invoice.
    return sorted({m for m in kept if not any(
        (o[2], o[3]) != (m[2], m[3]) and o[0] <= m[0] and m[1] <= o[1] and o[1] - o[0] > m[1] - m[0] for o in kept)})


def asked(text, routes=None):
    """The packs an ask names, in the order it names them, each with the kinds it names: [(route, [kind])]."""
    routes = load() if routes is None else routes
    found = []
    for _, _, r, k in matches(text, routes):
        name = routes[r]["kinds"][k]["kind"]
        for route, names in found:
            if route is routes[r]:
                if name not in names:
                    names.append(name)
                break
        else:
            found.append((routes[r], [name]))
    return found


def either(names):
    return names[0] if len(names) == 1 else "%s or %s" % (", ".join(names[:-1]), names[-1])


#: Run 9 (2026-10-14): two asks were answered with a list of questions the folder's own files answered.
FOLDER = " The person's details are in the files in this folder: read them before asking for any."


def line(found):
    """The one line for the packs an ask names: one pack, or two with what each is for."""
    if not found:
        return ""
    if len(found) == 1:
        route, names = found[0]
        does = "it lays the file out and checks it" if route.get("checks") else "it lays the file out"
        return ("If this ask is for %s, load the %s skill before writing anything: %s. Hand back a file, not text "
                "in the chat.%s" % (either(names), route["skill"], does, FOLDER))
    (first, a), (second, b) = found[:2]
    does = "Each lays its file out and checks it" if first.get("checks") and second.get("checks") \
        else "Each lays its file out"
    return ("If this ask is for %s, load the %s skill before writing anything; if it is for %s, load the %s skill "
            "instead. %s. Hand back a file, not text in the chat.%s"
            % (either(a), first["skill"], either(b), second["skill"], does, FOLDER))


def load(path=ROUTES):
    """The table, less any pack whose folder is no longer beside it: a line never names a skill that is gone."""
    try:
        routes = json.loads(Path(path).read_text(encoding="utf-8")).get("routes") or []
    except (OSError, ValueError, AttributeError):
        return []
    skills = Path(path).resolve().parent.parent / "skills"
    return [route for route in routes if (skills / str(route.get("skill"))).is_dir()]


def an_ask(prompt):
    """Whether a prompt is a person's ask: not empty, not a command, not the Stop hook's own text coming back."""
    return isinstance(prompt, str) and bool(prompt.strip()) and not prompt.lstrip().startswith(("/", OURS))


def hint(prompt, routes=None):
    """The line to add to the turn for this ask, or "" when it names no kind of file a pack here makes."""
    return line(asked(prompt, routes)) if an_ask(prompt) else ""


def main(argv):
    if len(argv) > 2 and argv[1] == "--ask":
        print(hint(" ".join(argv[2:])))
        return 0
    data = json.load(sys.stdin)
    # An app that starts the agent adds the same line to the turn itself.
    if os.environ.get(APP_ENV) or not isinstance(data, dict):
        return 0
    text = hint(data.get("prompt"))
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": data.get("hook_event_name") or "UserPromptSubmit",
                                                 "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # a hint that breaks must never stand in the way of an ask
        sys.exit(0)
