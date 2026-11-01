#!/usr/bin/env python3
"""Business and payment identifiers the Nordic and English-speaking invoices carry: their check digits
and the forms they are printed in. The page builder and the pack check read the same functions, so
an identifier the build accepts is one the check accepts.

    Norway     organisasjonsnummer, nine digits, modulus 11 with weights 3 2 7 6 5 4 3 2 (Brønnøysund-
               registrene; the Peppol rule PEPPOL-COMMON-R041 and NO-R-001 test the same); an account
               number, eleven digits, modulus 11 with weights 5 4 3 2 7 6 5 4 3 2; a KID, modulus 10
               or 11 (Bits / Nets)
    Denmark    CVR-nummer, eight digits (modulus 11 with weights 2 7 6 5 4 3 2 1 for numbers issued
               under the old rule; read as a warning, never a refusal)
    Finland    Y-tunnus, seven digits, a hyphen and a check digit (modulus 11, weights 7 9 10 5 8 4 2);
               the Finnish creditor reference (viitenumero), weights 7 3 1 from the right; the bank
               barcode version 4 (Finanssiala, "Pankkiviivakoodi", freely usable)
    UK         VAT registration number, nine digits, modulus 97 (HMRC VAT Notice 700/1)
    Australia  ABN, eleven digits, modulus 89 with weights 10 1 3 5 7 9 11 13 15 17 19 (Australian
               Business Register, "Format of the ABN")
    Canada     the business number, nine digits, and the GST/HST program account RT0001
    Belgium    the enterprise number (ondernemingsnummer, numéro d'entreprise), ten digits starting 0 or
               1 whose last two are 97 less the first eight modulo 97 (Crossroads Bank for
               Enterprises; the Peppol rule PEPPOL-COMMON-R043 tests the same for scheme 0208); the VAT
               number is BE and the enterprise number; the structured payment reference (OGM/VCS)
               +++123/4567/89012+++, ten digits and then the remainder of those ten modulo 97, written
               97 when the remainder is 0 (Febelfin); it is not 97 less the remainder, the enterprise
               number's rule
    Netherlands  the btw-identificatienummer NL, nine digits, B and two digits (Ondernemersplein): the nine
               digits pass the eleven test (weights 9..2) or, for the btw-id issued from 2020, the whole
               number passes ISO 7064 modulus 97 with the letters as numbers; neither is a published rule,
               so a mismatch only warns; the KvK number, eight digits
    Austria    the UID-Nummer ATU and eight digits, the last a check digit by the ministry's own formula
               (BMF, "Konstruktionsregeln der UID", November 2020: C9 = (10 - (R + C2 + C4 + C6 + C8 + 4)
               mod 10) mod 10 with R = S3 + S5 + S7 and Si = INT(Ci / 5) + (Ci * 2) mod 10; its sample is
               U10223006); the Firmenbuchnummer FN 123456a
    Ireland    the VAT registration number IE, seven digits and a check letter, with a second letter
               (A-I, W) on newer numbers, or the old form with a letter, + or * second (the forms the
               European Commission's VIES lists for Ireland); the check letter,
               weights 8..2, the second letter times 9, modulo 23 read as W A B ... V, is the one in common
               use, not a published rule, so it only warns
    Any        IBAN, ISO 13616 modulus 97

Standard library only.
"""
import re

_D = re.compile(r"\D")


def digits(value):
    return _D.sub("", str(value or ""))


# ---- Norway ------------------------------------------------------------------------------------

def no_orgnr_ok(value):
    d = digits(value)
    if len(d) != 9:
        return False
    s = sum(int(c) * w for c, w in zip(d[:8], (3, 2, 7, 6, 5, 4, 3, 2)))
    check = 11 - s % 11
    check = 0 if check == 11 else check
    return check != 10 and check == int(d[8])


def no_orgnr_text(value):
    """999 999 999: the way Brønnøysundregistrene and Norwegian invoices print it."""
    d = digits(value)
    return " ".join((d[:3], d[3:6], d[6:9])) if len(d) == 9 else str(value or "")


def no_account_ok(value):
    d = digits(value)
    if len(d) != 11:
        return False
    s = sum(int(c) * w for c, w in zip(d[:10], (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)))
    check = 11 - s % 11
    check = 0 if check == 11 else check
    return check != 10 and check == int(d[10])


def no_account_text(value):
    """1234.56.78903: a Norwegian account number as banks print it."""
    d = digits(value)
    return "%s.%s.%s" % (d[:4], d[4:6], d[6:]) if len(d) == 11 else str(value or "")


def luhn_ok(d):
    total = 0
    for i, c in enumerate(reversed(d)):
        n = int(c) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def no_kid_ok(value):
    """A KID carries a modulus 10 (Luhn) or modulus 11 check digit, as the payee's agreement says."""
    d = digits(value)
    if not 2 <= len(d) <= 25 or d != str(value).strip().replace(" ", ""):
        return False
    if luhn_ok(d):
        return True
    weights = [2, 3, 4, 5, 6, 7]
    s = sum(int(c) * weights[i % 6] for i, c in enumerate(reversed(d[:-1])))
    check = 11 - s % 11
    check = 0 if check == 11 else check
    return (d[-1] == "-" if check == 10 else check == int(d[-1]))


# ---- Denmark -----------------------------------------------------------------------------------

def dk_cvr_ok(value):
    d = digits(value)
    return len(d) == 8 and d[0] != "0"


def dk_cvr_mod11(value):
    d = digits(value)
    return len(d) == 8 and sum(int(c) * w for c, w in zip(d, (2, 7, 6, 5, 4, 3, 2, 1))) % 11 == 0


# ---- Finland -----------------------------------------------------------------------------------

def fi_ytunnus_ok(value):
    m = re.fullmatch(r"(\d{7})-(\d)", str(value or "").strip())
    if not m:
        return False
    s = sum(int(c) * w for c, w in zip(m.group(1), (7, 9, 10, 5, 8, 4, 2)))
    r = s % 11
    if r == 1:
        return False
    return (0 if r == 0 else 11 - r) == int(m.group(2))


def fi_vat_of(ytunnus):
    """FI12345671: the VAT identifier is FI and the Y-tunnus without its hyphen."""
    return "FI" + digits(ytunnus)


def fi_reference_check(base):
    base = digits(base)
    s = sum(int(c) * (7, 3, 1)[i % 3] for i, c in enumerate(reversed(base)))
    return (10 - s % 10) % 10


def fi_reference_ok(value):
    d = digits(value)
    if str(value or "").strip().upper().startswith("RF"):
        return rf_reference_ok(value)
    return 4 <= len(d) <= 20 and fi_reference_check(d[:-1]) == int(d[-1])


def fi_reference_text(value):
    """1 23453: a Finnish reference in groups of five from the right, as banks print it."""
    raw = str(value or "").strip()
    if raw.upper().startswith("RF"):
        r = raw.replace(" ", "").upper()
        return " ".join(r[i:i + 4] for i in range(0, len(r), 4))
    d = digits(raw)
    groups = []
    while d:
        groups.insert(0, d[-5:])
        d = d[:-5]
    return " ".join(groups)


def rf_reference_ok(value):
    """ISO 11649 creditor reference: RF, two check digits, up to 21 characters, modulus 97."""
    r = str(value or "").replace(" ", "").upper()
    if not re.fullmatch(r"RF\d\d[0-9A-Z]{1,21}", r):
        return False
    moved = r[4:] + r[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


def fi_virtual_barcode(iban, amount, reference, due):
    """The bank barcode version 4 (Finanssiala, Pankkiviivakoodi): 4, the 16 digits of a Finnish IBAN,
    euros in six digits, cents in two, 000, the reference in twenty digits and the due date as YYMMDD.
    None when the parts are not there or will not fit (an RF reference is version 5, not written here)."""
    i = str(iban or "").replace(" ", "").upper()
    ref = digits(reference)
    if not (i.startswith("FI") and len(i) == 18 and ref and len(ref) <= 20) \
            or str(reference).strip().upper().startswith("RF"):
        return None
    cents = int(round(float(amount) * 100))
    if cents < 0 or cents >= 100000000:
        return None
    euros, cents = divmod(cents, 100)
    d = re.fullmatch(r"\d{2}(\d{2})-(\d{2})-(\d{2})", str(due or ""))
    date = "".join(d.groups()) if d else "000000"
    return "4" + i[2:] + "%06d%02d" % (euros, cents) + "000" + ref.rjust(20, "0") + date


# ---- United Kingdom ----------------------------------------------------------------------------

def gb_vat_ok(value):
    """A UK VAT registration number: GB and nine digits whose weighted sum (8..2) plus the last two
    digits is a multiple of 97, or is after adding 55 (the series issued from 2010)."""
    raw = str(value or "").upper().replace(" ", "")
    if raw.startswith("GB"):
        raw = raw[2:]
    if not re.fullmatch(r"\d{9}(\d{3})?", raw):
        return False
    s = sum(int(c) * w for c, w in zip(raw[:7], (8, 7, 6, 5, 4, 3, 2))) + int(raw[7:9])
    return s % 97 == 0 or (s + 55) % 97 == 0


def gb_vat_text(value):
    """GB 123 4567 89: as HMRC prints a VAT registration number."""
    d = digits(value)
    return "GB %s %s %s" % (d[:3], d[3:7], d[7:9]) if len(d) == 9 else str(value or "")


# ---- Australia ---------------------------------------------------------------------------------

def au_abn_ok(value):
    d = digits(value)
    if len(d) != 11 or d[0] == "0":
        return False
    n = [int(c) for c in d]
    n[0] -= 1
    return sum(a * w for a, w in zip(n, (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19))) % 89 == 0


def au_abn_text(value):
    """12 345 678 901: as the Australian Business Register prints an ABN."""
    d = digits(value)
    return "%s %s %s %s" % (d[:2], d[2:5], d[5:8], d[8:]) if len(d) == 11 else str(value or "")


# ---- Canada ------------------------------------------------------------------------------------

CA_GST = re.compile(r"^\s*(\d{9})\s*RT\s*(\d{4})\s*$", re.I)
CA_QST = re.compile(r"^\s*(\d{10})\s*TQ\s*(\d{4})\s*$", re.I)


def ca_gst_ok(value):
    """The GST/HST registration number: the nine-digit business number and the program account RT0001."""
    return bool(CA_GST.match(str(value or "")))


def ca_gst_text(value):
    m = CA_GST.match(str(value or ""))
    return "%s RT%s" % (m.group(1), m.group(2)) if m else str(value or "")


def ca_qst_ok(value):
    return bool(CA_QST.match(str(value or "")))


def ca_qst_text(value):
    m = CA_QST.match(str(value or ""))
    return "%s TQ%s" % (m.group(1), m.group(2)) if m else str(value or "")


# ---- Belgium -----------------------------------------------------------------------------------

def be_enterprise_ok(value):
    """The enterprise number: ten digits, the first 0 or 1, the last two 97 - (first eight mod 97). BE and
    the ten digits is the VAT number; a nine-digit number from before 2005 takes a leading 0."""
    d = digits(value)
    if len(d) == 9:
        d = "0" + d
    return len(d) == 10 and d[0] in "01" and 97 - int(d[:8]) % 97 == int(d[8:])


def be_enterprise_digits(value):
    d = digits(value)
    return "0" + d if len(d) == 9 else d


def be_enterprise_text(value):
    """0123.456.749: as the Crossroads Bank for Enterprises prints it."""
    d = be_enterprise_digits(value)
    return "%s.%s.%s" % (d[:4], d[4:7], d[7:]) if len(d) == 10 else str(value or "")


def be_vat_text(value):
    """BE 0123.456.749."""
    d = be_enterprise_digits(value)
    return "BE " + be_enterprise_text(d) if len(d) == 10 else str(value or "")


def be_ogm_ok(value):
    """The structured communication +++123/4567/89012+++: twelve digits, the last two the first ten modulo
    97, 97 when that is 0."""
    d = digits(value)
    if len(d) != 12:
        return False
    return (int(d[:10]) % 97 or 97) == int(d[10:])


def be_ogm_text(value):
    d = digits(value)
    return "+++%s/%s/%s+++" % (d[:3], d[3:7], d[7:]) if len(d) == 12 else str(value or "")


# ---- The Netherlands ---------------------------------------------------------------------------

def nl_vat_ok(value):
    """NL123456782B01: nine digits that pass the eleven test, or a 2020 btw-id that passes modulus 97."""
    r = str(value or "").upper().replace(" ", "").replace(".", "")
    m = re.fullmatch(r"NL(\d{9})B(\d{2})", r)
    if not m:
        return False
    d = m.group(1)
    s = sum(int(c) * w for c, w in zip(d[:8], (9, 8, 7, 6, 5, 4, 3, 2)))
    if s % 11 != 10 and s % 11 == int(d[8]):
        return True
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1


def nl_kvk_ok(value):
    return len(digits(value)) == 8 and digits(value) == str(value or "").strip().replace(" ", "")


# ---- Austria -----------------------------------------------------------------------------------

def at_uid_ok(value):
    """ATU and eight digits C2..C9 whose last is the ministry's check digit: the digits in the even places
    (C3, C5, C7) doubled and their digits summed, the others as they are, and C9 = (10 - (sum + 4) mod 10)
    mod 10 (BMF, Konstruktionsregeln der UID, November 2020)."""
    r = str(value or "").upper().replace(" ", "")
    m = re.fullmatch(r"ATU(\d{8})", r)
    if not m:
        return False
    d = m.group(1)
    s = 0
    for i, c in enumerate(d[:7]):
        v = int(c) * (2 if i % 2 else 1)
        s += v // 10 + v % 10
    return (10 - (s + 4) % 10) % 10 == int(d[7])


AT_FN = re.compile(r"^\s*(?:FN\s*)?(\d{1,6})\s*([a-z])\s*$", re.I)


def at_fn_ok(value):
    return bool(AT_FN.match(str(value or "")))


def at_fn_text(value):
    m = AT_FN.match(str(value or ""))
    return "FN %s%s" % (m.group(1), m.group(2).lower()) if m else str(value or "")


# ---- Ireland -----------------------------------------------------------------------------------

def ie_vat_form(value):
    """IE and seven digits and one or two letters, or the old form, a digit, a letter or + or *, five digits
    and a letter (the forms VIES lists for Ireland)."""
    r = str(value or "").upper().replace(" ", "")
    return bool(re.fullmatch(r"IE(\d{7}[A-W][A-IW]?|\d[A-Z+*]\d{5}[A-W])", r))


def ie_vat_ok(value):
    """IE1234567T or IE1234567WH: seven digits, a check letter and, from 2013, a second letter."""
    r = str(value or "").upper().replace(" ", "")
    if r.startswith("IE"):
        r = r[2:]
    m = re.fullmatch(r"(\d{7})([A-W])([A-IW]?)", r)
    if not m:
        return False
    d, check, second = m.groups()
    s = sum(int(c) * w for c, w in zip(d, (8, 7, 6, 5, 4, 3, 2)))
    if second:
        s += "WABCDEFGHI".index(second) * 9
    return "WABCDEFGHIJKLMNOPQRSTUV"[s % 23] == check


# ---- Belgium: the language of a seller's region ------------------------------------------------

def be_region_locale(postcode):
    """The page language a Belgian seller's own region writes in, read off its postcode (bpost's ranges):
    Dutch in Flanders (1500-3999, 8000-9999), French in Wallonia (1300-1499, 4000-7999) and German in the
    German-speaking Community (4700-4799); Brussels (1000-1299) writes French or Dutch, and gets French
    unless the order names Dutch. (locale, region)."""
    d = digits(postcode)
    n = int(d) if len(d) == 4 else 0
    if 1000 <= n <= 1299:
        return "fr-BE", "Brussels"
    if 4700 <= n <= 4799:
        return "de-BE", "the German-speaking Community"
    if 1300 <= n <= 1499 or 4000 <= n <= 7999:
        return "fr-BE", "Wallonia"
    if 1500 <= n <= 3999 or 8000 <= n <= 9999:
        return "nl-BE", "Flanders"
    return "nl-BE", "no Belgian postcode"


# Flanders: Dutch at home. The decree of 19 July 1973 on the use of languages (art. 2, 5 § 1) makes Dutch
# the language of the legally required documents of a firm with a place of business in the Dutch language
# area; art. 5 § 2/1 (decree of 7 July 2017, in force 11 August 2017) lets an invoice carry a second valid
# version in an official language of the EU or EEA that all parties understand, only when the customer is
# established in another EU or EEA state.

def be_dutch_at_home(seller, buyer, named):
    """True when a seller in Flanders is asked for another language than Dutch for a customer in Belgium (or
    one whose country the order does not give): the page stays Dutch."""
    seller, buyer = seller or {}, buyer or {}
    if str(seller.get("country") or "").strip().upper() != "BE":
        return False
    if not named or str(named).strip().lower().split("-")[0] == "nl":
        return False
    if be_region_locale(seller.get("postcode"))[1] != "Flanders":
        return False
    return str(buyer.get("country") or "").strip().upper() in ("", "BE")


# ---- wave 9: Spain, Italy, Poland ---------------------------------------------------------------
# What each state publishes is the form of the number, and the form is what the build refuses on. The
# check characters below are the ones in common use; none of the three formulas was read from an official
# text, so a mismatch warns and never refuses.
#
#   Spain    the NIF, nine characters. A natural person: the eight digits of the DNI and its letter (Real
#            Decreto 1065/2007 art. 19), or the NIE, X, Y or Z, seven digits and a letter (art. 20), or K, L
#            or M, seven characters and a letter. An entity: a letter for its legal form, seven digits and a
#            control character (Orden EHA/451/2008 art. 2 and 3: A sociedad anónima, B sociedad de
#            responsabilidad limitada ... N a foreign entity, W a permanent establishment). In common use:
#            the DNI number modulo 23 read in TRWAGMYFPDXBNJZSQVHLCKE; for an entity the digits in the
#            even places plus the digits of twice each digit in the odd places, the control ten less the
#            last digit of that sum, written as a digit or as a letter of JABCDEFGHI.
#   Italy    the partita IVA, eleven digits (IT before them as a VAT number). In common use: the last is
#            a Luhn check digit. A person without one gives the codice fiscale, sixteen characters.
#   Poland   the NIP, ten digits in the form the Ministry's own FA(3) schema accepts (TNrNIP:
#            [1-9]((\d[1-9])|([1-9]\d))\d{7}). In common use: the weights 6 5 7 2 3 4 5 6 7 over the first
#            nine, modulo 11, give the tenth.

ES_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
ES_ENTITY_LETTERS = "ABCDEFGHJNPQRSUVW"


def es_nif(value):
    """The NIF as nine characters: spaces, points and hyphens out, ES off the front."""
    r = re.sub(r"[\s.\-]", "", str(value or "")).upper()
    return r[2:] if r.startswith("ES") and len(r) == 11 else r


def es_nif_form(value):
    r = es_nif(value)
    return bool(re.fullmatch(r"\d{8}[A-Z]|[XYZ]\d{7}[A-Z]|[KLM][0-9A-Z]{7}[A-Z]|[%s]\d{7}[0-9A-J]" % ES_ENTITY_LETTERS, r))


def es_nif_person(value):
    """True for a natural person's NIF (DNI, NIE, K, L, M), False for an entity's."""
    return es_nif(value)[:1] not in ES_ENTITY_LETTERS


def es_nif_ok(value):
    """The check character in common use holds (see the note above: not read from an official text)."""
    r = es_nif(value)
    if not es_nif_form(r):
        return False
    if re.fullmatch(r"\d{8}[A-Z]", r):
        return ES_DNI_LETTERS[int(r[:8]) % 23] == r[8]
    if r[0] in "XYZ":
        return ES_DNI_LETTERS[int(str("XYZ".index(r[0])) + r[1:8]) % 23] == r[8]
    if r[0] in "KLM":
        return True if not r[1:8].isdigit() else ES_DNI_LETTERS[int(r[1:8]) % 23] == r[8]
    d = r[1:8]
    total = sum(int(c) for c in d[1::2]) + sum(sum(divmod(int(c) * 2, 10)) for c in d[0::2])
    control = (10 - total % 10) % 10
    return r[8] in (str(control), "JABCDEFGHI"[control])


def it_piva(value):
    """The eleven digits of a partita IVA, IT off the front."""
    r = re.sub(r"[\s.\-]", "", str(value or "")).upper()
    return r[2:] if r.startswith("IT") else r


def it_piva_form(value):
    return bool(re.fullmatch(r"\d{11}", it_piva(value)))


def it_piva_ok(value):
    d = it_piva(value)
    return it_piva_form(d) and luhn_ok(d)


def it_cf_form(value):
    """A codice fiscale: sixteen characters for a person, eleven digits for an entity."""
    r = re.sub(r"\s", "", str(value or "")).upper()
    return bool(re.fullmatch(r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-EHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]|\d{11}", r))


def pl_nip(value):
    """The ten digits of a NIP: hyphens and spaces out, PL off the front."""
    r = re.sub(r"[\s\-]", "", str(value or "")).upper()
    return r[2:] if r.startswith("PL") else r


def pl_nip_form(value):
    return bool(re.fullmatch(r"[1-9]((\d[1-9])|([1-9]\d))\d{7}", pl_nip(value)))


def pl_nip_ok(value):
    d = pl_nip(value)
    if not re.fullmatch(r"\d{10}", d):
        return False
    check = sum(int(c) * w for c, w in zip(d[:9], (6, 5, 7, 2, 3, 4, 5, 6, 7))) % 11
    return check != 10 and check == int(d[9])


def pl_nip_text(value):
    """123-456-32-18: the way a Polish invoice prints a NIP."""
    d = pl_nip(value)
    return "%s-%s-%s-%s" % (d[:3], d[3:6], d[6:8], d[8:]) if len(d) == 10 else str(value or "")


# ---- IBAN ---------------------------------------------------------------------------------------

def iban_ok(value):
    r = str(value or "").replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", r):
        return False
    moved = r[4:] + r[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


def iban_text(value):
    r = str(value or "").replace(" ", "").upper()
    return " ".join(r[i:i + 4] for i in range(0, len(r), 4))


# ---- Sweden ------------------------------------------------------------------------------------

def se_bankgiro_ok(value):
    """A Bankgiro number: seven or eight digits, the last a modulus 10 (Luhn) check digit (Bankgirot)."""
    d = digits(value)
    return len(d) in (7, 8) and luhn_ok(d)


def se_plusgiro_ok(value):
    """A PlusGiro number: two to eight digits, the last a modulus 10 (Luhn) check digit."""
    d = digits(value)
    return 2 <= len(d) <= 8 and luhn_ok(d)


def se_bankgiro_text(value):
    """123-4567 or 1234-5678: a Bankgiro number as Bankgirot prints it."""
    d = digits(value)
    return "%s-%s" % (d[:-4], d[-4:]) if len(d) in (7, 8) else str(value or "")


def se_plusgiro_text(value):
    """123456-7: a PlusGiro number with its check digit after a hyphen."""
    d = digits(value)
    return "%s-%s" % (d[:-1], d[-1]) if len(d) >= 2 else str(value or "")
