"""What a form needs to know about each shipped scheme, shared by the command line, the demo page
and the downloadable examples: a label, the accepted format in words, a valid and an invalid
sample, and the keyboard to ask for."""
from __future__ import annotations

import html


def _s(title, shape, valid, invalid, letters=False):
    return {"title": title, "shape": shape, "valid": valid, "invalid": invalid, "letters": letters}


SCHEMES = {
    "luhn": _s("Luhn number", "Any number of digits, the last one a Luhn check digit.",
               "79927398713", "79927398712"),
    "card": _s("Payment card", "12 to 19 digits, the last one a Luhn check digit.",
               "4111111111111111", "4111111111111112"),
    "card16": _s("Payment card, 16 digits", "16 digits, the last one a Luhn check digit.",
                 "4111111111111111", "4111111111111112"),
    "imei": _s("IMEI", "15 digits, the last one a Luhn check digit.",
               "490154203237518", "490154203237512"),
    "sin": _s("Canadian SIN", "9 digits, the last one a Luhn check digit.",
              "046454286", "046454282"),
    "gtin": _s("GTIN", "Any number of digits, the last one a GTIN check digit (weights 3, 1).",
               "036000291452", "036000291453"),
    "ean8": _s("EAN-8 barcode", "8 digits, the last one a check digit.",
               "96385074", "96385072"),
    "upca": _s("UPC-A barcode", "12 digits, the last one a check digit.",
               "036000291452", "036000291453"),
    "ean13": _s("EAN-13 barcode", "13 digits, the last one a check digit.",
                "4006381333931", "4006381333932"),
    "isbn13": _s("ISBN-13", "978 or 979, then 10 digits, the last one a check digit.",
                 "9780306406157", "9780306406152"),
    "gtin14": _s("GTIN-14", "14 digits, the last one a check digit.",
                 "00012345600012", "00012345600013"),
    "aba": _s("US bank routing number", "9 digits, weights 3, 7, 1.",
              "011000015", "011000012"),
    "isbn10": _s("ISBN-10", "9 digits, then a check digit or a capital X (for 10).",
                 "080442957X", "0804429572", letters=True),
    "issn": _s("ISSN", "7 digits, then a check digit or a capital X (for 10).",
               "03785955", "03785952", letters=True),
    "bsn": _s("Dutch BSN", "9 digits that pass the elfproef.",
              "111222333", "111222332"),
    "iban_de": _s("German IBAN", "DE, 2 check digits, then 18 digits. Capitals, no spaces.",
                  "DE89370400440532013000", "DE89370400440532013002", letters=True),
    "iban_nl": _s("Dutch IBAN", "NL, 2 check digits, 4 capital letters, then 10 digits. No spaces.",
                  "NL91ABNA0417164300", "NL91ABNA0417164302", letters=True),
    "iban_gb": _s("UK IBAN", "GB, 2 check digits, 4 capital letters, then 14 digits. No spaces.",
                  "GB82WEST12345698765432", "GB82WEST12345698765433", letters=True),
    "iban_fr": _s("French IBAN", "FR, 2 check digits, then 23 characters: digits, and capitals in the account number. No spaces.",
                  "FR1420041010050500013M02606", "FR1420041010050500013M02602", letters=True),
    "iban": _s("IBAN, any country", "2 capitals for the country, 2 check digits, then the account number laid out as that country's IBANs are (15 to 33 characters in all). No spaces.",
               "GB82WEST12345698765432", "GB82WEST12345698765433", letters=True),
    "lei": _s("LEI (Legal Entity Identifier)", "18 digits or capitals, then 2 check digits. No spaces.",
              "506700GE1G29325QX363", "506700GE1G29325QX362", letters=True),
    "rf": _s("RF creditor reference", "RF, 2 check digits, then 1 to 21 digits or capitals: 5 to 25 characters. No spaces.",
             "RF18539007547034", "RF18539007547035", letters=True),
    "vin": _s("VIN (vehicle identification number)", "17 digits or capitals, no I, O or Q; the 9th is a check digit or X. North American and Chinese VINs have one; many European VINs do not.",
              "1M8GDM9AXKP042788", "1M8GDM9AXKP042789", letters=True),
    "dni": _s("Spanish DNI or NIE", "8 digits, or X, Y or Z and 7 digits, then a check letter. Capitals, no dash.",
              "54362315K", "54362315Z", letters=True),
    "hetu": _s("Finnish personal identity code (HETU)", "Date of birth as DDMMYY, a century sign (+, - or A, or one of the newer letters), a 3-digit number, then a check character. Capitals.",
               "131052-308T", "131052-308U", letters=True),
    "ogm": _s("Belgian structured communication", "12 digits, the last two a check number (OGM-VCS). Without the +++ and slashes.",
              "010806817183", "010806817184"),
    "nir": _s("French social security number (NIR)", "15 digits, the last two a check key; 2A or 2B for Corsica in the 6th and 7th. No spaces.",
              "295109912611193", "295109912611194", letters=True),
    "damm": _s("Damm check digit", "1 to 20 digits, the last one a Damm check digit.",
               "31415926535897932383", "31415926535897932384"),
    "verhoeff": _s("Verhoeff check digit", "1 to 20 digits, the last one a Verhoeff check digit.",
                   "2363", "2364"),
    "aadhaar": _s("Aadhaar number", "12 digits, not starting with 0 or 1, the last one a Verhoeff check digit. No spaces.",
                  "234123412346", "234123412347"),
}


def keyboard(name: str | None = None, letters: bool | None = None) -> str:
    """The attributes that pick the on-screen keyboard: digits only, or capitals as well."""
    if letters is None:
        letters = SCHEMES[name]["letters"]
    return 'autocapitalize="characters"' if letters else 'inputmode="numeric"'


def input_element(pattern: str, kb: str, extra: str = "") -> str:
    return f'<input {kb}{" " + extra if extra else ""} pattern="{html.escape(pattern, quote=True)}">'
