#!/usr/bin/env python3
"""Write an invented one-way NDA, as the other side might send it, for the review and redline tests.

    make_counterparty.py their-nda.docx

The companies are invented. The text is our own and deliberately one-sided, so the review has
something to find: a one-way agreement, one carve-out of four, a ten-year survival, a penalty, a
non-solicit, backups to delete and a schedule that is not attached. Needs python-docx.
"""
import sys

from docx import Document
from docx.shared import Pt

CLAUSES = [
    ("1. Definitions", ["1.1 “Confidential Information” means all information disclosed by Halvard to the Recipient, "
                        "whether marked as confidential or not, including information disclosed orally."]),
    ("2. Obligations", ["2.1 The Recipient shall keep the Confidential Information strictly confidential and shall not "
                        "disclose it to any third party.",
                        "2.2 The Recipient shall be liable for any disclosure of Confidential Information, however caused."]),
    ("3. Exceptions", ["3.1 The obligations in clause 2 do not apply to information which is or becomes publicly "
                       "available other than through a breach of this Agreement."]),
    ("4. Permitted disclosure", ["4.1 The Recipient may disclose Confidential Information to its employees who need to "
                                 "know it for the Project."]),
    ("5. Term", ["5.1 This Agreement remains in force for five (5) years from the date above. The obligations of "
                 "confidentiality shall survive for a period of ten (10) years after termination."]),
    ("6. Return of information", ["6.1 On Halvard's request the Recipient shall return all Confidential Information and "
                                  "delete all copies, including back-up copies."]),
    ("7. Non-solicitation", ["7.1 For twenty-four (24) months from the date above the Recipient shall not solicit or "
                             "employ any employee of Halvard."]),
    ("8. Contractual penalty", ["8.1 For each breach of this Agreement the Recipient shall pay Halvard a contractual "
                                "penalty of NOK 500,000, without prejudice to Halvard's right to claim further damages."]),
    ("9. Governing law", ["9.1 This Agreement is governed by Norwegian law. Any dispute shall be settled by the courts "
                          "set out in Schedule 1."]),
]


def main(out):
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading("Confidentiality Agreement", level=1)
    p = doc.add_paragraph("This Confidentiality Agreement is entered into on 20 October 2026 between ")
    p.add_run("Halvard Data AS").bold = True
    p.add_run(", org. no. 921 456 789, Strandgaten 31, 5013 Bergen, Norway (“Halvard”) and ")
    p.add_run("Exempel Tryck AB").bold = True
    p.add_run(", reg. no. 556677-8899, Verkstadsgatan 7, 417 07 Gothenburg, Sweden (the “Recipient”), in connection "
              "with a possible joint reporting service (the “Project”).")
    for heading, texts in CLAUSES:
        h = doc.add_paragraph()
        h.add_run(heading).bold = True
        for t in texts:
            number, rest = t.split(" ", 1)
            q = doc.add_paragraph()
            q.add_run(number + " ")
            q.add_run(rest)
    doc.add_paragraph("Signed in two copies.")
    for name in ("Halvard Data AS", "Exempel Tryck AB"):
        doc.add_paragraph("For %s: ______________________" % name)
    doc.core_properties.title = "Confidentiality Agreement"
    doc.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
