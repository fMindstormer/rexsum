"""Every country in the IBAN registry, with its BBAN layout in the registry's notation (n a digit,
a a capital letter, c either): SWIFT's IBAN Registry, release 101, as python-stdnum 2.2 ships it
(stdnum/iban.dat). Regenerate from a newer release when countries are added."""

REGISTRY = {
    "AD": "4n4n12c",           # Andorra
    "AE": "3n16n",             # United Arab Emirates (The)
    "AL": "8n16c",             # Albania
    "AT": "5n11n",             # Austria
    "AZ": "4a20c",             # Azerbaijan
    "BA": "3n3n8n2n",          # Bosnia and Herzegovina
    "BE": "3n7n2n",            # Belgium
    "BG": "4a4n2n8c",          # Bulgaria
    "BH": "4a14c",             # Bahrain
    "BI": "5n5n11n2n",         # Burundi
    "BR": "8n5n10n1a1c",       # Brazil
    "BY": "4c4n16c",           # Belarus
    "CH": "5n12c",             # Switzerland
    "CR": "4n14n",             # Costa Rica
    "CY": "3n5n16c",           # Cyprus
    "CZ": "4n16n",             # Czechia
    "DE": "8n10n",             # Germany
    "DJ": "5n5n11n2n",         # Djibouti
    "DK": "4n9n1n",            # Denmark
    "DO": "4c20n",             # Dominican Republic
    "EE": "2n14n",             # Estonia
    "EG": "4n4n17n",           # Egypt
    "ES": "4n4n1n1n10n",       # Spain
    "FI": "3n11n",             # Finland
    "FK": "2a12n",             # Falkland Islands (Malvinas)
    "FO": "4n9n1n",            # Faroe Islands
    "FR": "5n5n11c2n",         # France
    "GB": "4a6n8n",            # United Kingdom
    "GE": "2a16n",             # Georgia
    "GI": "4a15c",             # Gibraltar
    "GL": "4n9n1n",            # Greenland
    "GR": "3n4n16c",           # Greece
    "GT": "4c20c",             # Guatemala
    "HN": "4a20n",             # Honduras
    "HR": "7n10n",             # Croatia
    "HU": "3n4n1n15n1n",       # Hungary
    "IE": "4a6n8n",            # Ireland
    "IL": "3n3n13n",           # Israel
    "IQ": "4a3n12n",           # Iraq
    "IS": "4n2n6n10n",         # Iceland
    "IT": "1a5n5n12c",         # Italy
    "JO": "4a4n18c",           # Jordan
    "KW": "4a22c",             # Kuwait
    "KZ": "3n13c",             # Kazakhstan
    "LB": "4n20c",             # Lebanon
    "LC": "4a24c",             # Saint Lucia
    "LI": "5n12c",             # Liechtenstein
    "LT": "5n11n",             # Lithuania
    "LU": "3n13c",             # Luxembourg
    "LV": "4a13c",             # Latvia
    "LY": "3n3n15n",           # Libya
    "MC": "5n5n11c2n",         # Monaco
    "MD": "2c18c",             # Moldova, Republic of
    "ME": "3n13n2n",           # Montenegro
    "MK": "3n10c2n",           # North Macedonia
    "MN": "4n12n",             # Mongolia
    "MR": "5n5n11n2n",         # Mauritania
    "MT": "4a5n18c",           # Malta
    "MU": "4a2n2n12n3n3a",     # Mauritius
    "NI": "4a20n",             # Nicaragua
    "NL": "4a10n",             # Netherlands (The)
    "NO": "4n6n1n",            # Norway
    "OM": "3n16c",             # Oman
    "PK": "4a16c",             # Pakistan
    "PL": "8n16n",             # Poland
    "PS": "4a21c",             # Palestine, State of
    "PT": "4n4n11n2n",         # Portugal
    "QA": "4a21c",             # Qatar
    "RO": "4a16c",             # Romania
    "RS": "3n13n2n",           # Serbia
    "RU": "9n5n15c",           # Russian Federation
    "SA": "2n18c",             # Saudi Arabia
    "SC": "4a2n2n16n3a",       # Seychelles
    "SD": "2n12n",             # Sudan
    "SE": "3n16n1n",           # Sweden
    "SI": "5n8n2n",            # Slovenia
    "SK": "4n6n10n",           # Slovakia
    "SM": "1a5n5n12c",         # San Marino
    "SO": "4n3n12n",           # Somalia
    "ST": "4n4n11n2n",         # Sao Tome and Principe
    "SV": "4a20n",             # El Salvador
    "TL": "3n14n2n",           # Timor-Leste
    "TN": "2n3n13n2n",         # Tunisia
    "TR": "5n1n16c",           # Turkiye
    "UA": "6n19c",             # Ukraine
    "VA": "3n15n",             # Holy See
    "VG": "4a16n",             # Virgin Islands (British)
    "XK": "4n10n2n",           # Kosovo
    "YE": "4a4n18c",           # Yemen
}
