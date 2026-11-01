#!/usr/bin/env python3
"""Turn the printed invoice page into a Factur-X / ZUGFeRD 2 file: one PDF/A-3 with the invoice's
Cross Industry Invoice XML inside it.

    python3 facturx_pdf.py invoice.pdf invoice.xml [--out invoice.pdf] [--lang fr-FR]

What goes in, and where each part comes from:

    The XML        attached as factur-x.xml (xrechnung.xml for the XRECHNUNG profile), an embedded
                   file whose file specification says how it relates to the page (AFRelationship)
                   and is listed in the catalog's /AF array (ISO 19005-3, PDF/A-3, clause 6.8).
    XMP            pdfaid part 3, conformance B; the Factur-X extension schema and its four values:
                   DocumentType INVOICE, DocumentFileName, Version 1.0 and ConformanceLevel (the
                   profile the XML's guideline ID names: EN 16931, or XRECHNUNG). ZUGFeRD 2.x uses
                   the same namespace and file name since 2.1, so one file serves France and Germany.
    Output intent  sRGB, the colour space Chromium prints in, with an ICC profile LittleCMS writes
                   (cmsCreate_sRGBProfile, through Pillow's ImageCms) carried beside this script as
                   srgb.icc; the profile is generated, not copied.
    Trailer ID     the file identifier PDF/A asks for.

The attachment and XMP code follows akretion's factur-x library (BSD-3-Clause, Copyright (c)
2016-2023 Alexis de Lattre, github.com/akretion/factur-x, release 7.4): its
_facturx_update_metadata_add_attachment and _prepare_pdf_metadata_xml, ported onto pypdf alone, with
the output intent, trailer ID and profile detection added. The package itself is not a dependency:
it pulls in python-stdnum, which is LGPL.

pypdf (BSD-3-Clause) is the one library this needs; the app's Python runtime carries it.
"""
import argparse
import datetime as dt
import hashlib
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
FX_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
# The profile the XML's guideline ID (BT-24) names, as Factur-X 1.x (namespace 1p0 through 1.09.2) and ZUGFeRD 2.x
# write it in the XMP.
PROFILES = [
    ("urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0", "XRECHNUNG", "xrechnung.xml"),
    ("urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended", "EXTENDED", "factur-x.xml"),
    ("urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic", "BASIC", "factur-x.xml"),
    ("urn:factur-x.eu:1p0:basicwl", "BASIC WL", "factur-x.xml"),
    ("urn:factur-x.eu:1p0:minimum", "MINIMUM", "factur-x.xml"),
    ("urn:cen.eu:en16931:2017", "EN 16931", "factur-x.xml"),
]


def profile_of(xml_bytes):
    """(conformance level, embedded file name) from the XML's guideline ID (BT-24)."""
    root = ET.fromstring(xml_bytes)
    node = root.find("{*}ExchangedDocumentContext/{*}GuidelineSpecifiedDocumentContextParameter/{*}ID")
    guideline = (node.text or "").strip() if node is not None else ""
    for urn, level, name in PROFILES:
        if guideline == urn:
            return level, name, guideline
    raise SystemExit("the XML's guideline ID (BT-24) is %r, which no Factur-X or ZUGFeRD profile names"
                     % guideline)


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def xmp(level, file_name, title, lang, stamp, producer):
    """The XMP packet: PDF/A-3B identification, Dublin Core, and the Factur-X extension schema."""
    return ("""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
   <pdfaid:part>3</pdfaid:part>
   <pdfaid:conformance>B</pdfaid:conformance>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">
   <dc:format>application/pdf</dc:format>
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">%(title)s</rdf:li></rdf:Alt></dc:title>
   <dc:language><rdf:Bag><rdf:li>%(lang)s</rdf:li></rdf:Bag></dc:language>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
   <pdf:Producer>%(producer)s</pdf:Producer>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
   <xmp:CreatorTool>nodejam-page-builder</xmp:CreatorTool>
   <xmp:CreateDate>%(stamp)s</xmp:CreateDate>
   <xmp:ModifyDate>%(stamp)s</xmp:ModifyDate>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/"
    xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">
   <pdfaExtension:schemas>
    <rdf:Bag>
     <rdf:li rdf:parseType="Resource">
      <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>
      <pdfaSchema:namespaceURI>%(ns)s</pdfaSchema:namespaceURI>
      <pdfaSchema:prefix>fx</pdfaSchema:prefix>
      <pdfaSchema:property>
       <rdf:Seq>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>The name of the embedded XML document</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>DocumentType</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>The type of the hybrid document in capital letters, e.g. INVOICE or ORDER</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>Version</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>The actual version of the standard applying to the embedded XML document</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>The conformance level of the embedded XML document</pdfaProperty:description>
        </rdf:li>
       </rdf:Seq>
      </pdfaSchema:property>
     </rdf:li>
    </rdf:Bag>
   </pdfaExtension:schemas>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:fx="%(ns)s">
   <fx:DocumentType>INVOICE</fx:DocumentType>
   <fx:DocumentFileName>%(file)s</fx:DocumentFileName>
   <fx:Version>1.0</fx:Version>
   <fx:ConformanceLevel>%(level)s</fx:ConformanceLevel>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""" % {"title": esc(title), "lang": esc(lang or "x-default"), "producer": esc(producer),
                          "stamp": stamp, "ns": FX_NS, "file": file_name, "level": level}).encode("utf-8")


def embed(pdf_in, xml_bytes, pdf_out, title="", lang=""):
    """Write pdf_out: the page of pdf_in as PDF/A-3B with xml_bytes attached as the Factur-X XML.
    Returns (conformance level, embedded file name)."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import (ArrayObject, ByteStringObject, DecodedStreamObject, DictionaryObject,
                                   NameObject, NumberObject, TextStringObject)
    except ImportError:
        raise SystemExit("pypdf is not installed: pip install pypdf (BSD-3-Clause), then build again")
    level, file_name, _guideline = profile_of(xml_bytes)
    # One relation for every profile: the XML is the invoice's data, the page its picture. Factur-X 1.x
    # lets France and Germany use Data, Alternative or Source; Alternative says the XML is the whole
    # invoice again, which it is for EN 16931 and XRECHNUNG.
    relation = "/Alternative" if level in ("EN 16931", "EXTENDED", "XRECHNUNG") else "/Data"
    reader = PdfReader(str(pdf_in))
    writer = PdfWriter(clone_from=reader)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    pdf_date = now.strftime("D:%Y%m%d%H%M%S+00'00'")
    stamp = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    producer = "pypdf"

    # The embedded file, its file specification, and the catalog's /AF and /Names entries.
    data = DecodedStreamObject()
    data.set_data(xml_bytes)
    data = data.flate_encode()
    data.update({NameObject("/Type"): NameObject("/EmbeddedFile"), NameObject("/Subtype"): NameObject("/text/xml"),
                 NameObject("/Params"): DictionaryObject({
                     NameObject("/CheckSum"): ByteStringObject(hashlib.md5(xml_bytes).digest()),
                     NameObject("/ModDate"): TextStringObject(pdf_date),
                     NameObject("/Size"): NumberObject(len(xml_bytes))})})
    data_ref = writer._add_object(data)
    spec = DictionaryObject({
        NameObject("/Type"): NameObject("/Filespec"),
        NameObject("/F"): TextStringObject(file_name), NameObject("/UF"): TextStringObject(file_name),
        NameObject("/Desc"): TextStringObject("Factur-X invoice data (%s)" % level),
        NameObject("/AFRelationship"): NameObject(relation),
        NameObject("/EF"): DictionaryObject({NameObject("/F"): data_ref, NameObject("/UF"): data_ref})})
    spec_ref = writer._add_object(spec)
    root = writer._root_object
    root[NameObject("/AF")] = writer._add_object(ArrayObject([spec_ref]))
    root[NameObject("/Names")] = DictionaryObject({NameObject("/EmbeddedFiles"): DictionaryObject({
        NameObject("/Names"): ArrayObject([TextStringObject(file_name), spec_ref])})})

    # The XMP, uncompressed so any reader (and the pack check) can read it as it stands.
    meta = DecodedStreamObject()
    meta.set_data(xmp(level, file_name, title, lang, stamp, producer))
    meta.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
    root[NameObject("/Metadata")] = writer._add_object(meta)

    # The output intent: sRGB, the space the page is printed in.
    icc_bytes = (HERE / "srgb.icc").read_bytes()
    icc = DecodedStreamObject()
    icc.set_data(icc_bytes)
    icc = icc.flate_encode()
    icc[NameObject("/N")] = NumberObject(3)
    root[NameObject("/OutputIntents")] = ArrayObject([writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/OutputIntent"), NameObject("/S"): NameObject("/GTS_PDFA1"),
        NameObject("/OutputConditionIdentifier"): TextStringObject("sRGB IEC61966-2.1"),
        NameObject("/Info"): TextStringObject("sRGB IEC61966-2.1"),
        NameObject("/DestOutputProfile"): writer._add_object(icc)}))])
    if lang:
        root[NameObject("/Lang")] = TextStringObject(lang)

    # The document information dictionary says what the XMP says (PDF/A-3 clause 6.6.2.3.1).
    writer._info = None
    writer.add_metadata({"/Title": title, "/Producer": producer, "/Creator": "nodejam-page-builder",
                         "/CreationDate": pdf_date, "/ModDate": pdf_date})
    # The file identifier PDF/A asks for in the trailer (clause 6.1.3).
    ident = ByteStringObject(hashlib.md5(xml_bytes + pdf_date.encode()).digest())
    writer._ID = ArrayObject([ident, ident])
    tmp = Path(str(pdf_out) + ".part")
    with open(tmp, "wb") as fh:
        writer.write(fh)
    tmp.replace(pdf_out)
    return level, file_name


def main():
    ap = argparse.ArgumentParser(description="Make a Factur-X / ZUGFeRD 2 PDF/A-3 from the page and its XML.")
    ap.add_argument("pdf")
    ap.add_argument("xml")
    ap.add_argument("--out")
    ap.add_argument("--title", default="")
    ap.add_argument("--lang", default="")
    a = ap.parse_args()
    level, name = embed(a.pdf, Path(a.xml).read_bytes(), a.out or a.pdf, a.title, a.lang)
    print("%s: Factur-X %s, %s embedded" % (a.out or a.pdf, level, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
