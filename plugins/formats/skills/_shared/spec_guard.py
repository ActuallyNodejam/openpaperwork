#!/usr/bin/env python3
"""A builder never drops what it was given.

Every builder reads a data file and prints what it has a field for. Before this guard a key the builder
did not know was left off the page without a word, and a value of the wrong shape was guessed at: a
note given as one string where a list of lines is expected printed one letter a line, an amount given
as text was summed as whatever it parsed to. The guard reads the data file against the builder's own
list of fields (a `spec.fields.json` in the pack's folder) BEFORE anything is laid out:

    unknown key    an error that names the key, the nearest key the builder does know, and the one
                   place of that pack where a fact with no field of its own is printed
    wrong shape    an error that says what was given and what the field takes; nothing is guessed
    a tax rate     written as a fraction (0.2 where 20 percent is meant) is an error

This is a house rule of the library (a defect check on its own input), not a rule taken from a standard.

The fields file:

    {"about": "...",
     "open": {"": "notes", "seller": "further"},      path -> the key at that path that takes free lines
     "hints": {"contact": "a contact person goes in ..."},   an unknown key -> where this pack prints such a fact
     "defs": {"party": {...}},                         shapes used more than once, named "@party"
     "fields": {"type": "text", "lines": [{"quantity": "number"}], "seller": "@party", "notes": ["text"]}}

Shapes: "text" (one line of text; a number is printed as written), "number" (written as a number, never
as text), "rate" (a percentage written as a number: 20 for 20 percent), "flag" (true or false), "any"
(the builder reads it itself), ["shape"] (a list), {"key": shape} (an object; "*" as a key takes any
key), "@name" (a shape from "defs"), and "a | b" for a field that takes either. A key that starts with
an underscore is a comment for whoever fills the file in; it is never read and never printed.

The file lands in the person's folder, too: a builder refuses an output path inside the library's own folder
(output_guard), where a file is one the person never sees.

Standard library only.
"""
import difflib
import json
import os
import re
from pathlib import Path


def load_fields(path):
    return json.loads(Path(path).read_text())


def _name(path, key):
    return "%s.%s" % (path, key) if path else str(key)


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _show(v):
    text = json.dumps(v, ensure_ascii=False)
    return text if len(text) <= 60 else text[:57] + "..."


def _kind(v):
    if isinstance(v, bool):
        return "true or false"
    if _is_number(v):
        return "a number"
    if isinstance(v, str):
        return "text"
    if isinstance(v, list):
        return "a list"
    if isinstance(v, dict):
        return "an object"
    return "nothing (null)"


class Guard:
    def __init__(self, fields):
        self.defs = fields.get("defs") or {}
        self.open = fields.get("open") or {}
        self.hints = fields.get("hints") or {}
        self.known = {}                # path -> the keys the builder knows there, named once after the errors
        self.fields = fields["fields"]

    def shape_at(self, path, key):
        """The shape the fields file gives a key at a path, or None."""
        shape = self.fields
        for part in [p for p in path.split(".") if p] + [key]:
            shape = self.resolve(shape)
            if isinstance(shape, list):
                shape = self.resolve(shape[0])
            if not isinstance(shape, dict):
                return None
            shape = shape.get(part)
        return self.resolve(shape)

    def home(self, path):
        """The sentence that says where a fact with no field of its own is printed: the open key of the
        object the unknown key stands in, else of the nearest object above it."""
        probe = re.sub(r"\[\d+\]", "", path)
        while True:
            key = self.open.get(probe)
            if key:
                shape = self.shape_at(probe, key)
                if isinstance(shape, list) and isinstance(self.resolve(shape[0]), dict):
                    takes = "a list of entries (%s)" % ", ".join(sorted(self.resolve(shape[0])))
                elif isinstance(shape, list):
                    takes = "a list of lines printed as written"
                elif isinstance(shape, str) and "[" in shape:
                    takes = "a line or a list of lines printed as written"
                else:
                    takes = "one line of text printed as written"
                return ('a fact the page must carry and that has no field of its own goes in "%s", %s'
                        % (_name(probe, key), takes))
            if not probe:
                return ""
            probe = probe.rpartition(".")[0]

    @staticmethod
    def _inline(option):
        """One side of "a | b": "[text]" is a list of text, anything else a shape's own name."""
        return [option[1:-1].strip()] if option.startswith("[") and option.endswith("]") else option

    def resolve(self, shape):
        seen = 0
        while isinstance(shape, str) and shape.startswith("@") and seen < 8:
            shape = self.defs[shape[1:]]
            seen += 1
        return shape

    def fits(self, value, shape, path):
        """The errors of one value against one shape."""
        shape = self.resolve(shape)
        errors = []
        if shape == "any" or value is None:
            return errors
        if isinstance(shape, str) and "|" in shape:
            # Either shape: the one of the value's own kind is the one meant (an object against the object
            # shape, so its own keys are checked), else whichever fits best.
            options = [o.strip() for o in shape.split("|")]
            kind = dict if isinstance(value, dict) else list if isinstance(value, list) else str
            same = [o for o in options if isinstance(self.resolve(self._inline(o)), kind)
                    and not (kind is str and self.resolve(self._inline(o)) in ("number", "rate", "flag")
                             and not _is_number(value) and not isinstance(value, bool))]
            return min((self.fits(value, self._inline(o), path) for o in (same or options)), key=len)
        if shape == "text":
            if isinstance(value, (list, dict, bool)):
                errors.append('"%s" is %s (%s) where the builder prints one line of text. Write it as text'
                              % (path, _kind(value), _show(value)))
        elif shape in ("number", "rate"):
            if not _is_number(value):
                hint = ""
                if isinstance(value, str):
                    hint = (': write %s as a number, without quote marks, a currency sign or a thousands separator'
                            % _show(value))
                errors.append('"%s" is %s where the builder calculates with a number%s. Nothing is guessed'
                              % (path, _kind(value), hint))
            elif shape == "rate" and 0 < abs(value) < 1:
                errors.append('"%s" is %s: a rate is written as a percentage, so 20 percent is 20, not 0.2'
                              % (path, _show(value)))
        elif shape == "flag":
            if not isinstance(value, bool):
                errors.append('"%s" is %s (%s); write true or false' % (path, _kind(value), _show(value)))
        elif isinstance(shape, list):
            if isinstance(value, str):
                errors.append('"%s" is one string where the builder takes a list of %s; a string there is printed '
                              'one letter a line. Write ["%s"]'
                              % (path, "lines" if self.resolve(shape[0]) == "text" else "entries",
                                 value[:40] + ("..." if len(value) > 40 else "")))
            elif not isinstance(value, list):
                errors.append('"%s" is %s (%s) where the builder takes a list' % (path, _kind(value), _show(value)))
            else:
                for i, item in enumerate(value):
                    errors += self.fits(item, shape[0], "%s[%d]" % (path, i))
        elif isinstance(shape, dict):
            if not isinstance(value, dict):
                errors.append('"%s" is %s (%s) where the builder takes an object with the keys %s'
                              % (path, _kind(value), _show(value),
                                 ", ".join(sorted(k for k in shape if k != "*")[:14])))
            else:
                errors += self.walk(value, shape, path)
        return errors

    def walk(self, data, shape, path=""):
        errors = []
        anykey = shape.get("*")
        known = sorted(k for k in shape if k != "*")
        for key, value in data.items():
            if str(key).startswith("_"):
                continue                                   # a comment for whoever fills the file in
            here = _name(path, key)
            if key in shape:
                errors += self.fits(value, shape[key], here)
            elif anykey is not None:
                errors += self.fits(value, anykey, here)
            elif value in (None, "", [], {}):
                continue                                   # nothing given under it, so nothing to drop
            else:
                near = difflib.get_close_matches(str(key), known, n=2, cutoff=0.72)
                where = re.sub(r"\[\d+\]", "", path)
                hint = self.hints.get(_name(where, key)) or self.hints.get(str(key))
                home = hint or self.home(path)
                self.known[where] = known
                errors.append('unknown key "%s": the builder has no field of that name and would leave %s off the '
                              'page.%s%s'
                              % (here, _show(value),
                                 ' Did you mean %s?' % " or ".join('"%s"' % _name(path, n) for n in near) if near else "",
                                 " %s%s." % (("Otherwise " if near else ""), home if near else home[:1].upper() + home[1:])
                                 if home else ""))
        return errors


def problems(spec, fields):
    """Every error of a data file against a fields file (a dict as load_fields returns it). After the errors,
    one line for each place an unknown key stood in, with the keys the builder knows there."""
    if not isinstance(spec, dict):
        return ["the data file is %s; the builder reads one JSON object" % _kind(spec)]
    g = Guard(fields)
    found = g.walk(spec, fields["fields"])
    for where, known in sorted(g.known.items()):
        found.append("the keys the builder knows %s: %s" % ('in "%s"' % where if where else "at the top", ", ".join(known)))
    return found


def message(found, what="data file"):
    """The one text a builder stops with: what is wrong, each on its own line, and what never to do about it."""
    return ("the %s holds what this builder cannot print as given; nothing was built. Fix each and build again, "
            "and never leave a fact out to make an error go away:\n  - %s" % (what, "\n  - ".join(found)))


def guard(spec, fields_path, what="data file"):
    """Stop the build, before anything is laid out, when the data file holds a key the builder would drop
    or a value of the wrong shape. Returns the spec unchanged when it is sound."""
    found = problems(spec, load_fields(fields_path))
    if found:
        raise SystemExit(message(found, what))
    return spec


# ---- the file lands in the person's folder ------------------------------------------------------------

def library_root(script):
    """The library's own folder a builder stands in: the skills folder that holds its pack, or the plugin
    around that folder when it is one."""
    script = Path(script).resolve()
    for parent in script.parents:
        if (parent / "_shared" / "spec_guard.py").is_file():
            plugin = parent.parent
            if (plugin / ".claude-plugin").is_dir() or (plugin / "plugin.json").is_file():
                return plugin
            return parent
    return script.parents[1]


def working_folder(root):
    """The folder the person is working in, as far as a builder can tell, when it is not the library's own: the
    agent's project folder, the folder the shell stood in before it moved into the library, or the folder it
    stands in now. None when all of them are inside the library."""
    for value in (os.environ.get("CLAUDE_PROJECT_DIR"), os.environ.get("OLDPWD"), os.getcwd()):
        if not value:
            continue
        folder = Path(value).expanduser().resolve()
        try:
            folder.relative_to(root)
        except ValueError:
            if folder.is_dir():
                return folder
    return None


def output_problem(out, script, what="file"):
    """What is wrong with an output path that lies inside the library's own folder, or None. A file made there
    is beside the pack, not in the person's folder: the reply would name a path they never look in."""
    target = Path(out).expanduser()
    target = (Path.cwd() / target).resolve() if not target.is_absolute() else target.resolve()
    root = library_root(script)
    try:
        target.relative_to(root)
    except ValueError:
        return None
    folder = working_folder(root)
    where = ("the working folder, %s" % folder) if folder else "the working folder (the folder this chat was opened in)"
    return ("the %s would be written to %s, inside the library's own folder (%s), where the person never sees it; "
            "nothing was built. Write it in %s, beside the person's own files: run the builder from there, keep the "
            "data file there, and give the output path there." % (what, target, root, where))


def output_guard(out, script, what="file"):
    """Stop the build when the output path lies inside the library's own folder."""
    problem = output_problem(out, script, what)
    if problem:
        raise SystemExit(problem)
    return out
