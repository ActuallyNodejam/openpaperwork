#!/usr/bin/env python3
"""A company's facts are written once, and every pack reads them.

`company.json` stands in the person's folder, beside their files. It holds the company's own particulars: the
seller party of EN 16931-1 (BG-4 to BG-7: name, trading name, identifiers, legal registration, VAT number,
address, contact), its payment details (BG-16, BG-17) and the mentions its own country's company law asks for
(the register and its number, the registered office, the share capital, the directors). Every key is one a
builder already reads for a sender (company.fields.json beside this file lists them).

    Every builder that prints a sender fills, from this file, what its data file leaves out, and stops when
    the data file says something else than this file does. The check (COMPANY-FILE) fails a page whose
    sender disagrees with it or leaves one of its numbers off.

    python3 <skills>/_shared/company.py make company.json name="Example Studio Ltd" country=GB \\
        street="12 Sample Square" postcode="M1 1AA" city=Manchester register_number=01234567
        (or: make company.json --from particulars.json)
    writes the file from what the person gives, refuses a key it has no field for, and says which particulars
    that country's company law still wants. One the files do not give is declared with unknown=register_number:
    it is printed as nothing and warned about, never made up.

A house rule of the library; the shape is EN 16931-1's seller, cited, nothing copied. Standard library only.
"""
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec_guard  # noqa: E402

NAME = "company.json"
FIELDS = HERE / "company.fields.json"
# What a sender party takes from the file as it stands (the keys every letter, trade and invoice builder reads).
PARTY = ("name", "trading_name", "legal_form", "street", "street2", "postcode", "city", "county", "province", "state",
         "country", "vat_id", "tax_number", "tax_code", "register", "register_number", "registered_office",
         "share_capital", "paid_up_capital", "sole_shareholder", "in_liquidation", "directed_by", "group",
         "managing_directors", "siren", "siret", "rcs", "abn", "acn", "org_number", "business_id", "cvr", "kvk",
         "enterprise_number", "email", "phone", "web", "contact", "further")
PAYMENT = ("bank", "iban", "bic", "account", "account_name", "sort_code", "bsb", "routing", "bank_reg", "bankgiro", "plusgiro")
# The particulars a page of the company must carry when the file gives them: its name and its numbers.
ON_THE_PAGE = ("name", "vat_id", "register_number")


def find(start):
    """company.json in the folder the data file is in, or one or two folders up."""
    folder = Path(start).resolve()
    folder = folder if folder.is_dir() else folder.parent
    for base in (folder, folder.parent, folder.parent.parent):
        path = base / NAME
        if path.is_file():
            return path
    return None


def load(path):
    try:
        data = json.loads(Path(path).read_text())
    except ValueError as exc:
        raise SystemExit("%s is not valid JSON: %s" % (path, exc))
    found = spec_guard.problems(data, spec_guard.load_fields(FIELDS))
    if found:
        raise SystemExit(spec_guard.message(found, "company file %s" % path))
    return data


def unknown_of(company):
    listed = company.get("unknown") or []
    return {str(k).strip() for k in ([listed] if isinstance(listed, str) else listed)}


def _empty(value):
    return value in (None, "", [], {})


def _same(a, b):
    """Two values that say the same: spaces, case and the grouping of a number aside."""
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, list) or isinstance(b, list):
        la = sorted(_norm(x) for x in (a if isinstance(a, list) else [a]))
        lb = sorted(_norm(x) for x in (b if isinstance(b, list) else [b]))
        return la == lb
    try:
        return Decimal(str(a).replace(",", "").replace(" ", "")) == Decimal(str(b).replace(",", "").replace(" ", ""))
    except InvalidOperation:
        return _norm(a) == _norm(b)


def _norm(value):
    return re.sub(r"[\s .\-/,]", "", str(value)).casefold()


def fill(party, company, keys=PARTY):
    """(the party with what it leaves out filled from the company file, the keys that were filled, the keys
    on which the two disagree as [(key, in the data file, in the company file)])."""
    out = dict(party or {})
    filled, clash = [], []
    for key in keys:
        if _empty(company.get(key)):
            continue
        if _empty(out.get(key)):
            out[key] = company[key]
            filled.append(key)
        elif not _same(out[key], company[key]):
            clash.append((key, out[key], company[key]))
    return out, filled, clash


def is_ours(party, company):
    """The party is the company of the file: the same name, or the same VAT or register number."""
    party = party or {}
    if not _empty(party.get("name")) and not _empty(company.get("name")):
        return _same(party["name"], company["name"])
    return any(not _empty(party.get(k)) and not _empty(company.get(k)) and _same(party[k], company[k])
               for k in ("vat_id", "register_number"))


# ---- each pack's sender --------------------------------------------------------------------------------

def _address_line(company):
    place = " ".join(str(x) for x in (company.get("postcode"), company.get("city")) if not _empty(x))
    return ", ".join(str(x) for x in (company.get("street"), place) if not _empty(x))


def sender_of(spec, pack):
    """(where the sender stands in a data file, the sender as a party) for a pack, or (None, None)."""
    if pack == "business-letter":
        return "sender", spec.get("sender")
    if pack == "trade-documents":
        role = "buyer" if spec.get("type") == "purchase_order" else "seller"
        return role, spec.get(role)
    if pack == "e-invoice":
        return "seller", spec.get("seller")
    if pack == "meeting-minutes":
        return "", {"name": spec.get("body"), "register_number": spec.get("company_number"),
                    "legal_form": spec.get("legal_form")}
    if pack == "employment-statement":
        e = spec.get("employer") or {}
        return "employer", {"name": e.get("name"), "phone": e.get("phone")}
    if pack == "contract-drafting":
        for i, p in enumerate(spec.get("parties") or []):
            if isinstance(p, dict) and p.get("name"):
                return "parties[%d]" % i, {"name": p.get("name"), "register_number": p.get("registration")}
    return None, None


def _known(fields_path, where):
    """The keys a pack's builder has a field for at a place of its data file (its spec.fields.json), so that
    only what the builder can print is taken from the company file. None when there is no fields file."""
    if not fields_path or not Path(fields_path).is_file():
        return None
    guard = spec_guard.Guard(spec_guard.load_fields(fields_path))
    shape = guard.shape_at("", where)
    return set(shape) if isinstance(shape, dict) else None


def apply(spec, data_file, pack, say=True, fields=None):
    """Fill the sender of a data file from company.json where the data file leaves a particular out. Stops
    when the two disagree. Returns {"file", "filled"} or None when the folder has no company file or the
    sender is another company. Called by every builder that prints a sender, before anything is laid out."""
    path = find(Path(data_file).parent if Path(data_file).suffix else data_file)
    if not path or not isinstance(spec, dict):
        return None
    company = load(path)
    where, party = sender_of(spec, pack)
    if where is None:
        return None
    named = bool(party and not _empty(party.get("name")))
    if named and not is_ours(party, company):
        return None                                  # another company's paper: the file is not about it
    filled, clash = [], []
    if fields is None:
        fields = HERE.parent / pack / "spec.fields.json"
    if pack in ("business-letter", "trade-documents", "e-invoice"):
        known = _known(fields, where)
        spec[where], filled, clash = fill(spec.get(where), company, [k for k in PARTY if known is None or k in known])
        filled = ["%s.%s" % (where, k) for k in filled]
        clash = [("%s.%s" % (where, k), a, b) for k, a, b in clash]
        pay_key = {"trade-documents": "bank", "e-invoice": "payment"}.get(pack)
        if pay_key and isinstance(company.get("payment"), dict) and not (pack == "trade-documents" and
                                                                         spec.get("type") in ("purchase_order", "delivery_note")):
            known = _known(fields, pay_key)
            spec[pay_key], f, c = fill(spec.get(pay_key), company["payment"],
                                       [k for k in PAYMENT if known is None or k in known])
            filled += ["%s.%s" % (pay_key, k) for k in f]
            clash += [("%s.%s" % (pay_key, k), a, b) for k, a, b in c]
        if pack == "business-letter" and isinstance(company.get("contact"), dict):
            spec["contact"], f, c = fill(spec.get("contact"), company["contact"], ("name", "phone", "email"))
            filled += ["contact.%s" % k for k in f]
        if pack == "business-letter" and isinstance(company.get("signatory"), dict) and _empty(spec.get("signatory")):
            spec["signatory"] = dict(company["signatory"])
            filled.append("signatory")
    elif pack == "meeting-minutes":
        for key, source in (("body", "name"), ("company_number", "register_number"), ("legal_form", "legal_form")):
            if _empty(company.get(source)):
                continue
            if _empty(spec.get(key)):
                spec[key] = company[source]
                filled.append(key)
            elif key != "legal_form" and not _same(spec[key], company[source]):
                clash.append((key, spec[key], company[source]))
    elif pack == "employment-statement":
        e = dict(spec.get("employer") or {})
        wanted = {"name": company.get("name"), "phone": company.get("phone"), "address": _address_line(company),
                  "number": company.get("register_number")}
        for key, value in wanted.items():
            if _empty(value):
                continue
            if _empty(e.get(key)):
                e[key] = value
                filled.append("employer.%s" % key)
            elif key in ("name",) and not _same(e[key], value):
                clash.append(("employer.%s" % key, e[key], value))
            elif key == "number" and _norm(value) not in _norm(e[key]):
                clash.append(("employer.number", e[key], value))
        spec["employer"] = e
    elif pack == "contract-drafting":
        i = int(re.search(r"\d+", where).group(0))
        p = dict(spec["parties"][i])
        for key, value in (("registration", company.get("register_number")), ("address", _address_line(company))):
            if _empty(value):
                continue
            if _empty(p.get(key)):
                p[key] = value
                filled.append("%s.%s" % (where, key))
            elif key == "registration" and _norm(value) not in _norm(p[key]):
                clash.append(("%s.registration" % where, p[key], value))
        spec["parties"][i] = p
    if clash:
        raise SystemExit("the data file says something else about the company than %s does; nothing was built:\n  - %s\n"
                         "The company file is the company's own record, written once. Correct whichever is wrong from "
                         "the person's files, and never change a particular to make the two agree."
                         % (path, "\n  - ".join('"%s" is %s in the data file and %s in the company file'
                                                % (k, json.dumps(a, ensure_ascii=False), json.dumps(b, ensure_ascii=False))
                                                for k, a, b in clash)))
    if say and filled:
        print("company file %s: filled %s" % (path, ", ".join(filled)), file=sys.stderr)
    return {"file": str(path), "filled": filled}


# ---- making the file -----------------------------------------------------------------------------------

def still_wanted(company):
    """What the country's own company law asks a company's papers to state that the file does not give and
    does not declare unknown (skills/_shared/letter.py company_missing, which cites each article)."""
    import letter
    unknown = unknown_of(company)
    return [m for m in letter.company_missing(company) if m.split(" ")[0] not in unknown]


def make(argv):
    if not argv:
        print(__doc__)
        return 2
    out = Path(argv[0])
    data = load(out) if out.is_file() else {}
    rest = argv[1:]
    if "--from" in rest:
        src = json.loads(Path(rest[rest.index("--from") + 1]).read_text())
        data.update(src)
        rest = [a for i, a in enumerate(rest) if a != "--from" and (i == 0 or rest[i - 1] != "--from")]
    for pair in rest:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit('give each particular as key=value (name="Example Studio Ltd"); got %r' % pair)
        if key in ("managing_directors", "further", "unknown"):
            data[key] = list(data.get(key) or []) + [value] if not isinstance(data.get(key), str) else [data[key], value]
        elif "." in key:
            head, _, tail = key.partition(".")
            data.setdefault(head, {})[tail] = value
        else:
            data[key] = value
    found = spec_guard.problems(data, spec_guard.load_fields(FIELDS))
    if found:
        raise SystemExit(spec_guard.message(found, "company file"))
    if _empty(data.get("name")) or _empty(data.get("country")):
        raise SystemExit("the company file needs at least the company's name and its country")
    spec_guard.output_guard(out, __file__, "company file")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    wanted = still_wanted(data)
    unknown = sorted(unknown_of(data))
    summary = {"file": str(out), "particulars": len([k for k in data if k != "unknown"]), "still_wanted": wanted,
               "declared_unknown": unknown}
    if wanted:
        summary["say"] = ("The company's own law asks its papers to state %s; the file does not give them. Take them "
                          "from the person's files; if they are not there, say so in your reply and declare each with "
                          "unknown=<key>. Never make one up." % ", ".join(wanted))
    elif unknown:
        summary["say"] = ("Declared unknown and printed as nothing: %s. Say in your reply that the papers are not "
                          "complete without them." % ", ".join(unknown))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "make":
        sys.exit(make(sys.argv[2:]))
    print(__doc__)
    sys.exit(2)
