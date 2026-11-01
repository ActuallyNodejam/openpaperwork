#!/usr/bin/env python3
"""The e-invoice as a file other systems take in: the Factur-X PDF and the official validators.

  EINV-FACTURX  The PDF is a Factur-X / ZUGFeRD 2 invoice: it carries the invoice XML as an embedded
                file named factur-x.xml (xrechnung.xml for the XRECHNUNG profile), listed in the
                catalog's /AF with an AFRelationship, and XMP that declares PDF/A-3 and the Factur-X
                DocumentType, DocumentFileName, Version and ConformanceLevel; the level is the profile
                the XML's guideline ID (BT-24) names, and the embedded XML is the XML beside the PDF.
  EINV-PDFA     veraPDF (run untouched as an external program; it is GPL/MPL and none of it is here)
                finds the PDF compliant with PDF/A-3B.
  EINV-KOSIT    The official KoSIT validator (github.com/itplr-kosit/validator, Apache-2.0) with the
                KoSIT XRechnung configuration accepts the XML: the XRechnung scenario when the XML
                names XRechnung, the EN 16931 (CII) scenario otherwise.
  EINV-FR-CTC   For a French seller, the same validator with the French rules of FNFE-MPE France_RFE
                (Apache-2.0, AFNOR XP Z12-012 BR-FR) and the EN 16931 schematron accepts the XML. The
                scenario file is skills/e-invoice/validators/fr-ctc-scenarios.xml.
  EINV-PEPPOL   For a UBL invoice or credit note, the same validator with OpenPeppol's Peppol BIS Billing
                3.0 rules (release 3.0.21, mandatory from 2026-08-17: CEN-EN16931-UBL and PEPPOL-EN16931-UBL
                with the Norwegian NO-R, Danish DK-R and Dutch NL-R rules) accepts it. OpenPeppol's terms allow no copy, so the
                rules are fetched and compiled to XSLT on install (SchXslt 1.10.1, MIT) and run untouched;
                the scenario is skills/e-invoice/validators/peppol-scenarios.xml.
  EINV-FINVOICE For a Finvoice 3.0 message, the same validator with Finanssiala's Finvoice3.0.xsd accepts
                it (skills/e-invoice/validators/finvoice-scenarios.xml).
  EINV-SI-UBL   For an SI-UBL 2.0 (NLCIUS) invoice or credit note, the same validator with the Nederlandse
                Peppol Autoriteit's si-ubl-2.0.xsl (2.0.3.13, MIT; the EN 16931 rules in it EUPL-1.2, run
                untouched) accepts it (skills/e-invoice/validators/siubl-scenarios.xml).
  EINV-EBINTERFACE  For an ebInterface 6.1 invoice, the same validator with AUSTRIAPRO's Invoice.xsd accepts
                it (skills/e-invoice/validators/ebinterface-scenarios.xml).
  EINV-FACTURAE For a Spanish Facturae 3.2.2 file, the same validator with the schema facturae.gob.es
                publishes (Facturaev3_2_2.xml) accepts it (skills/e-invoice/validators/facturae-scenarios.xml).
                The schema allows a file without a signature; no entry point does, and the rule says so.
  EINV-FATTURAPA  For an Italian FatturaPA file (FPR12 or FPA12), the same validator with schema 1.2.3 of
                fatturapa.gov.it accepts it (skills/e-invoice/validators/fatturapa-scenarios.xml).
  EINV-KSEF     For a Polish structured invoice, the same validator with the Ministry of Finance's logical
                structure FA(3) accepts it (skills/e-invoice/validators/ksef-scenarios.xml).

check(rule_id, path, case, stage) -> (passed, evidence). A validator that is not installed is not a
fail: the rule answers "could not run" and names how to install it, and the pack check prints it
as SKIP. Installed by skills/e-invoice/scripts/fetch_validators.py into ~/.cache/nodejam/einvoice-tools
(or FILETASK_EINVOICE_TOOLS); FILETASK_KOSIT_JAR, FILETASK_KOSIT_CONFIG and FILETASK_FNFE_RFE name each
part, FILETASK_VERAPDF a verapdf program and FILETASK_VERAPDF_IMAGE a veraPDF container image. Java
runs from PATH, or in the container image FILETASK_JAVA_IMAGE (default eclipse-temurin:21-jre) with
no network and read-only mounts.

These say whether a file passes published validators; none of them says the invoice is right for
the person, or lawful.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
RSM = "{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}"
FX_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
XRECHNUNG_ID = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
PROFILES = {XRECHNUNG_ID: ("XRECHNUNG", "xrechnung.xml"),
            "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended": ("EXTENDED", "factur-x.xml"),
            "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic": ("BASIC", "factur-x.xml"),
            "urn:factur-x.eu:1p0:basicwl": ("BASIC WL", "factur-x.xml"),
            "urn:factur-x.eu:1p0:minimum": ("MINIMUM", "factur-x.xml"),
            "urn:cen.eu:en16931:2017": ("EN 16931", "factur-x.xml")}
INSTALL = "python3 skills/e-invoice/scripts/fetch_validators.py"
RULES = ("EINV-FACTURX", "EINV-PDFA", "EINV-KOSIT", "EINV-FR-CTC", "EINV-PEPPOL", "EINV-FINVOICE", "EINV-SI-UBL",
         "EINV-EBINTERFACE", "EINV-FACTURAE", "EINV-FATTURAPA", "EINV-KSEF")
NLCIUS = "urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0"
EBI_NS = "{http://www.ebinterface.at/schema/6p1/}"
PEPPOL_VERSION = "3.0.21"
# The XML that travels beside the page rather than inside a Factur-X PDF, by syntax.
BESIDE = {"ubl": "Peppol UBL", "finvoice": "Finvoice", "si-ubl": "SI-UBL 2.0", "ebinterface": "ebInterface 6.1",
          "facturae": "Facturae 3.2.2", "fatturapa": "FatturaPA 1.2.3", "ksef": "KSeF FA(3)"}
# Wave 9: the root element of each national file, and for each rule the syntax it reads, its scenario file,
# the folder the schema is installed in (with the file that must be there and the variable that names
# another place), the name the scenario mounts it under, what to call it, and any option java needs.
NATIONAL_ROOTS = {"{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae": "facturae",
                  "{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronica": "fatturapa",
                  "{http://crd.gov.pl/wzor/2025/06/25/13775/}Faktura": "ksef"}
NATIONAL = {
    "EINV-FACTURAE": ("facturae", "facturae-scenarios.xml", "facturae-3.2.2", "Facturaev3_2_2.xml",
                      "FILETASK_FACTURAE_XSD", "facturae", "Facturae 3.2.2 schema", ()),
    "EINV-FATTURAPA": ("fatturapa", "fatturapa-scenarios.xml", "fatturapa-1.2.3", "Schema_VFPR12_v1.2.3.xsd",
                       "FILETASK_FATTURAPA_XSD", "fatturapa", "FatturaPA 1.2.3 schema", ()),
    # FA(3) counts up to 10 000 lines and 50 000 corrected invoices, and java expands every counted
    # occurrence: about ten minutes a file. The pack check loads the installed copy whose counts above 100
    # are unbounded (offline/); FILETASK_KSEF_STRICT=1 loads the copy with the counts as published (strict/).
    "EINV-KSEF": ("ksef", "ksef-scenarios.xml", "ksef-fa3", "offline/schemat.xsd", "FILETASK_KSEF_XSD", "ksef",
                  "KSeF FA(3) schema", ()),
}
UBL_ROOTS = ("{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice",
             "{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote")


# ---- where things are -------------------------------------------------------------------------

def tools_dir():
    return Path(os.environ.get("FILETASK_EINVOICE_TOOLS") or Path.home() / ".cache" / "nodejam" / "einvoice-tools")


def kosit_parts():
    """(jar, XRechnung configuration dir, France_RFE dir), each None when absent."""
    t = tools_dir()
    jar = os.environ.get("FILETASK_KOSIT_JAR")
    jar = Path(jar) if jar else next(iter(sorted(t.glob("validator-*-standalone.jar"))), None)
    config = Path(os.environ.get("FILETASK_KOSIT_CONFIG") or t / "xrechnung-config")
    fnfe = Path(os.environ.get("FILETASK_FNFE_RFE") or t / "france-rfe")
    return (jar if jar and jar.is_file() else None,
            config if (config / "scenarios.xml").is_file() else None,
            fnfe if (fnfe / "FNFE_RFE_INVOICE").is_dir() else None)


def java_runner():
    """How to run java: ("local", None), ("docker", image), or None."""
    if shutil.which("java"):
        return "local", None
    if shutil.which("docker"):
        return "docker", os.environ.get("FILETASK_JAVA_IMAGE", "eclipse-temurin:21-jre")
    return None


def peppol_parts():
    """(compiled Peppol rules dir, Finvoice schema dir), each None when absent."""
    t = tools_dir()
    peppol = Path(os.environ.get("FILETASK_PEPPOL_RULES") or t / ("peppol-" + PEPPOL_VERSION))
    finvoice = Path(os.environ.get("FILETASK_FINVOICE_XSD") or t / "finvoice")
    return (peppol if (peppol / "PEPPOL-EN16931-UBL.xsl").is_file() and (peppol / "CEN-EN16931-UBL.xsl").is_file() else None,
            finvoice if (finvoice / "Finvoice3.0.xsd").is_file() else None)


def w8_parts():
    """(SI-UBL 2.0 xsl dir, ebInterface 6.1 schema dir), each None when absent."""
    t = tools_dir()
    siubl = Path(os.environ.get("FILETASK_SIUBL") or t / "si-ubl-2.0")
    ebi = Path(os.environ.get("FILETASK_EBINTERFACE_XSD") or t / "ebinterface-6.1")
    return (siubl if (siubl / "si-ubl-2.0.xsl").is_file() else None,
            ebi if (ebi / "Invoice.xsd").is_file() else None)


def page_only(pdf):
    """True when the order beside the page is a seller's in a country whose invoices are pages only, or
    says "syntax": "none"."""
    for p in sorted(Path(pdf).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("seller"), dict) and data.get("lines"):
            sys.path.insert(0, str(HERE))
            import einvoice_particulars
            return str(data.get("syntax") or "").lower() == "none" or \
                str(data["seller"].get("country") or "").upper() in ("AU", "CA", "US", "NZ") or \
                bool(einvoice_particulars.blocked_keys(data))
    return False


def syntax_of_xml(data):
    """cii, ubl, finvoice or '' for the XML's root element."""
    try:
        tag = ET.fromstring(data).tag
    except (ET.ParseError, TypeError):
        return ""
    if tag == RSM + "CrossIndustryInvoice":
        return "cii"
    if tag in UBL_ROOTS:
        found = re.search(rb"<(?:\w+:)?CustomizationID>\s*([^<]+?)\s*</", data)
        if found and found.group(1).decode("utf-8", "ignore").startswith(NLCIUS):
            return "si-ubl"
        return "ubl"
    if tag == EBI_NS + "Invoice":
        return "ebinterface"
    if tag in NATIONAL_ROOTS:
        return NATIONAL_ROOTS[tag]
    return "finvoice" if tag == "Finvoice" else ""


def pdf_and_xml(path):
    """(pdf, xml) for an output: the PDF and the XML of the same name beside it."""
    path = Path(path)
    pdf = path if path.suffix.lower() == ".pdf" else path.with_suffix(".pdf")
    xml = path if path.suffix.lower() == ".xml" else path.with_suffix(".xml")
    return (pdf if pdf.is_file() else None), (xml if xml.is_file() else None)


def embedded_files(pdf):
    """{name: bytes} of the PDF's embedded files, read with poppler's pdfdetach."""
    out = {}
    listing = subprocess.run(["pdfdetach", "-list", str(pdf)], capture_output=True, text=True)
    if listing.returncode != 0:
        return out
    names = re.findall(r"^\s*(\d+):\s*(.+?)\s*$", listing.stdout, re.M)
    work = Path(tempfile.mkdtemp(prefix="einv-fx-"))
    try:
        for number, name in names:
            target = work / ("f%s" % number)
            subprocess.run(["pdfdetach", "-save", number, "-o", str(target), str(pdf)], capture_output=True)
            if target.is_file():
                out[name] = target.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out


def xmp_of(pdf):
    return subprocess.run(["pdfinfo", "-meta", str(pdf)], capture_output=True, text=True).stdout


def relationships(pdf):
    """The AFRelationship of each file specification, read with pypdf when it is there, else from the
    file's bytes (pypdf writes the catalog and file specifications as plain objects)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf))
        root = reader.trailer["/Root"]
        found = {}
        for spec in root.get("/AF") or []:
            spec = spec.get_object()
            found[str(spec.get("/UF") or spec.get("/F"))] = str(spec.get("/AFRelationship") or "")
        return found
    except ImportError:
        raw = Path(pdf).read_bytes()
        return {"?": m.decode() for m in re.findall(rb"/AFRelationship\s*/(\w+)", raw)}
    except Exception:
        return {}


def guideline(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    if root.tag != RSM + "CrossIndustryInvoice":
        return None
    node = root.find("{*}ExchangedDocumentContext/{*}GuidelineSpecifiedDocumentContextParameter/{*}ID")
    return (node.text or "").strip() if node is not None else ""


def seller_country(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    node = root.find(".//{*}SellerTradeParty/{*}PostalTradeAddress/{*}CountryID")
    return (node.text or "").strip().upper() if node is not None else ""


# ---- the rules --------------------------------------------------------------------------------

def facturx(path):
    pdf, xml = pdf_and_xml(path)
    if pdf is None:
        return None, "no PDF to read"
    if xml is not None and syntax_of_xml(xml.read_bytes()) in BESIDE:
        return None, ("%s is %s, which travels as XML beside the page, not inside a Factur-X PDF"
                      % (xml.name, BESIDE[syntax_of_xml(xml.read_bytes())]))
    if xml is None and page_only(pdf):
        return None, "a page-only invoice (Australia, Canada, the United States): no EN 16931 XML applies"
    files = embedded_files(pdf)
    invoices = {name: data for name, data in files.items() if guideline(data) is not None}
    if not invoices:
        return False, ("%s carries no invoice XML inside it; build the page with build_page.py, which "
                       "writes the Factur-X PDF" % pdf.name)
    if len(invoices) > 1:
        return False, "%s carries %d invoice XMLs (%s); Factur-X has one" % (pdf.name, len(invoices), ", ".join(invoices))
    name, data = next(iter(invoices.items()))
    problems = []
    gid = guideline(data)
    level, want_name = PROFILES.get(gid, (None, None))
    if level is None:
        problems.append("the embedded XML's guideline ID (BT-24) %r is no Factur-X or ZUGFeRD profile" % gid)
    elif name != want_name:
        problems.append("the XML is embedded as %s; the %s profile names it %s" % (name, level, want_name))
    rel = relationships(pdf)
    if not rel:
        problems.append("no /AF entry with an AFRelationship for the XML (PDF/A-3 clause 6.8)")
    elif not any(v.strip("/") in ("Data", "Alternative", "Source") for v in rel.values()):
        problems.append("AFRelationship is %s; Factur-X takes Data, Alternative or Source" % ", ".join(rel.values()))
    meta = xmp_of(pdf)
    if not re.search(r"pdfaid:part[^>]*>\s*3\s*<|pdfaid:part=\"3\"", meta):
        problems.append("the XMP does not declare PDF/A-3 (pdfaid:part 3)")
    if FX_NS not in meta:
        problems.append("the XMP has no Factur-X extension schema (%s)" % FX_NS)
    got = dict(re.findall(r"<fx:(DocumentType|DocumentFileName|Version|ConformanceLevel)>\s*([^<]*?)\s*</fx:", meta))
    if level and got.get("ConformanceLevel") != level:
        problems.append("fx:ConformanceLevel is %r and the XML is %s" % (got.get("ConformanceLevel"), level))
    if got.get("DocumentFileName") != name:
        problems.append("fx:DocumentFileName is %r and the file inside is %s" % (got.get("DocumentFileName"), name))
    if got.get("DocumentType") != "INVOICE":
        problems.append("fx:DocumentType is %r, not INVOICE" % got.get("DocumentType"))
    if xml is not None and xml.read_bytes().strip() != data.strip():
        problems.append("the XML inside the PDF is not the %s beside it; build both from one source" % xml.name)
    return (not problems, "; ".join(problems) or "Factur-X %s: %s inside, PDF/A-3 declared%s"
            % (level, name, ", the same as %s" % xml.name if xml is not None else ""))


def pdfa(path):
    pdf, xml = pdf_and_xml(path)
    if pdf is None:
        return None, "no PDF to validate"
    if (xml is not None and syntax_of_xml(xml.read_bytes()) in BESIDE) or \
            (xml is None and not any(guideline(d) is not None for d in embedded_files(pdf).values())):
        return None, "a readable page with no invoice XML inside; PDF/A-3 is asked of a Factur-X PDF"
    tool = os.environ.get("FILETASK_VERAPDF") or shutil.which("verapdf")
    image = os.environ.get("FILETASK_VERAPDF_IMAGE")
    work = None
    try:
        if tool:
            cmd = [tool, "--flavour", "3b", "--format", "xml", str(pdf)]
        elif image and shutil.which("docker"):
            work = Path(tempfile.mkdtemp(prefix="einv-pdfa-"))
            shutil.copyfile(pdf, work / "invoice.pdf")
            os.chmod(work, 0o755)
            os.chmod(work / "invoice.pdf", 0o644)
            cmd = ["docker", "run", "--rm", "--network", "none", "-v", "%s:/data:ro" % work, image,
                   "--flavour", "3b", "--format", "xml", "/data/invoice.pdf"]
        else:
            return False, ("could not run: veraPDF is not installed (put verapdf on PATH, or set "
                           "FILETASK_VERAPDF or FILETASK_VERAPDF_IMAGE)")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        verdict = re.search(r'<validationReport[^>]*isCompliant="(true|false)"', p.stdout)
        if not verdict:
            return False, "could not read veraPDF's report: %s" % (p.stderr or p.stdout)[-160:].strip()
        if verdict.group(1) == "true":
            return True, "veraPDF: compliant with PDF/A-3B"
        failed = re.findall(r'<rule [^>]*clause="([^"]+)"[^>]*testNumber="([^"]+)"[^>]*status="failed"[^>]*>\s*'
                            r'<description>(.*?)</description>', p.stdout, re.S)
        return False, "veraPDF: not PDF/A-3B; " + "; ".join(
            "%s-%s %s" % (c, n, re.sub(r"\s+", " ", d)[:110]) for c, n, d in failed[:4])
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)


def xml_bytes_for(path):
    """The XML the validators read: the one beside the output, else the one inside the PDF."""
    pdf, xml = pdf_and_xml(path)
    if xml is not None:
        return xml.read_bytes()
    if pdf is not None:
        for data in embedded_files(pdf).values():
            if guideline(data) is not None:
                return data
    return None


def kosit_run(xml_bytes, scenarios, repository_mounts, java_opts=(), timeout=600):
    """Run the KoSIT validator on one XML. scenarios: (host dir, file name); repository_mounts:
    {name under the repository root: host dir}, or {"": dir} for a configuration that is its own root.
    Returns (accepted, scenario name, [(level, code, text)]) or raises RuntimeError."""
    jar, _config, _fnfe = kosit_parts()
    runner = java_runner()
    if runner is None:
        raise RuntimeError("no java and no docker to run it")
    work = Path(tempfile.mkdtemp(prefix="einv-kosit-"))
    try:
        (work / "in").mkdir()
        (work / "out").mkdir()
        (work / "in" / "invoice.xml").write_bytes(xml_bytes)
        for d in (work, work / "in", work / "out"):
            os.chmod(d, 0o777)
        os.chmod(work / "in" / "invoice.xml", 0o644)
        scen_dir, scen_file = scenarios
        if runner[0] == "local":
            repo = repository_mounts.get("")
            if repo is None:
                repo = work / "repo"
                repo.mkdir()
                for name, host in repository_mounts.items():
                    (repo / name).symlink_to(Path(host).resolve())
            cmd = ["java", *java_opts, "-jar", str(jar), "-s", str(Path(scen_dir) / scen_file), "-r", str(repo),
                   "-o", str(work / "out"), str(work / "in" / "invoice.xml")]
        else:
            mounts = ["-v", "%s:/tools/validator.jar:ro" % Path(jar).resolve(), "-v", "%s:/scen:ro" % Path(scen_dir).resolve(),
                      "-v", "%s:/data" % work]
            for name, host in repository_mounts.items():
                mounts += ["-v", "%s:/repo/%s:ro" % (Path(host).resolve(), name) if name else "%s:/repo:ro" % Path(host).resolve()]
            cmd = ["docker", "run", "--rm", "--network", "none", "--user", "%d:%d" % (os.getuid(), os.getgid())] + mounts + [
                runner[1], "java", *java_opts, "-jar", "/tools/validator.jar", "-s", "/scen/%s" % scen_file, "-r", "/repo",
                "-o", "/data/out", "/data/in/invoice.xml"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        reports = list((work / "out").glob("*-report.xml"))
        if not reports:
            raise RuntimeError("the validator wrote no report (%s)" % (p.stderr or p.stdout)[-200:].strip())
        report = reports[0].read_text(errors="replace")
        accepted = "<rep:accept" in report
        scenario = re.search(r"<rep:scenarioMatched>.*?<s:name>(.*?)</s:name>", report, re.S)
        messages = [(lv, code, re.sub(r"\s+", " ", text).strip())
                    for lv, code, text in re.findall(r'<rep:message[^>]*level="(error|warning)"[^>]*code="([^"]*)"[^>]*>([^<]*)',
                                                     report)]
        return accepted, (scenario.group(1) if scenario else "no scenario matched"), messages
    finally:
        shutil.rmtree(work, ignore_errors=True)


def verdict(accepted, scenario, messages, who):
    errors = [m for m in messages if m[0] == "error"]
    warnings = [m for m in messages if m[0] == "warning"]
    if accepted:
        return True, "%s, scenario %s: acceptable%s" % (who, scenario, (", %d warning(s): %s" % (
            len(warnings), "; ".join(text[:120] for _, _, text in warnings[:2]))) if warnings else "")
    shown = errors or warnings
    return False, "%s, scenario %s: rejected; %s" % (who, scenario, "; ".join(text[:160] for _, _, text in shown[:4])
                                                     or "no message in the report")


def kosit(path):
    data = xml_bytes_for(path)
    if data is None:
        return None, "no invoice XML beside the file or inside it"
    if syntax_of_xml(data) in BESIDE:
        return None, ("not a CII invoice; EINV-PEPPOL, EINV-FINVOICE, EINV-SI-UBL, EINV-EBINTERFACE, EINV-FACTURAE, "
                      "EINV-FATTURAPA or EINV-KSEF validates it")
    jar, config, _fnfe = kosit_parts()
    if jar is None or config is None:
        return False, "could not run: the KoSIT validator and its XRechnung configuration are not installed (%s)" % INSTALL
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    try:
        accepted, scenario, messages = kosit_run(data, (config, "scenarios.xml"), {"": config})
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    return verdict(accepted, scenario, messages, "KoSIT validator (%s)" % jar.name)


def fr_ctc(path):
    data = xml_bytes_for(path)
    if data is None:
        return None, "no invoice XML beside the file or inside it"
    if seller_country(data) != "FR":
        return None, "the seller is not French; the French rules do not apply"
    jar, config, fnfe = kosit_parts()
    if jar is None or config is None or fnfe is None:
        return False, ("could not run: the KoSIT validator, its configuration and FNFE-MPE France_RFE are not "
                       "installed (%s)" % INSTALL)
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    scenarios = HERE.parent / "e-invoice" / "validators"
    try:
        accepted, scenario, messages = kosit_run(data, (scenarios, "fr-ctc-scenarios.xml"),
                                                 {"kosit": config, "fnfe": fnfe})
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    return verdict(accepted, scenario, messages, "KoSIT validator with the FNFE-MPE BR-FR rules")


def peppol(path):
    _pdf, xml = pdf_and_xml(path)
    data = xml.read_bytes() if xml is not None else None
    if data is not None and syntax_of_xml(data) == "si-ubl":
        return None, "an SI-UBL 2.0 (NLCIUS) invoice; EINV-SI-UBL validates it"
    if data is None or syntax_of_xml(data) != "ubl":
        return None, "no UBL invoice beside the file; Peppol BIS applies to the UBL the pack writes for Norway, Denmark, Finland, the UK, Belgium, the Netherlands, Austria and Ireland"
    jar, config, _fnfe = kosit_parts()
    rules, _fin = peppol_parts()
    if jar is None or config is None or rules is None:
        return False, ("could not run: the KoSIT validator and the Peppol BIS 3.0 rules are not installed (%s)" % INSTALL)
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    try:
        accepted, scenario, messages = kosit_run(data, (HERE.parent / "e-invoice" / "validators", "peppol-scenarios.xml"),
                                                 {"kosit": config, "peppol": rules})
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    return verdict(accepted, scenario, messages, "KoSIT validator with the Peppol BIS Billing 3.0 rules")


def finvoice(path):
    _pdf, xml = pdf_and_xml(path)
    data = xml.read_bytes() if xml is not None else None
    if data is None or syntax_of_xml(data) != "finvoice":
        return None, "no Finvoice message beside the file"
    jar, config, _fnfe = kosit_parts()
    _rules, schema = peppol_parts()
    if jar is None or config is None or schema is None:
        return False, "could not run: the KoSIT validator and the Finvoice 3.0 schema are not installed (%s)" % INSTALL
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    try:
        accepted, scenario, messages = kosit_run(data, (HERE.parent / "e-invoice" / "validators", "finvoice-scenarios.xml"),
                                                 {"kosit": config, "finvoice": schema})
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    return verdict(accepted, scenario, messages, "KoSIT validator with the Finvoice 3.0 schema")


def w8_run(path, want, scen, mount, label):
    _pdf, xml = pdf_and_xml(path)
    data = xml.read_bytes() if xml is not None else None
    if data is None or syntax_of_xml(data) != want:
        return None, "no %s beside the file" % label
    jar, config, _fnfe = kosit_parts()
    siubl, ebi = w8_parts()
    part = siubl if want == "si-ubl" else ebi
    if jar is None or config is None or part is None:
        return False, "could not run: the KoSIT validator and the %s artefacts are not installed (%s)" % (label, INSTALL)
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    try:
        accepted, scenario, messages = kosit_run(data, (HERE.parent / "e-invoice" / "validators", scen),
                                                 {"kosit": config, mount: part})
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    return verdict(accepted, scenario, messages, "KoSIT validator with the %s" % label)


def national(rule_id, path):
    """Facturae, FatturaPA or FA(3) against its state's own schema."""
    want, scen, folder, must, env, mount, label, java_opts = NATIONAL[rule_id]
    _pdf, xml = pdf_and_xml(path)
    data = xml.read_bytes() if xml is not None else None
    if data is None or syntax_of_xml(data) != want:
        return None, "no %s file beside the page" % BESIDE[want]
    jar, config, _fnfe = kosit_parts()
    part = Path(os.environ.get(env) or tools_dir() / folder)
    if jar is None or config is None or not (part / must).is_file():
        return False, "could not run: the KoSIT validator and the %s are not installed (%s)" % (label, INSTALL)
    if java_runner() is None:
        return False, "could not run: the KoSIT validator needs java or docker, and neither is here"
    timeout = 600
    if want == "ksef":
        strict = bool(os.environ.get("FILETASK_KSEF_STRICT")) and (part / "strict" / "schemat.xsd").is_file()
        part = part / ("strict" if strict else "offline")
        if strict:
            java_opts, timeout, label = ("-Djdk.xml.maxOccurLimit=0",), 2400, label + ", counts as published"
    try:
        accepted, scenario, messages = kosit_run(data, (HERE.parent / "e-invoice" / "validators", scen),
                                                 {"kosit": config, mount: part}, java_opts, timeout)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return False, "could not run the KoSIT validator: %s" % str(e)[:160]
    ok, why = verdict(accepted, scenario, messages, "KoSIT validator with the %s" % label)
    if ok and want == "facturae":
        why += "; the file is unsigned, and FACe takes a Facturae only with an XAdES signature"
    if ok and want != "facturae":
        why += "; the file is not sent to %s" % ("the Sistema di Interscambio" if want == "fatturapa" else "KSeF")
    return ok, why


def check(rule_id, path, case, stage):
    if rule_id in NATIONAL:
        return national(rule_id, path)
    if rule_id == "EINV-PEPPOL":
        return peppol(path)
    if rule_id == "EINV-SI-UBL":
        return w8_run(path, "si-ubl", "siubl-scenarios.xml", "siubl", "SI-UBL 2.0 (NLCIUS) rules")
    if rule_id == "EINV-EBINTERFACE":
        return w8_run(path, "ebinterface", "ebinterface-scenarios.xml", "ebinterface", "ebInterface 6.1 schema")
    if rule_id == "EINV-FINVOICE":
        return finvoice(path)
    if rule_id == "EINV-FACTURX":
        if Path(path).suffix.lower() == ".xml" and not Path(path).with_suffix(".pdf").is_file():
            return None, "an XML on its own; no PDF to carry it"
        return facturx(path)
    if rule_id == "EINV-PDFA":
        return pdfa(path)
    if rule_id == "EINV-KOSIT":
        return kosit(path)
    if rule_id == "EINV-FR-CTC":
        return fr_ctc(path)
    return None, "unknown rule %s" % rule_id


if __name__ == "__main__":
    for rule in RULES:
        ok, why = check(rule, sys.argv[1], {}, "first")
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}, ensure_ascii=False))
