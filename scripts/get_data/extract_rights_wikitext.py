"""
Extract `author`, and `license` from Wikimedia Commons Wikitext
stored in a CSV column called 'Wikitext', using mwparserfromhell.

Usage:
    pip install mwparserfromhell pandas
    python extract_commons_author_license.py [INPUTFILE] [OUTPUTFILE]
"""

import re
from pathlib import Path
from sys import argv
import pandas as pd
import mwparserfromhell as mw

# --- I/O ---
INPUT  = Path(argv[1])            # CSV with a 'Wikitext' column
OUTPUT = Path(argv[2])

WIKITEXT_COL = "Wikitext"
PREFERRED_LANGS = ('nl', 'en')     # preferred languages for multi-language metadata fields
HEADER_OUTPUT_ROWS = {"license": 'profielfoto_licentie',
                      "author": 'profielfoto_maker'} #new column names

# --- Config ---
INFO_TEMPLATES = {
    "information", "artwork", "photograph", "book", "map",
    "art photo", "artphoto"
}
AUTHOR_ALIASES = {"author", "artist", "photographer", "creator", "by", "maker"}
PERMISSION_ALIASES = {"permission", "licence", "license"}

# License detection: exact names and prefixes commonly used on Commons
LICENSE_EXACT = {
    "cc0", "self", "gfdl", "gfdl-user", "attribution",
    "fal", "free-art-license", "pd", "pd-old", "pd-old-70",
    "pd-ineligible", "pd-us", "pd-textlogo"
}
LICENSE_PREFIXES = (
    "cc-by", "cc by", "cc-by-sa", "cc by-sa", "cc0", "pd", "gfdl",
    "creative commons", "cc-", "attribution-gencat"
)
# Dictionary to change the license names into URI's
LICENSE_URI = {
    "PD": "https://creativecommons.org/publicdomain/mark/1.0/",
    "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by": "https://creativecommons.org/licenses/",
    "gfdl": "GFDL",
    "ccby30": "https://creativecommons.org/licenses/by/3.0/",
    "ccbysa30": "https://creativecommons.org/licenses/by-sa/3.0/"
}

SPECIAL_TEMPLATES = {"wikiportrait", "nationaal archief"}

UNKNOWN = "Onbekend" # default value when a value is unknown

def normalize_whitespace(s: str) -> str:
    """
    When you extract text from Wikitext (or any HTML-like markup), you often end up with:
    - irregular spacing
    - newlines (`\n`)
    - tabs (`\t`)
    - multiple spaces between words
    This function collapses all of that into a single clean space.
    """
    return " ".join((s or "").split())

def clean_text(wikicode) -> str:
    """Render Wikicode to plain-ish text."""
    text = mw.parse(str(wikicode or "")).strip_code(normalize=True, collapse=True)
    return normalize_whitespace(text)

def template_name(template) -> str:
    """Lowercased, stripped template name (without 'Template:' prefix)."""
    name = clean_text(template.name).lower()
    name = re.sub(r"^template\s*:\s*", "", name)
    return name

def is_info_template(name: str) -> bool:
    """Checks if a template is an information template"""
    name = name.lower()
    return name in INFO_TEMPLATES or "information" in name

def get_param_value(template, names: set[str]):
    """Return first non-empty value for any parameter in names (case-insensitive)."""
    for param in template.params:
        param_name = clean_text(param.name).lower()
        if param_name in names:
            value = str(param.value).strip()
            if value:
                return value
    return None

def simplify_creator_lang(value: str, preferred_langs = PREFERRED_LANGS) -> str:
    """
    - If value uses {{Creator:Name}} (transclusion), return 'Name'.
    - If language wrappers are used ({{en|...}}, {{nl|1=...}}, {{lang|nl|...}}, {{lang-nl|...}})
      choose the best language according to preferred_langs
    - Otherwise, return plain-stripped text.
    """
    if not isinstance(value, str) or not value.strip():
        return ""

    wikicode = mw.parse(value or "")
    templates = list(wikicode.filter_templates(recursive=True))

    lang_hits = [] # list of (langcode, text)
    creator_name = None
    unknown_author = False

    for template in templates:
        name = str(template.name).strip()
        name_lower = name.lower()

        # search for unknown|author
        if name_lower == "unknown":
            for param in template.params:
                if clean_text(param.value).strip().lower() == "author":
                    unknown_author = True
                    break
                if unknown_author:
                    break # no checks necessary

        # search for Creator:Naam
        if name_lower.startswith("creator:"):
            # everything after 'creator:' is the display name
            creator_name = normalize_whitespace(name.split(":", 1)[1])
            # further checks necessary, unknown|author is still possible
            continue

    # Collect language wrappers {{en|...}} or {{nl|1=...}} or {{fr|...}} etc.
        if re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]+)?", name_lower):
            if template.params:
                value = None
                # take "1" or first param
                for param in template.params:
                    if clean_text(param.name) in ("1", ""):
                        value = param.value
                        break
                if value is None:
                    value = template.params[0].value

                lang_code = name_lower.split("-", 1)[0]  # en-gb → en
                lang_hits.append((lang_code, clean_text(value)))
            continue

        # {{lang|nl|tekst}}
        if name_lower == "lang" and len(template.params) >= 2:
            lang_code = clean_text(template.params[0].value).lower().split("-", 1)[0]
            text_value = clean_text(template.params[1].value)
            lang_hits.append((lang_code, text_value))
            continue

        # {{lang-nl|tekst}}
        if name.startswith("lang-") and len(template.params) >= 1:
            lang_code = name.split("-", 1)[1].split("-", 1)[0]
            text_value = clean_text(template.params[0].value)
            lang_hits.append((lang_code, text_value))
            continue

    # scenario 1: author without language codes
    if creator_name:
        return creator_name

    # scenario 2: author with multi-language values
    # choose preferred language (nl → en → eerste andere)
    if lang_hits:
        for pref in preferred_langs:
            for language_code, text in lang_hits:
                if language_code == pref and text:
                    return text
        #fallback to any other language if preferred language is not there
        for _, text in lang_hits:
            if text:
                return text

    # scenario 3: author is unknown
    if unknown_author:
        return UNKNOWN

    # Fallback to cleaned text
    return clean_text(wikicode)

def is_license_template(name: str) -> bool:
    """Checks if the template is a template for the license"""
    n = name.strip().lower()
    if n in LICENSE_EXACT:
        return True
    return any(n.startswith(prefix) for prefix in LICENSE_PREFIXES)

def normalize_license_name(name: str) -> str:
    """Returns a clean text of the license"""
    n = name.strip().lower()
    n = re.sub(r"^template\s*:\s*", "", n)
    n = re.sub(r"\s+", " ", n)
    uri = get_license_uri(n)
    return uri

def get_license_uri(name: str) -> str:
    """Returns the URI of the license"""
    if "pd" in name:
        return LICENSE_URI.get('PD')
    if "cc-zero" in name:
        return LICENSE_URI.get('cc-zero')
    if "cc-" in name:
        if name.endswith('sa'):
            name += "-4.0"
        if name.endswith('all'):
            name = 'cc-by-sa-4.0'
        if not (name[-1].isdigit() or name.split('-')[-1] == 'old'):
            end = name.rfind('-')
            name = name[:end]
        start = name.find('-') +1
        end = name.rfind('-')
        version = name.split('-')[-1]
        if version == 'old':
            version = '1.0'
        if ',' in version:
            versions = version.split(',')
            version = max(versions)
        license_options = name[start:end]
        return f"{LICENSE_URI.get("cc-by")}{license_options}/{version}/"
    if "gfdl" in name:
        return LICENSE_URI.get(name)
    if "gencat" in name:
        return LICENSE_URI.get('cc-zero')
    return name

def get_most_strict_license(licenses: list[str]) -> str:
    """
    Keep max 1 Creative commons license that is the most strict:
    cc-by-sa > cc-by > cc0/pd
    If licenses are even strict, keep the most recent version (4.0 > 3.0)
    """
    print(licenses)
    cc_pd = []

    for lic in licenses:
        l = (lic or "").lower()
        if "by" in l or "zero" in l or "publicdomain" in l:
            cc_pd.append(lic)

    def strictness_key(lic: str):
        l = lic.lower()

        if 'by-sa' in l:
            level = 3
        elif 'by' in l:
            level = 2
        elif 'zero' in l or 'publicdomain' in l:
            level = 1
        else:
            level = 0

        version = float(lic[:-1].split('/')[-1])
        print(level,version)
        return (level, version)
    
    print(cc_pd)
    best_license = max(cc_pd, key=strictness_key)

    return best_license

def is_special_template(wikitext:str) -> bool:
    """Check if a license is hidden in a special template"""
    n = wikitext.strip().lower()
    return any(n.startswith(template) for template in SPECIAL_TEMPLATES)

def extract_from_wikitext(wikitext: str) -> dict:
    """
    Parse Commons wikitext and extract:
    - author: from Information/Artwork-like templates (author/artist/photographer/creator/by/maker)
    - license: from license templates (including {{Self|...}} parameters)
    """
    author = ""
    permission_note = ""
    licenses = []
    special = ""

    code = mw.parse(wikitext or "")

    # 1) Walk all templates (recursive=True to catch deeply-nested ones)
    for template in code.filter_templates(recursive=True):
        name = template_name(template)

        # Information-like templates → author / permission
        if is_info_template(name):
            raw_author = get_param_value(template, AUTHOR_ALIASES)
            if raw_author and not author:
                author = simplify_creator_lang(raw_author)
            raw_perm = get_param_value(template, PERMISSION_ALIASES)
            if raw_perm and not permission_note:
                permission_note = clean_text(raw_perm)

        # Special case: {{Self|cc-by-sa-4.0|...}}
        if name == "self":
            for p in template.params:
                # param values of Self are usually license tokens
                val = normalize_license_name(clean_text(p.value))
                if val and val != "self":
                    licenses.append(val)
            continue

        # License templates → template itself indicates license
        if is_license_template(name):
            licenses.append(normalize_license_name(name))
        elif is_special_template(name.lower()):
            print("this is something special")
            if 'nationaal archief' in name.lower():
                special = LICENSE_URI["ccbysa30"]
            if 'wikiportrait' in name.lower():
                special = LICENSE_URI["ccby30"]

    # 2) Deduplicate licenses while preserving order
    seen = set()
    uniq_licenses = []
    for lic in licenses:
        if lic and lic != "self" and lic not in seen:
            seen.add(lic)
            uniq_licenses.append(lic)

    if len(uniq_licenses) > 1:
        uniq_license = get_most_strict_license(uniq_licenses)
    if len(uniq_licenses) == 0:
        uniq_license = ""
    else:
        if "GFDL" not in uniq_licenses:
            uniq_license = uniq_licenses[0]
        else:
            uniq_license = LICENSE_URI['ccbysa30']

    if permission_note and uniq_license == "":
        perm_lower = permission_note.lower().replace(" ", "-").split('/', maxsplit=1)[0]
        for key, _ in LICENSE_URI.items():
            if key.lower() in perm_lower:
                uniq_license = get_license_uri(perm_lower)
                break

    if special != "" and uniq_license == "":
        uniq_license = special

    return {
        "license": uniq_license,
        "author": author
    }

def main():
    """
    main logic of script
    this method starts every other method in script in the correct order
    """
    if not INPUT.exists():
        raise FileNotFoundError(f"CSV not found: {INPUT}")

    df = pd.read_csv(INPUT)
    df = df.fillna('')
    if WIKITEXT_COL not in df.columns:
        raise KeyError(f"CSV must contain a '{WIKITEXT_COL}' column.")

    out = df[WIKITEXT_COL].apply(extract_from_wikitext)
    out_df = pd.concat([df, pd.DataFrame(list(out)).rename(columns=HEADER_OUTPUT_ROWS)], axis=1)
    out_df.to_csv(OUTPUT, index=False)
    print(f"✅ Wrote: {OUTPUT}")
    # Optional tiny preview
    #print(out_df[[HEADER_OUTPUT_ROWS.get("author"), HEADER_OUTPUT_ROWS.get("license")]].head(20).to_string(index=False))

if __name__ == "__main__":
    main()
