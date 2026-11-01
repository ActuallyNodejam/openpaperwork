#!/usr/bin/env python3
"""The words and the country parts of the invoice page for Norway, Denmark, Finland, the United Kingdom,
Australia, Canada (English and French) and the United States, and from wave 8 Belgium (Dutch, French and
German), the Netherlands, Austria and Ireland, and from wave 9 Spain, Italy and Poland. build_page.py merges these tables into its
own and asks this module for each country's lines: the seller's identifiers in the footer, the payment
lines, the mentions the law asks for, the sums and, in Canada and the United States, the sales taxes.

Where each piece comes from is in scripts/countries.py; the number and date forms are CLDR's, from
skills/_checks/locales.json. Standard library only.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import countries  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import letter  # noqa: E402

ids = countries.ids

WORDS = {
    "nb-NO": {"invoice": "Faktura", "credit_note": "Kreditnota", "preceding": "Opprinnelig faktura",
              "number": "Fakturanummer", "issue": "Fakturadato", "due": "Forfallsdato", "delivery": "Leveringsdato",
              "from": "Fra", "to": "Til", "description": "Beskrivelse", "qty": "Antall", "unit": "Enhet",
              "unit_price": "Enhetspris", "net": "Beløp", "vat": "MVA", "total": "Å betale", "rate": "MVA",
              "base": "Grunnlag", "account": "Kontonr.", "terms": "Betalingsbetingelser", "delivered": "Leveringsdato",
              "currency": "Valuta", "vat_id": "Org.nr."},
    "fi-FI": {"invoice": "Lasku", "credit_note": "Hyvityslasku", "preceding": "Alkuperäinen lasku",
              "number": "Laskun numero", "issue": "Laskun päivämäärä", "due": "Eräpäivä", "delivery": "Toimituspäivä",
              "from": "Lähettäjä", "to": "Vastaanottaja", "description": "Kuvaus", "qty": "Määrä", "unit": "Yksikkö",
              "unit_price": "À-hinta", "net": "Veroton", "vat": "ALV", "total": "Maksettava yhteensä", "rate": "ALV",
              "base": "Veron peruste", "account": "Tilinumero", "terms": "Maksuehto", "delivered": "Toimituspäivä",
              "currency": "Valuutta", "vat_id": "ALV-tunniste"},
    "en-AU": {"invoice": "Tax invoice", "credit_note": "Adjustment note", "preceding": "Original invoice",
              "number": "Invoice number", "issue": "Date", "due": "Due date", "delivery": "Supply date",
              "from": "From", "to": "To", "description": "Description", "qty": "Qty", "unit": "Unit",
              "unit_price": "Unit price", "net": "Amount", "vat": "GST", "total": "Total incl. GST", "rate": "GST",
              "base": "Base", "account": "Account", "terms": "Terms", "delivered": "Supply date",
              "currency": "Currency", "vat_id": "ABN"},
    "en-CA": {"invoice": "Invoice", "credit_note": "Credit note", "preceding": "Original invoice",
              "number": "Invoice no.", "issue": "Invoice date", "due": "Due date", "delivery": "Date of supply",
              "from": "From", "to": "Bill to", "description": "Description", "qty": "Qty", "unit": "Unit",
              "unit_price": "Unit price", "net": "Amount", "vat": "Tax", "total": "Total", "rate": "Tax",
              "base": "Base", "account": "Account", "terms": "Terms", "delivered": "Date of supply",
              "currency": "Currency", "vat_id": "GST/HST no."},
    "fr-CA": {"invoice": "Facture", "credit_note": "Note de crédit", "preceding": "Facture d'origine",
              "number": "No de facture", "issue": "Date de facturation", "due": "Date d'échéance",
              "delivery": "Date de fourniture", "from": "De", "to": "Facturer à", "description": "Description",
              "qty": "Qté", "unit": "Unité", "unit_price": "Prix unitaire", "net": "Montant", "vat": "Taxe",
              "total": "Total", "rate": "Taxe", "base": "Base", "account": "Compte", "terms": "Modalités de paiement",
              "delivered": "Date de fourniture", "currency": "Devise", "vat_id": "No de TPS/TVH"},
    "en-US": {"invoice": "Invoice", "credit_note": "Credit memo", "preceding": "Original invoice",
              "number": "Invoice #", "issue": "Invoice date", "due": "Due date", "delivery": "Ship date",
              "from": "From", "to": "Bill to", "description": "Description", "qty": "Qty", "unit": "Unit",
              "unit_price": "Rate", "net": "Amount", "vat": "Sales tax", "total": "Total", "rate": "Tax",
              "base": "Base", "account": "Account", "terms": "Terms", "delivered": "Ship date",
              "currency": "Currency", "vat_id": "Sales tax permit"},
    # Wave 8. Dutch in the Netherlands and Flanders, French and German in Belgium, Austrian German, Irish
    # English: the words each country's invoices and its tax administration's guidance use.
    "nl-NL": {"invoice": "Factuur", "credit_note": "Creditnota", "preceding": "Oorspronkelijke factuur",
              "number": "Factuurnummer", "issue": "Factuurdatum", "due": "Vervaldatum", "delivery": "Leverdatum",
              "from": "Van", "to": "Aan", "description": "Omschrijving", "qty": "Aantal", "unit": "Eenheid",
              "unit_price": "Prijs", "net": "Bedrag", "vat": "Btw", "total": "Te betalen", "rate": "Btw",
              "base": "Grondslag", "account": "Rekening", "terms": "Betalingstermijn", "delivered": "Leverdatum",
              "currency": "Valuta", "vat_id": "Btw-id"},
    "nl-BE": {"invoice": "Factuur", "credit_note": "Creditnota", "preceding": "Oorspronkelijke factuur",
              "number": "Factuurnummer", "issue": "Factuurdatum", "due": "Vervaldatum", "delivery": "Leveringsdatum",
              "from": "Van", "to": "Aan", "description": "Omschrijving", "qty": "Aantal", "unit": "Eenheid",
              "unit_price": "Eenheidsprijs", "net": "Bedrag", "vat": "Btw", "total": "Te betalen", "rate": "Btw",
              "base": "Maatstaf", "account": "Rekening", "terms": "Betalingsvoorwaarden", "delivered": "Leveringsdatum",
              "currency": "Munt", "vat_id": "Btw-nr."},
    "fr-BE": {"invoice": "Facture", "credit_note": "Note de crédit", "preceding": "Facture d'origine",
              "number": "N° de facture", "issue": "Date de facture", "due": "Date d'échéance",
              "delivery": "Date de livraison", "from": "De", "to": "À", "description": "Description", "qty": "Qté",
              "unit": "Unité", "unit_price": "Prix unitaire", "net": "Montant", "vat": "TVA", "total": "Total à payer",
              "rate": "TVA", "base": "Base", "account": "Compte", "terms": "Conditions de paiement",
              "delivered": "Date de livraison", "currency": "Devise", "vat_id": "N° TVA"},
    "de-BE": {"invoice": "Rechnung", "credit_note": "Gutschrift", "preceding": "Ursprüngliche Rechnung",
              "number": "Rechnungsnummer", "issue": "Rechnungsdatum", "due": "Fällig am", "delivery": "Lieferdatum",
              "from": "Von", "to": "An", "description": "Beschreibung", "qty": "Menge", "unit": "Einheit",
              "unit_price": "Einzelpreis", "net": "Betrag", "vat": "MwSt.", "total": "Zu zahlen", "rate": "MwSt.",
              "base": "Besteuerungsgrundlage", "account": "Konto", "terms": "Zahlungsbedingungen",
              "delivered": "Lieferdatum", "currency": "Währung", "vat_id": "MwSt.-Nr."},
    # Austria: a credit note correcting an invoice is a Rechnungskorrektur; "Gutschrift" is the word UStG
    # § 11 Abs. 7 and 8 reserve for self-billing, which this pack does not write.
    "de-AT": {"invoice": "Rechnung", "credit_note": "Rechnungskorrektur", "preceding": "Ursprüngliche Rechnung",
              "number": "Rechnungsnummer", "issue": "Rechnungsdatum", "due": "Fällig am", "delivery": "Leistungsdatum",
              "from": "Von", "to": "An", "description": "Bezeichnung", "qty": "Menge", "unit": "Einheit",
              "unit_price": "Einzelpreis", "net": "Netto", "vat": "USt", "total": "Gesamtbetrag", "rate": "USt",
              "base": "Bemessungsgrundlage", "account": "Konto", "terms": "Zahlungsbedingungen",
              "delivered": "Leistungsdatum", "currency": "Währung", "vat_id": "UID-Nr."},
    "en-IE": {"invoice": "Invoice", "credit_note": "Credit note", "preceding": "Original invoice",
              "number": "Invoice number", "issue": "Invoice date", "due": "Due date", "delivery": "Date of supply",
              "from": "From", "to": "To", "description": "Description", "qty": "Qty", "unit": "Unit",
              "unit_price": "Unit price", "net": "Amount", "vat": "VAT", "total": "Total due", "rate": "VAT rate",
              "base": "Base", "account": "Account", "terms": "Payment terms", "delivered": "Date of supply",
              "currency": "Currency", "vat_id": "VAT No."},
    # Wave 9. Spanish, Italian and Polish: the words of each country's invoicing rules (Real Decreto 1619/2012:
    # factura rectificativa, base imponible, fecha de expedición; DPR 633/1972: imponibile, nota di credito;
    # ustawa o VAT art. 106e and 106j: data wystawienia, cena jednostkowa netto, wartość sprzedaży netto,
    # faktura korygująca) and of its invoices.
    "es-ES": {"invoice": "Factura", "credit_note": "Factura rectificativa", "preceding": "Factura rectificada",
              "number": "Número", "issue": "Fecha de expedición", "due": "Vencimiento",
              "delivery": "Fecha de operación", "from": "De", "to": "Para", "description": "Descripción",
              "qty": "Cantidad", "unit": "Unidad", "unit_price": "Precio unitario", "net": "Importe", "vat": "IVA",
              "total": "Total factura", "rate": "IVA", "base": "Base imponible", "account": "Cuenta",
              "terms": "Forma de pago", "delivered": "Fecha de operación", "currency": "Moneda", "vat_id": "NIF"},
    "it-IT": {"invoice": "Fattura", "credit_note": "Nota di credito", "preceding": "Fattura di riferimento",
              "number": "Numero", "issue": "Data", "due": "Scadenza", "delivery": "Data operazione",
              "from": "Da", "to": "A", "description": "Descrizione", "qty": "Quantità", "unit": "U.M.",
              "unit_price": "Prezzo unitario", "net": "Importo", "vat": "IVA", "total": "Totale documento",
              "rate": "IVA", "base": "Imponibile", "account": "Conto", "terms": "Pagamento",
              "delivered": "Data operazione", "currency": "Valuta", "vat_id": "P. IVA"},
    "pl-PL": {"invoice": "Faktura", "credit_note": "Faktura korygująca", "preceding": "Faktura korygowana",
              "number": "Numer", "issue": "Data wystawienia", "due": "Termin płatności",
              "delivery": "Data sprzedaży", "from": "Sprzedawca", "to": "Nabywca",
              "description": "Nazwa towaru lub usługi", "qty": "Ilość", "unit": "J.m.",
              "unit_price": "Cena jedn. netto", "net": "Wartość netto", "vat": "VAT", "total": "Razem do zapłaty",
              "rate": "VAT", "base": "Podstawa", "account": "Rachunek", "terms": "Warunki płatności",
              "delivered": "Data sprzedaży", "currency": "Waluta", "vat_id": "NIP"},
}
EXTRA_WORDS = {
    "nb-NO": {"customer_vat": "Kundens org.nr.", "tax_number": "Org.nr.", "vat_in": "MVA i %s",
              "vat_on": "MVA %s %% av %s", "preceding_date": "Dato opprinnelig faktura",
              "buyer_reference": "Deres ref.", "contact": "Vår ref.", "phone": "Telefon", "email": "E-post",
              "net_total": "Sum eks. MVA", "delivery_place": "Leveringssted", "order_reference": "Bestillingsnr.",
              "kid": "KID", "pay_to": "Betales til kontonr.", "register": "Foretaksregisteret",
              "office": "Hovedkontor"},
    "da-DK": {"net_total": "I alt ekskl. moms", "bank_reg": "Reg.nr.", "account_no": "Kontonr.",
              "order_reference": "Ordrenr.", "office": "Hjemsted", "register_no": "CVR-nr.",
              "pay_to": "Betaling til"},
    "fi-FI": {"customer_vat": "Asiakkaan ALV-tunniste", "tax_number": "Y-tunnus", "vat_in": "ALV euroina",
              "vat_on": "ALV %s %% (peruste %s)", "preceding_date": "Alkuperäisen laskun päivämäärä",
              "buyer_reference": "Viitteenne", "contact": "Yhteyshenkilö", "phone": "Puhelin", "email": "Sähköposti",
              "net_total": "Veroton yhteensä", "order_reference": "Tilausnumero", "reference": "Viitenumero",
              "late_interest": "Viivästyskorko", "complaint": "Huomautusaika", "barcode": "Virtuaaliviivakoodi",
              "office": "Kotipaikka", "days": "pv"},
    "en-GB": {"order_reference": "Purchase order", "sort_code": "Sort code", "account_no": "Account",
              "pay_to": "Pay to"},
    "en-AU": {"customer_vat": "Customer ABN", "tax_number": "ABN", "vat_in": "GST in %s",
              "vat_on": "GST %s%% on %s", "preceding_date": "Original invoice date", "buyer_reference": "Your reference",
              "contact": "Contact", "phone": "Phone", "email": "Email", "net_total": "Total excl. GST",
              "order_reference": "Purchase order", "gst_free": "GST-free", "bsb": "BSB", "account_no": "Account",
              "pay_to": "Pay to"},
    "en-CA": {"customer_vat": "Customer", "tax_number": "Business number", "vat_in": "Tax in %s",
              "vat_on": "%s %s%% on %s", "preceding_date": "Original invoice date", "buyer_reference": "Your reference",
              "contact": "Contact", "phone": "Phone", "email": "Email", "net_total": "Subtotal",
              "order_reference": "PO number", "qst": "QST no.", "exempt": "Exempt", "pay_to": "Pay to"},
    "fr-CA": {"customer_vat": "Client", "tax_number": "No d'entreprise", "vat_in": "Taxe en %s",
              "vat_on": "%s %s %% sur %s", "preceding_date": "Date de la facture d'origine",
              "buyer_reference": "Votre référence", "contact": "Personne-ressource", "phone": "Téléphone",
              "email": "Courriel", "net_total": "Sous-total", "order_reference": "No de bon de commande",
              "qst": "No de TVQ", "exempt": "Exonéré", "pay_to": "Payable à"},
    "en-US": {"customer_vat": "Customer", "tax_number": "EIN", "vat_in": "Tax in %s", "vat_on": "%s %s%% on %s",
              "preceding_date": "Original invoice date", "buyer_reference": "Your reference", "contact": "Contact",
              "phone": "Phone", "email": "Email", "net_total": "Subtotal", "order_reference": "P.O. #",
              "exempt": "Non-taxable", "balance": "Balance due", "pay_to": "Pay to", "rate": "Tax"},
    "nl-NL": {"customer_vat": "Btw-id klant", "tax_number": "KvK", "vat_in": "Btw in %s", "vat_on": "Btw %s%% over %s",
              "preceding_date": "Datum oorspr. factuur", "buyer_reference": "Uw referentie",
              "contact": "Contactpersoon", "phone": "Telefoon", "email": "E-mail", "net_total": "Totaal excl. btw",
              "order_reference": "Ordernummer", "reference": "Betalingskenmerk", "pay_to": "Te betalen op",
              "office": "Statutaire zetel"},
    "nl-BE": {"customer_vat": "Btw-nr. klant", "tax_number": "Ondernemingsnr.", "vat_in": "Btw in %s",
              "vat_on": "Btw %s%% op %s", "preceding_date": "Datum oorspr. factuur",
              "buyer_reference": "Uw referentie", "contact": "Contactpersoon", "phone": "Telefoon", "email": "E-mail",
              "net_total": "Totaal excl. btw", "order_reference": "Bestelnummer", "reference": "Gestructureerde mededeling",
              "pay_to": "Te betalen op", "office": "Zetel"},
    "fr-BE": {"customer_vat": "N° TVA client", "tax_number": "N° d'entreprise", "vat_in": "TVA en %s",
              "vat_on": "TVA %s %% sur %s", "preceding_date": "Date de la facture d'origine",
              "buyer_reference": "Votre référence", "contact": "Contact", "phone": "Téléphone", "email": "E-mail",
              "net_total": "Total hors TVA", "order_reference": "N° de commande", "reference": "Communication structurée",
              "pay_to": "À payer sur le compte", "office": "Siège"},
    "de-BE": {"customer_vat": "MwSt.-Nr. Kunde", "tax_number": "Unternehmensnr.", "vat_in": "MwSt. in %s",
              "vat_on": "MwSt. %s %% auf %s", "preceding_date": "Datum der ursprünglichen Rechnung",
              "buyer_reference": "Ihre Referenz", "contact": "Ansprechpartner", "phone": "Telefon", "email": "E-Mail",
              "net_total": "Gesamt ohne MwSt.", "order_reference": "Bestellnummer",
              "reference": "Strukturierte Mitteilung", "pay_to": "Zahlbar auf", "office": "Sitz"},
    "de-AT": {"customer_vat": "UID-Nr. Empfänger", "tax_number": "Steuernummer", "vat_in": "USt in %s",
              "vat_on": "USt %s %% von %s", "preceding_date": "Urspr. Rechnung vom",
              "buyer_reference": "Ihre Referenz", "contact": "Ansprechperson", "phone": "Telefon", "email": "E-Mail",
              "net_total": "Summe netto", "order_reference": "Bestellnummer", "reference": "Zahlungsreferenz",
              "pay_to": "Zahlbar auf", "office": "Sitz"},
    "en-IE": {"customer_vat": "Customer VAT No.", "tax_number": "Company number", "vat_in": "VAT in %s",
              "vat_on": "VAT %s%% on %s", "preceding_date": "Original invoice date", "buyer_reference": "Your reference",
              "contact": "Contact", "phone": "Phone", "email": "Email", "net_total": "Total excl. VAT",
              "order_reference": "Purchase order", "pay_to": "Pay to", "office": "Registered office",
              "reason": "Reason for credit"},
    "es-ES": {"customer_vat": "NIF del cliente", "tax_number": "NIF", "vat_in": "IVA en %s",
              "vat_on": "IVA %s\u00a0%% sobre %s", "preceding_date": "Fecha fact. rectificada",
              "buyer_reference": "Su referencia", "contact": "Contacto", "phone": "Teléfono", "email": "Correo",
              "net_total": "Base imponible", "order_reference": "N.º de pedido", "reference": "Concepto",
              "pay_to": "Pago a", "office": "Domicilio social", "series": "Serie",
              "reason": "Motivo de la rectificación"},
    "it-IT": {"customer_vat": "P. IVA cliente", "tax_number": "Codice fiscale", "vat_in": "IVA in %s",
              "vat_on": "IVA %s%% su %s", "preceding_date": "Data fattura di rif.",
              "buyer_reference": "Vs. riferimento", "contact": "Referente", "phone": "Telefono", "email": "E-mail",
              "net_total": "Totale imponibile", "order_reference": "Ordine n.", "reference": "Causale",
              "pay_to": "Pagamento a", "office": "Sede legale", "customer_cf": "C.F. cliente", "reason": "Causale"},
    "pl-PL": {"customer_vat": "NIP nabywcy", "tax_number": "REGON", "vat_in": "VAT w %s",
              "vat_on": "VAT %s%% od %s", "preceding_date": "Data faktury koryg.",
              "buyer_reference": "Nr ref. nabywcy", "contact": "Osoba kontaktowa", "phone": "Telefon",
              "email": "E-mail", "net_total": "Razem netto", "order_reference": "Nr zamówienia",
              "reference": "Tytuł przelewu", "pay_to": "Płatne na rachunek", "office": "Siedziba",
              "ksef_number": "Numer KSeF faktury korygowanej", "reason": "Przyczyna korekty"},
}
CREDIT_WORDS = {
    "nb-NO": {"number": "Kreditnotanummer", "issue": "Kreditnotadato"},
    "fi-FI": {"number": "Hyvityslaskun numero", "issue": "Hyvityslaskun päivämäärä"},
    "en-AU": {"number": "Adjustment note number", "issue": "Date"},
    "en-CA": {"number": "Credit note no.", "issue": "Credit note date"},
    "fr-CA": {"number": "No de note de crédit", "issue": "Date de la note de crédit"},
    "en-US": {"number": "Credit memo #", "issue": "Date"},
    "nl-NL": {"number": "Creditnotanummer", "issue": "Creditnotadatum"},
    "nl-BE": {"number": "Creditnotanummer", "issue": "Creditnotadatum"},
    "fr-BE": {"number": "N° de note de crédit", "issue": "Date de la note de crédit"},
    "de-BE": {"number": "Gutschriftsnummer", "issue": "Gutschriftsdatum"},
    "de-AT": {"number": "Korrekturnummer", "issue": "Korrekturdatum"},
    "en-IE": {"number": "Credit note number", "issue": "Credit note date"},
    # A Spanish rectifying invoice and a Polish correcting invoice state the correction, not an amount to pay.
    "es-ES": {"total": "Total rectificación"},
    "it-IT": {"number": "Numero", "issue": "Data"},
    "pl-PL": {"total": "Razem korekta"},
}
TERMS = {
    "nb-NO": {"days": "%d dager", "net": "%d dager netto"},
    "fi-FI": {"days": "%d päivää", "net": "%d päivää netto"},
    "en-AU": {"days": "%d days", "net": "%d days net"},
    "en-CA": {"days": "%d days", "net": "Net %d days"},
    "fr-CA": {"days": "%d jours", "net": "Net %d jours"},
    "en-US": {"days": "%d days", "net": "Net %d"},
    "nl-NL": {"days": "%d dagen", "net": "%d dagen netto"},
    "nl-BE": {"days": "%d dagen", "net": "%d dagen netto"},
    "fr-BE": {"days": "%d jours", "net": "%d jours net"},
    "de-BE": {"days": "%d Tage", "net": "%d Tage netto"},
    "de-AT": {"days": "%d Tage", "net": "%d Tage netto"},
    "en-IE": {"days": "%d days", "net": "%d days net"},
    "es-ES": {"days": "%d días", "net": "%d días fecha factura"},
    "it-IT": {"days": "%d giorni", "net": "%d giorni data fattura"},
    "pl-PL": {"days": "%d dni", "net": "%d dni"},
}
UNITS = {"C62": {"nb-NO": "stk", "fi-FI": "kpl", "en-AU": "ea", "en-CA": "ea", "fr-CA": "unité", "en-US": "ea"},
         "HUR": {"nb-NO": "timer", "fi-FI": "h", "en-AU": "hrs", "en-CA": "hrs", "fr-CA": "h", "en-US": "hrs"},
         "DAY": {"nb-NO": "dager", "fi-FI": "pv", "en-AU": "days", "en-CA": "days", "fr-CA": "jours", "en-US": "days"},
         "KGM": {k: "kg" for k in ("nb-NO", "fi-FI", "en-AU", "en-CA", "fr-CA", "en-US")},
         "MTR": {k: "m" for k in ("nb-NO", "fi-FI", "en-AU", "en-CA", "fr-CA", "en-US")},
         "LTR": {"nb-NO": "l", "fi-FI": "l", "en-AU": "L", "en-CA": "L", "fr-CA": "L", "en-US": "L"},
         "MON": {"nb-NO": "mnd", "fi-FI": "kk", "en-AU": "month", "en-CA": "month", "fr-CA": "mois", "en-US": "month",
                 "en-GB": "month", "de-DE": "Monat", "sv-SE": "mån", "da-DK": "md.", "fr-FR": "mois"}}
W8 = ("nl-NL", "nl-BE", "fr-BE", "de-BE", "de-AT", "en-IE")
for _code, _forms in {"C62": ("st", "st", "pce", "Stk", "Stk", "pcs"), "HUR": ("uur", "uur", "h", "Std", "Std", "h"),
                      "DAY": ("dag", "dag", "jour", "Tag", "Tag", "day"), "MON": ("maand", "maand", "mois", "Monat", "Monat", "month"),
                      "KGM": ("kg",) * 6, "MTR": ("m",) * 6, "LTR": ("l",) * 6}.items():
    UNITS[_code].update(dict(zip(W8, _forms)))
W9 = ("es-ES", "it-IT", "pl-PL")
for _code, _forms in {"C62": ("ud.", "pz", "szt."), "HUR": ("h", "ore", "godz."), "DAY": ("días", "giorni", "dni"),
                      "MON": ("meses", "mesi", "mies."), "KGM": ("kg",) * 3, "MTR": ("m",) * 3, "LTR": ("l",) * 3}.items():
    UNITS[_code].update(dict(zip(W9, _forms)))
REVERSE_CHARGE = {"nb-NO": countries.NO_REVERSE, "fi-FI": "Käännetty verovelvollisuus",
                  "en-AU": "Reverse charge", "en-CA": "Reverse charge", "fr-CA": "Autocotisation",
                  "en-US": "Reverse charge"}
REVERSE_CHARGE.update(countries.REVERSE)
# The UK words of VAT Notice 700/21 4.1 on a British seller's page: its VAT registration number, the
# time of supply (the tax point) and the totals excluding VAT and payable.
UK_WORDS = {"vat_id": "VAT registration no.", "delivered": "Tax point", "net_total": "Total excluding VAT",
            "total": "Total payable", "customer_vat": "Customer VAT no.", "rate": "VAT rate",
            "buyer_reference": "Your reference"}
# A line's discount, named in the description: momsbekendtgørelsen § 58 nr. 8, AVL 209 e § 8 and VAT
# Notice 700/21 ask for discounts not already in the unit price.
DISCOUNT = {"nb-NO": "rabatt", "da-DK": "rabat", "fi-FI": "alennus", "en-GB": "discount", "en-AU": "discount",
            "en-CA": "discount", "fr-CA": "remise", "en-US": "discount", "nl-NL": "korting", "nl-BE": "korting",
            "fr-BE": "remise", "de-BE": "Rabatt", "de-AT": "Rabatt", "en-IE": "discount", "es-ES": "descuento",
            "it-IT": "sconto", "pl-PL": "rabat"}
# Canadian tax names in French (Revenu Québec, CRA): TPS, TVH, TVQ, TVP.
FR_CA_TAX = {"GST": "TPS", "HST": "TVH", "QST": "TVQ", "PST": "TVP"}
# The locale each new country writes in, and the countries whose pages state a VAT rate on every line
# (VAT Notice 700/21 4.1 asks it for each description; the Nordic invoices and the Australian tax
# invoice print it the same way).
COUNTRY_LOCALE = {"NO": "nb-NO", "FI": "fi-FI", "AU": "en-AU", "CA": "en-CA", "US": "en-US", "GB": "en-GB",
                  "DK": "da-DK", "NL": "nl-NL", "AT": "de-AT", "IE": "en-IE", "ES": "es-ES", "IT": "it-IT",
                  "PL": "pl-PL"}
RATE_COLUMN = ("NO", "DK", "FI", "GB", "AU", "BE", "NL", "AT", "IE", "ES", "IT", "PL")
SYMBOL = {("GBP", "en-GB"): "£", ("AUD", "en-AU"): "$", ("USD", "en-US"): "$", ("CAD", "en-CA"): "$",
          ("CAD", "fr-CA"): "$", ("EUR", "fi-FI"): "€", ("EUR", "en-IE"): "€", ("EUR", "nl-NL"): "€",
          ("EUR", "nl-BE"): "€", ("EUR", "fr-BE"): "€", ("EUR", "de-BE"): "€", ("EUR", "de-AT"): "€",
          ("EUR", "es-ES"): "€", ("EUR", "it-IT"): "€", ("PLN", "pl-PL"): "zł"}
# CLDR's currency patterns: the euro after the amount with a no-break space in French, German (Belgium) and
# Finnish, before it with a no-break space in Dutch and Austrian German, close before it in English.
# Spanish, Italian and Polish too: 1234,56 €, 12.345,67 €, 1234,56 zł (CLDR 48).
AFTER = ("fr-CA", "fi-FI", "fr-BE", "de-BE", "es-ES", "it-IT", "pl-PL")
BEFORE_SPACED = ("nl-NL", "nl-BE", "de-AT")
NEW = ("NO", "DK", "FI", "GB", "AU", "CA", "US", "BE", "NL", "AT", "IE", "ES", "IT", "PL")


def covers(src):
    return countries.seller_country(src) in NEW


def place(p):
    """The town line of an address the country's way: post code first in the Nordics (0150 Oslo), after
    the town in the UK (Manchester M1 1AA), after the town and state in Australia, Canada and the US
    (Austin, TX 78701)."""
    return letter.town_line(p or {})          # one form for every pack: skills/_shared/letter.py


def money_text(amount_text, cur, locale):
    """£1,234.56 in Britain, $1,234.56 in Australia, Canada and the US, 1 234,56 $ in French Canada,
    1 234,56 € in Finland (CLDR's currency patterns); the code after the amount otherwise."""
    sym = SYMBOL.get((cur, locale))
    if not sym:
        return "%s %s" % (amount_text, cur)
    if locale in AFTER:
        return "%s %s" % (amount_text, sym)
    if locale in BEFORE_SPACED:
        return "%s %s" % (sym, amount_text)
    neg = amount_text.startswith("-")
    return ("-" if neg else "") + sym + amount_text.lstrip("-")


def pct_sep(locale):
    """CLDR's percent: 25 % with a space in Norwegian, Finnish and French, 25% in English."""
    if locale in ("fr-FR", "fr-BE"):
        return "\u202f%"
    # CLDR 48: 21 % in Spanish, 22% in Italian, 23% in Polish.
    return "\u00a0%" if locale in ("nb-NO", "fi-FI", "fr-CA", "da-DK", "de-BE", "de-AT", "es-ES") else "%"


def tax_name(name, locale):
    if locale == "fr-CA":
        for k, v in FR_CA_TAX.items():
            if name.upper().startswith(k):
                return v + name[len(k):]
    return name


def footer_tax(seller, locale, w):
    """The seller's identifiers in the footer, in the country's own form."""
    c = countries.country(seller)
    out = []
    if c == "NO":
        num = countries.org_number(seller, "NO")
        if num:
            mva = " MVA" if countries.vat_id(seller) else ""
            out.append("%s %s%s" % (w["vat_id"], ids.no_orgnr_text(num), mva))
        if countries.legal_form(seller).upper() in countries.NO_FORETAK:
            out.append(w["register"])
        if seller.get("registered_office"):
            out.append("%s: %s" % (w["office"], seller["registered_office"]))
    elif c == "DK":
        cvr = countries.org_number(seller, "DK")
        if cvr:
            out.append("%s %s" % (w["register_no"], ids.digits(cvr)))
        if seller.get("registered_office"):
            out.append("%s: %s" % (w["office"], seller["registered_office"]))
    elif c == "FI":
        yt = countries.org_number(seller, "FI")
        if yt:
            out.append("%s %s" % (w["tax_number"], yt))
        if countries.vat_id(seller):
            out.append("%s %s" % (w["vat_id"], countries.vat_id(seller)))
        if seller.get("registered_office"):
            out.append("%s %s" % (w["office"], seller["registered_office"]))
    elif c == "GB":
        if countries.vat_id(seller):
            out.append("%s %s" % (w["vat_id"], ids.gb_vat_text(countries.vat_id(seller))))
        if seller.get("register_number"):
            where = seller.get("registered_in") or seller.get("register") or ""
            out.append(("Registered in %s, company number %s" % (where, seller["register_number"])) if where
                       else "Company number %s" % seller["register_number"])
        if seller.get("registered_office"):
            out.append("Registered office: %s" % seller["registered_office"])
    elif c == "AU":
        if seller.get("acn"):
            # Corporations Act 2001 s 153(2): "ACN" and the number with the company's name on its invoices.
            acn = ids.digits(seller["acn"])
            out.append("ACN %s" % " ".join((acn[:3], acn[3:6], acn[6:])))
        if seller.get("abn"):
            out.append("ABN %s" % ids.au_abn_text(seller["abn"]))
    elif c == "CA":
        if seller.get("gst_number"):
            out.append("%s %s" % (w["vat_id"], ids.ca_gst_text(seller["gst_number"])))
        if seller.get("qst_number"):
            out.append("%s %s" % (w["qst"], ids.ca_qst_text(seller["qst_number"])))
    elif c == "US":
        if seller.get("sales_tax_permit"):
            out.append("%s %s" % (w["vat_id"], seller["sales_tax_permit"]))
    elif c == "BE":
        num = countries.org_number(seller, "BE")
        if num:
            # Royal Decree no. 1 art. 5 asks for the VAT number, the Code of companies and associations art.
            # 2:20 for the enterprise number and RPR/RPM with its court: the same ten digits, both named.
            out.append("%s %s" % (w["tax_number"], ids.be_enterprise_text(num)))
            out.append("%s %s" % (w["vat_id"], ids.be_vat_text(num)))
        if seller.get("register"):
            out.append(str(seller["register"]))
        if seller.get("registered_office"):
            # French sets a space before the colon (Siège : Liège).
            out.append("%s%s%s" % (w["office"], " : " if locale == "fr-BE" else ": ", seller["registered_office"]))
    elif c == "NL":
        if seller.get("vat_id"):
            out.append("%s %s" % (w["vat_id"], str(seller["vat_id"]).replace(" ", "").upper()))
        if countries.org_number(seller, "NL"):
            out.append("%s %s" % (w["tax_number"], ids.digits(countries.org_number(seller, "NL"))))
        if seller.get("registered_office"):
            out.append("%s: %s" % (w["office"], seller["registered_office"]))
    elif c == "AT":
        if countries.vat_id(seller):
            out.append("%s %s" % (w["vat_id"], countries.vat_id(seller)))
        if seller.get("register_number"):
            out.append(", ".join(x for x in (ids.at_fn_text(seller["register_number"]), seller.get("register")) if x))
        if seller.get("registered_office"):
            out.append("%s: %s" % (w["office"], seller["registered_office"]))
        directors = seller.get("managing_directors") or []
        if directors:
            out.append("Geschäftsführung: %s" % ", ".join([directors] if isinstance(directors, str) else directors))
    elif c == "IE":
        if seller.get("vat_id"):
            out.append("%s %s" % (w["vat_id"], str(seller["vat_id"]).replace(" ", "").upper()))
        if seller.get("register_number"):
            out.append("Registered in Ireland, company number %s" % seller["register_number"])
        if seller.get("registered_office"):
            out.append("Registered office: %s" % seller["registered_office"])
    elif c in ("ES", "IT", "PL"):
        # The tax number as the country prints it, then the company's particulars as its letters and trade
        # documents state them (skills/_shared/letter.py: Código de Comercio art. 24, Codice civile
        # art. 2250, Kodeks spółek handlowych art. 206 and 374), one writer for the whole library.
        if seller.get("vat_id"):
            form = {"ES": ids.es_nif, "IT": lambda v: "IT" + ids.it_piva(v), "PL": ids.pl_nip_text}[c]
            out.append("%s %s" % (w["vat_id"], form(seller["vat_id"])))
        if c == "IT" and seller.get("tax_code") and ids.digits(seller["tax_code"]) != ids.it_piva(seller.get("vat_id")):
            out.append("%s %s" % (w["tax_number"], seller["tax_code"]))
        rea = seller.get("rea") if isinstance(seller.get("rea"), dict) else {}
        if c == "IT" and rea.get("office") and rea.get("number"):
            out.append("REA %s-%s" % (str(rea["office"]).upper(), rea["number"]))
        if c == "PL" and seller.get("regon"):
            out.append("%s %s" % (w["tax_number"], seller["regon"]))
        # One of the two declared unknown: the register alone (Spain, Italy), or the Italian number with the
        # register's name and no office, so the page never prints a bare number nobody can place.
        reg, num = seller.get("register"), seller.get("register_number")
        alone = str(reg) if c in ("ES", "IT") and reg and not num else None
        if c == "IT" and num and not reg:
            alone = "Registro delle Imprese n. %s" % num
            seller = dict(seller, register_number=None)
        if c == "IT" and rea:
            # The REA block says whether the company has a sole shareholder or is in liquidation; art. 2250
            # wants both on the page.
            seller = dict(seller, sole_shareholder=seller.get("sole_shareholder") or rea.get("sole_shareholder"),
                          in_liquidation=seller.get("in_liquidation") or rea.get("in_liquidation"))
        lines = letter.company_lines(seller, locale)
        if alone:
            lines.insert(1 if seller.get("registered_office") else 0, alone)     # under the seat
        out += lines
    if c in ("NO", "BE"):
        out += liquidation_line(seller, locale)
    return out


# A company in liquidation says so on its invoices: Code de commerce R123-237 4°, the Belgian code art. 2:20
# 7°, aktiebolagslagen 28 kap. 5 §, bokføringsforskriften § 5-1-2 (Spain and Italy: letter.company_lines).
LIQUIDATION_WORDS = {"FR": "Société en liquidation", "SE": "I likvidation", "NO": "Under avvikling",
                     "BE": {"nl": "In vereffening", "fr": "En liquidation", "de": "In Liquidation"}}


def liquidation_line(seller, locale):
    if not seller.get("in_liquidation"):
        return []
    words = LIQUIDATION_WORDS.get(countries.country(seller))
    if isinstance(words, dict):
        words = words.get(str(locale)[:2], words["nl"])
    return [words] if words else []


def extra_mentions(src):
    """The mentions a seller's own law adds beside the reverse charge, in the words it fixes: Poland's
    „mechanizm podzielonej płatności” and „metoda kasowa” (ustawa o VAT art. 106e ust. 1 pkt 18a, 16), Italy's
    split payment and the annotation that stamp duty was paid (DM 17 giugno 2014 art. 6 comma 2)."""
    c = countries.seller_country(src)
    out = []
    if c == "PL":
        out += [countries.PL_SPLIT] if src.get("split_payment") else []
        out += [countries.PL_CASH] if src.get("cash_method") else []
    if c == "IT":
        out += [countries.IT_SPLIT] if src.get("split_payment") else []
        out += [countries.IT_STAMP] if src.get("stamp_duty") else []
    return out


def customer_id(buyer, locale, w, c):
    """The buyer's identifier in the information block: its org.nr. (with MVA when registered) in Norway,
    its VAT number in Denmark, Finland and the UK, its ABN in Australia."""
    bc = countries.country(buyer)
    if c == "NO":
        num = countries.org_number(buyer, "NO") if bc == "NO" else ""
        if num:
            return ids.no_orgnr_text(num) + (" MVA" if buyer.get("vat_id") else "")
        return buyer.get("vat_id")
    if c == "AU":
        return ids.au_abn_text(buyer["abn"]) if buyer.get("abn") else None
    if c in ("CA", "US"):
        return None
    if c == "ES" and bc == "ES" and ids.es_nif_form(buyer.get("vat_id")):
        return ids.es_nif(buyer["vat_id"])            # at home the NIF, as the footer writes the seller's
    if c == "PL" and bc == "PL" and ids.pl_nip_form(buyer.get("vat_id")):
        return ids.pl_nip_text(buyer["vat_id"])
    return countries.vat_id(buyer) or None


def bank_rows(src, locale, w):
    """How to pay, the country's way, as rows of key and value for the page's closing block: a Norwegian
    account and KID, a Danish registration and account number, a Finnish viitenumero, a British sort code and
    account, an Australian BSB, a structured communication, a Canadian or US bank with its routing or transit."""
    c = countries.seller_country(src)
    pay = src.get("payment") or {}
    out = []
    if c == "NO":
        if pay.get("account"):
            out.append((w["pay_to"], ids.no_account_text(pay["account"])))
        if pay.get("kid"):
            out.append((w["kid"], pay["kid"]))
    elif c == "DK":
        if pay.get("bank_reg") and pay.get("account"):
            out += [(w["bank_reg"], pay["bank_reg"]), (w["account_no"], pay["account"])]
    elif c == "FI":
        if pay.get("reference"):
            out.append((w["reference"], ids.fi_reference_text(pay["reference"])))
    elif c == "GB":
        if pay.get("sort_code") and pay.get("account"):
            out += [(w["sort_code"], pay["sort_code"]), (w["account_no"], pay["account"])]
    elif c == "AU":
        if pay.get("bsb") and pay.get("account"):
            out += [(w["bsb"], pay["bsb"]), (w["account_no"], pay["account"])]
    elif c in ("BE", "NL", "AT", "ES", "IT", "PL"):
        ref = pay.get("reference")
        if ref:
            out.append((w["reference"], ids.be_ogm_text(ref) if c == "BE" and ids.be_ogm_ok(ref) else str(ref)))
    elif c in ("CA", "US"):
        french = locale == "fr-CA"
        out += [("Banque" if french else "Bank", pay.get("bank")), ("Routing", pay.get("routing")),
                ("Transit", pay.get("transit")), ("Compte" if french else "Account", pay.get("account"))]
    return [(k, v) for k, v in out if v not in (None, "")]


def bank_lines(src, locale, w):
    """The same, one string a row: Sort code 12-34-56."""
    return ["%s %s" % row for row in bank_rows(src, locale, w)]


def sales_tax_rows(src, locale, w, money_of, plain=str):
    """[(label, amount)] for Canada and the United States: each tax once, named as the order names its
    jurisdiction, with its rate and the taxable base when not every line is taxed."""
    rows = []
    all_taxed = all(countries.taxable(l) for l in src.get("lines") or [])
    for name, rate, base, amount in countries.sales_taxes(src):
        rate_text = format(rate.normalize(), "f")
        if locale == "fr-CA":
            rate_text = rate_text.replace(".", ",")
        label = "%s %s%s" % (tax_name(name, locale), rate_text, pct_sep(locale))
        if not all_taxed:
            # The base as a plain amount, as the VAT pages write it: the currency belongs to the column.
            label = w["vat_on"] % (tax_name(name, locale), rate_text, plain(base)) if "%s %s" in w["vat_on"] \
                else label
        rows.append((label, money_of(amount)))
    return rows


def line_tax_word(line, src, locale, w):
    """The tax a Canadian or US line carries, so a mix of taxed and untaxed supplies is marked
    (SOR/91-45 s. 3(b)(ii))."""
    if not countries.taxable(line):
        return w.get("exempt", "Exempt")
    if countries.seller_country(src) == "US":
        return "Taxable"
    names = [tax_name(str(t.get("name") or ""), locale).split()[0] for t in src.get("taxes") or [] if t.get("name")]
    return ", ".join(dict.fromkeys(names)) or "—"


def sales_tax_total(src):
    return sum((t[3] for t in countries.sales_taxes(src)), Decimal(0))


def described(line, locale):
    """The line's name. Its discount stands under it (build_page.discount_row)."""
    return str(line.get("name", ""))