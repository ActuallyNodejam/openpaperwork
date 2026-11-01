#!/usr/bin/env python3
"""Install the official e-invoice validators the pack check runs, at pinned versions.

    python3 fetch_validators.py [--into DIR]

Writes into ~/.cache/nodejam/einvoice-tools (or FILETASK_EINVOICE_TOOLS, or --into):

    validator-1.6.3-standalone.jar   the KoSIT validator, github.com/itplr-kosit/validator (Apache-2.0)
    xrechnung-config/                 its XRechnung 3.0.2 configuration of 2026-08-31, with the CEN
                                      EN 16931 schematron 1.3.16 (Apache-2.0)
    france-rfe/                       FNFE-MPE France_RFE at 97ba0f3d, the BR-FR rules of AFNOR
                                      XP Z12-012 (Apache-2.0)
    peppol-bis-3.0.21/                OpenPeppol's Peppol BIS Billing 3.0, release 3.0.21 (May 2026, mandatory
                                      from 2026-08-17): CEN-EN16931-UBL.sch and PEPPOL-EN16931-UBL.sch as
                                      docs.peppol.eu publishes them, with the national rules (Norway, Denmark,
                                      the Netherlands). No licence is given and the guide forbids modifying or
                                      redistributing it: it is fetched here, run untouched, and nothing of it
                                      is in this repository
    schxslt-1.10.1.jar                SchXslt (MIT), the Schematron compiler that turns the Peppol .sch
                                      files into XSLT, run with the Saxon inside the KoSIT jar
    peppol-3.0.21/                    the compiled CEN-EN16931-UBL.xsl and PEPPOL-EN16931-UBL.xsl
    finvoice/Finvoice3.0.xsd          Finanssiala's Finvoice 3.0 schema of 27.9.2023 ("All materials on
                                      this page are freely usable", finanssiala.fi)
    si-ubl-2.0/si-ubl-2.0.xsl         SI-UBL 2.0 (NLCIUS) 2.0.3.13, the Nederlandse Peppol Autoriteit's
                                      validation artefacts (MIT, Stichting Simplerinvoicing; the CEN EN 16931
                                      rules inside are EUPL-1.2, run untouched)
    ebinterface-6.1/Invoice.xsd       AUSTRIAPRO's ebInterface 6.1 schema (free to implement, no licence
                                      stated: run untouched, not copied)
    facturae-3.2.2/Facturaev3_2_2.xml the Spanish Facturae 3.2.2 schema as facturae.gob.es publishes it (reuse
                                      under Ley 37/2007 with the source named; run untouched, not copied)
    fatturapa-1.2.3/Schema_VFPR12_v1.2.3.xsd
                                      the Italian FatturaPA schema 1.2.3, valid from 1 April 2025, one file
                                      for FPR12 and FPA12 (fatturapa.gov.it reserves all rights in its
                                      contents: run untouched, not copied)
    ksef-fa3/                         the Polish Ministry of Finance's logical structure FA(3) and the three
                                      type files it builds on, from the central repository of electronic
                                      document templates (crd.gov.pl; official documents, prawo autorskie
                                      art. 4), as fetched
    ksef-fa3/strict/                  the same four files with each schemaLocation pointing at the file
                                      beside it instead of at crd.gov.pl, nothing else changed, so the
                                      validator can load them without a network. java expands every counted
                                      occurrence of a schema (FA(3) counts up to 10 000 lines and 50 000
                                      corrected invoices), so one check against this copy takes about ten
                                      minutes; FILETASK_KSEF_STRICT=1 asks the pack check for it
    ksef-fa3/offline/                 the copy the pack check loads by default: as strict/, and every
                                      maxOccurs above 100 written as unbounded, which java checks at once.
                                      An invoice within FA(3)'s own counts gets the same verdict from both

Each download is checked against its SHA-256 before it is kept. The tools run untouched, as separate
programs; nothing of them is copied into this repository. Java 21 runs them (from PATH, or the
eclipse-temurin:21-jre container image). veraPDF, for the PDF/A rule, is installed apart: a verapdf
program on PATH, or the verapdf/cli container image named in FILETASK_VERAPDF_IMAGE.

This fetches from github.com only when someone runs it; the pack never runs it on its own.
"""
import argparse
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

# Where the Polish type files live, and where FA(3) and they look for one another.
KSEF_TYPES = "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/"
# Some state sites answer a plain script with an error page; the request names an ordinary browser.
AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

PINS = [
    ("validator-1.6.3-standalone.jar",
     "https://github.com/itplr-kosit/validator/releases/download/v1.6.3/validator-1.6.3-standalone.jar",
     "799e64befca97d4080e03608c80b85dd5a5ecc5f4ae4f35d1116ec2855b9a7c9", "file"),
    ("xrechnung-config",
     "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/v2026-08-31/"
     "xrechnung-3.0.2-validator-configuration-2026-08-31.zip",
     "2530cd107c414511c5d0462ec10f886910395abfca820db82e83d70bf01221a8", "zip"),
    ("france-rfe",
     "https://codeload.github.com/fnfempe/France_RFE/tar.gz/97ba0f3d4ef2abed5780e9490d5c3a2be832ab1d",
     "5fe43e3ec008000a6aa564e67063ee9dd9aa9f0cfc6786b68fa6693486bc5f60", "tar"),
    # Peppol BIS 3.0.21 is published on docs.peppol.eu; its GitHub repository has no tag for it.
    ("peppol-bis-3.0.21/CEN-EN16931-UBL.sch",
     "https://docs.peppol.eu/poacc/billing/3.0/files/CEN-EN16931-UBL.sch",
     "268d4f7a2688676695e6c69cba6fba69a6802604fee12cb544a6b30ff09555a3", "file"),
    ("peppol-bis-3.0.21/PEPPOL-EN16931-UBL.sch",
     "https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch",
     "62e5b67892f12755352d78b06f63229a02cc2eccc748677c56efbc8dbcb336e3", "file"),
    ("schxslt-1.10.1.jar",
     "https://repo1.maven.org/maven2/name/dmaus/schxslt/schxslt/1.10.1/schxslt-1.10.1.jar",
     "4f4f21edab7b37f96ad59ae12a344d3510f1092ac46b6d81a4efa0120b73cb58", "file"),
    ("finvoice/Finvoice3.0.xsd",
     "https://file.finanssiala.fi/finvoice/css/270923/Finvoice3.0.xsd",
     "03ba971b4eeb002e06e7d503a89ed58b67cf0516284b206bf25f664799d3b4c8", "file"),
    ("si-ubl-2.0/si-ubl-2.0.xsl",
     "https://raw.githubusercontent.com/peppolautoriteit-nl/validation/4e93ae8681f413fef627a338ad84ce465a153ee8/"
     "xsl/si-ubl-2.0.xsl",
     "73da3db0b8cf6a37a8ad17051ac1603a83a695e2fa066820803aa1283a06e140", "file"),
    ("ebinterface-6.1/Invoice.xsd",
     "https://raw.githubusercontent.com/austriapro/ebinterface-standards/a3cf861e87f481e2432385a6038834956786605a/"
     "schemas/ebInterface6p1/Invoice.xsd",
     "8c736ca0953c5b0128210bc75dfa1b8b96e9743e856b5d339eaf825c137fab7c", "file"),
    # Wave 9: the national schemas of Spain, Italy and Poland, each from its state's own site.
    ("facturae-3.2.2/Facturaev3_2_2.xml",
     "https://www.facturae.gob.es/content/dam/facturae/formato/versiones/Facturaev3_2_2.xml",
     "b4bbcd587f5fb0a8a906336cca09b0a40d06ffaa78c6a62f6e438c4e6ea86e07", "file"),
    ("fatturapa-1.2.3/Schema_VFPR12_v1.2.3.xsd",
     "https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.4/Schema_VFPR12_v1.2.3.xsd",
     "152944f6eef9f5d69ef6e955ee173b32142b00a8c1c5222fc97dfab5910e8a8c", "file"),
    ("ksef-fa3/schemat.xsd", "http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd",
     "b646b6b525f51adf1bb2545f111fc8ca6e7aa6dd2f98948f1667d3695c06d958", "file"),
    ("ksef-fa3/StrukturyDanych_v10-0E.xsd", KSEF_TYPES + "StrukturyDanych_v10-0E.xsd",
     "1137ce6e3c11c2b9ef3f05e4e72d6dcd6b4fa94908ea558f2ba15de0259bb2aa", "file"),
    ("ksef-fa3/ElementarneTypyDanych_v10-0E.xsd", KSEF_TYPES + "ElementarneTypyDanych_v10-0E.xsd",
     "8a531cb181d3e298d11b28766655ae91fee2d7851440095932ffc82137ed2be1", "file"),
    ("ksef-fa3/KodyKrajow_v10-0E.xsd", KSEF_TYPES + "KodyKrajow_v10-0E.xsd",
     "1d41a1b3184188f2d20a51d3afde26204dda182ec5dacf018204dcc9870dc644", "file"),
]
PEPPOL_VERSION = "3.0.21"
PEPPOL_RULES = ("CEN-EN16931-UBL", "PEPPOL-EN16931-UBL")


def compile_peppol(into):
    """Compile the Peppol BIS .sch files to XSLT with SchXslt and the Saxon inside the KoSIT jar, with java
    from PATH or in the eclipse-temurin:21-jre image, as the pack check runs the validator."""
    out = into / ("peppol-" + PEPPOL_VERSION)
    if all((out / (n + ".xsl")).is_file() for n in PEPPOL_RULES):
        print("have %s" % out)
        return
    jar = next(iter(sorted(into.glob("validator-*-standalone.jar"))), None)
    if jar is None:
        raise SystemExit("the KoSIT validator jar is missing; it carries the Saxon that compiles the Peppol rules")
    sx = into / "schxslt"
    if not sx.is_dir():
        with zipfile.ZipFile(into / "schxslt-1.10.1.jar") as z:
            names = [n for n in z.namelist() if n.startswith("xslt/")]
            safe_members(names, sx)
            z.extractall(sx, members=names)
    out.mkdir(exist_ok=True)
    image = os.environ.get("FILETASK_JAVA_IMAGE", "eclipse-temurin:21-jre")
    for name in PEPPOL_RULES:
        sch = into / ("peppol-bis-" + PEPPOL_VERSION) / (name + ".sch")
        if shutil.which("java"):
            cmd = ["java", "-cp", str(jar), "net.sf.saxon.Transform", "-s:%s" % sch,
                   "-xsl:%s" % (sx / "xslt/2.0/pipeline-for-svrl.xsl"), "-o:%s" % (out / (name + ".xsl"))]
        elif shutil.which("docker"):
            cmd = ["docker", "run", "--rm", "--network", "none", "--user", "%d:%d" % (os.getuid(), os.getgid()),
                   "-v", "%s:/t" % into.resolve(), image, "java", "-cp", "/t/%s" % jar.name, "net.sf.saxon.Transform",
                   "-s:/t/peppol-bis-%s/%s.sch" % (PEPPOL_VERSION, name), "-xsl:/t/schxslt/xslt/2.0/pipeline-for-svrl.xsl",
                   "-o:/t/peppol-%s/%s.xsl" % (PEPPOL_VERSION, name)]
        else:
            raise SystemExit("no java and no docker to compile the Peppol rules")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not (out / (name + ".xsl")).is_file():
            raise SystemExit("could not compile %s: %s" % (name, (r.stderr or r.stdout)[-300:]))
        print("compiled %s" % (out / (name + ".xsl")))


def localise_ksef(into):
    """FA(3) and its type files name one another by their crd.gov.pl addresses. The validator runs without
    a network, so two copies of the four files are written whose schemaLocation attributes name the file
    beside them: strict/, with nothing else changed, and offline/, where every maxOccurs above 100 is
    written as unbounded as well, because java expands each counted occurrence and takes about ten minutes
    over FA(3)'s 10 000 lines and 50 000 corrected invoices. The files as fetched stay as they are, checked
    against their sums."""
    import re
    src = into / "ksef-fa3"
    names = ("schemat.xsd", "StrukturyDanych_v10-0E.xsd", "ElementarneTypyDanych_v10-0E.xsd", "KodyKrajow_v10-0E.xsd")
    if not all((src / n).is_file() for n in names):
        return
    lift = lambda m: m.group(0) if int(m.group(1)) <= 100 else 'maxOccurs="unbounded"'
    for folder, fast in (("strict", False), ("offline", True)):
        out = src / folder
        out.mkdir(exist_ok=True)
        for n in names:
            text = (src / n).read_bytes().decode("utf-8").replace('schemaLocation="%s' % KSEF_TYPES, 'schemaLocation="')
            if fast:
                text = re.sub(r'maxOccurs="(\d+)"', lift, text)
            (out / n).write_bytes(text.encode("utf-8"))
        print("wrote %s" % out)


def safe_members(names, root):
    for name in names:
        target = (root / name).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise SystemExit("refusing an archive path outside the target: %s" % name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--into", default=os.environ.get("FILETASK_EINVOICE_TOOLS")
                    or str(Path.home() / ".cache" / "nodejam" / "einvoice-tools"))
    a = ap.parse_args()
    into = Path(a.into).expanduser()
    into.mkdir(parents=True, exist_ok=True)
    for name, url, sha, kind in PINS:
        target = into / name
        if target.exists():
            print("have %s" % target)
            continue
        print("fetching %s" % url)
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120).read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            raise SystemExit("%s: SHA-256 %s, expected %s; nothing kept" % (name, got, sha))
        if kind == "file":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        elif kind == "zip":
            work = into / (name + ".part")
            shutil.rmtree(work, ignore_errors=True)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                safe_members(z.namelist(), work)
                z.extractall(work)
            work.rename(target)
        else:
            work = into / (name + ".part")
            shutil.rmtree(work, ignore_errors=True)
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
                members = [m for m in t.getmembers() if m.isfile() or m.isdir()]
                top = members[0].name.split("/")[0]
                for m in members:
                    m.name = m.name[len(top):].lstrip("/") or "."
                safe_members([m.name for m in members], work)
                t.extractall(work, members=members)
            work.rename(target)
        print("kept %s" % target)
    compile_peppol(into)
    localise_ksef(into)
    print("the e-invoice validators are in %s" % into)
    return 0


if __name__ == "__main__":
    sys.exit(main())
