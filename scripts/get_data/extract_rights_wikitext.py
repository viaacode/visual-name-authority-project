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

# -------------------------------------------------------------
# Basic helpers
# -------------------------------------------------------------

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
    """
    Lowercased, stripped template name (without 'Template:' prefix).
    This method is only used for matching in some cases
    """
    name = clean_text(template.name).lower()
    name = re.sub(r"^template\s*:\s*", "", name)
    return name

def is_info_template(name: str) -> bool:
    """Checks if a template is an information template"""
    name = name.lower()
    return name in INFO_TEMPLATES or "information" in name

def get_param_value(template: mw.nodes.Template, names: set[str]) -> str | None:
    """Return first non-empty value for any parameter in names (case-insensitive)."""
    for param in template.params:
        param_name = clean_text(param.name).lower()
        if param_name in names:
            value = str(param.value).strip()
            if value:
                return value
    return None

# -------------------------------------------------------------
# Author detection helpers
# -------------------------------------------------------------

def detect_unknown_author(templates: list[mw.nodes.Template]) -> bool:
    """Detect {{Unknown|author}} templates in Wikitext"""
    for template in templates:
        if str(template.name).strip().lower() != "unknown":
            continue
        for param in template.params:
            if clean_text(param.value).strip().lower() == "author":
                return True
    return False

def extract_creator_name(templates: list[mw.nodes.Template]) -> str | None:
    """Extract the creator name in {{Creator:Name}} templates in Wikitext"""
    for template in templates:
        creator_text = str(template.name).strip()
        if creator_text.lower().startswith("creator:"):
            return normalize_whitespace(creator_text.split(":", 1)[1])
    return None

def collect_language_hits(templates: list[mw.nodes.Template]) -> list[tuple[str]]:
    """
    Collect text wrapped in lanuage templates, e.g. {{en|...}}, {{nl|1=...}},
    {{lang|nl|...}}, {{lang-nl|...}}.
    """

    results = []

    for template in templates:
        # template_name is used because the original template name is not used,
        # and only the language code is needed
        name = template_name(template)
        params = template.params

        # {{en|...}} / {{nl|1=...}}
        if re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]+)?", name):
            val = None
            for param in params:
                if clean_text(param.name) in ("", "1"):
                    val = param.value
                    break
            if val is None and params:
                val = params[0].value
            if val:
                results.append((name.split("-", 1)[0], clean_text(val)))
            continue

        if name == "lang" and len(params) >= 2:
            lang_code = clean_text(params[0].value).lower().split("-", 1)[0]
            text_val = clean_text(params[1].value)
            results.append((lang_code, text_val))
            continue

        if name.startswith("lang-") and params:
            lang_code = name.split("-", 1)[1].split("-", 1)[0]
            text_val = clean_text(params[0].value)
            results.append((lang_code, text_val))

    return results

def choose_language_text(lang_hits: list[tuple[str]], preferred=PREFERRED_LANGS) -> str | None:
    """If there are multilanguage values, choose the language that is preferred"""
    if not lang_hits:
        return None

    for pref in preferred:
        for lang_code, text in lang_hits:
            if lang_code == pref and text:
                return text

    for _, text in lang_hits:
        if text:
            return text

    return None

def simplify_author_field(value: str) -> str:
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

    # scenario 1: author without language codes
    creator_name = extract_creator_name(templates)
    if creator_name:
        return creator_name

    # scenario 2: author with multi-language values
    # choose preferred language (nl → en → eerste andere)
    lang_hits = collect_language_hits(templates)
    lang_text = choose_language_text(lang_hits)
    if lang_text:
        return lang_text

    # scenario 3: author is unknown
    if detect_unknown_author(templates):
        return UNKNOWN

    # Fallback to cleaned text
    return clean_text(wikicode)

# -------------------------------------------------------------
# License helpers
# -------------------------------------------------------------

def is_license_template(name: str) -> bool:
    """Checks if the template is a template for the license"""
    n = name.strip().lower()
    if n in LICENSE_EXACT:
        return True
    return any(n.startswith(prefix) for prefix in LICENSE_PREFIXES)

def normalize_license_name(name: str) -> str:
    """Returns a clean text of the license"""
    text = name.strip().lower()
    text = re.sub(r"^template\s*:\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return get_license_uri(text)

def license_from_self(template: mw.nodes.Template) -> list[str]:
    """Get license form {{Self|license|...}} template"""
    results = []
    for param in template.params:
        val = normalize_license_name(clean_text(param.value))
        if val and val != "self":
            results.append(val)
    return results

def handle_gfdl(template:mw.nodes.Template) -> list[str]:
    """Change {{GFDL|migration}} into canonical URI of cc-by-sa-3.0"""
    migration = get_param_value(template, {"migration"})
    if migration and clean_text(migration).lower() == "relicense":
        return [LICENSE_URI.get("ccbysa30")]
    return [LICENSE_URI.get("gfdl")]

def license_from_special_template(wikitext: str) -> str:
    """
    Check if a license is hidden in a special template
    and return the URI of the license
    """
    text = wikitext.strip().lower()
    if any(text.startswith(template) for template in SPECIAL_TEMPLATES):
        if 'nationaal archief' in text:
            return LICENSE_URI["ccbysa30"]
        if 'wikiportrait' in text:
            return LICENSE_URI["ccby30"]
    return ""

def license_from_permission(permission_note: str) -> str:
    """
    Check if a license is hidden in a permission field
    and return the URI of the license
    """
    perm_lower = permission_note.lower().replace(" ", "-").split('/', maxsplit=1)[0]
    for key, _ in LICENSE_URI.items():
        if key.lower() in perm_lower:
            return get_license_uri(perm_lower)
    return ""

def get_unique_license(licenses: list[str]) -> str:
    """Return one license from the list of licenses"""
    count = len(licenses)
    if count > 1:
        return get_most_strict_license(licenses)
    if count == 1:
        if "GFDL" not in licenses:
            return licenses[0]
        return LICENSE_URI.get('ccbysa30')
    return ""

def get_license_uri(text: str) -> str:
    """Returns the canonical URI of the license"""
    text_lower = text.strip().lower()

    # public domain variants
    if "pd" in text_lower:
        return LICENSE_URI.get('PD')

    # CC0 veriants
    if "cc-zero" in text_lower or text_lower.startswith('cc0') or "gencat" in text_lower:
        return LICENSE_URI.get('cc-zero')

    # CC licensens
    if "cc-" in text:
        return get_cc_uri(text_lower)

    #GFDL variants
    if "gfdl" in text_lower:
        return LICENSE_URI.get(text, LICENSE_URI.get("GFDL"))

    return text

def get_cc_uri(text: str) -> str:
    """
    Build a Creative Commons license URI from a normalized CC code.

    Handles:
    - cc-by-sa → default 4.0
    - cc-by → default 4.0
    - cc-by-sa-3.0
    - cc-by-sa-all → cc-by-sa-4.0
    - cc-by-sa-old → version 1.0
    - cc-by-sa-3.0,4.0 → highest version (4.0)
    - cc-by-3.0-nl → juridisction nl 
    """
    base = LICENSE_URI.get('cc-by')
    parts = text.split('-')
    # handle templates that contain a jurisdiction code
    if not (parts[-1][-1].isdigit() or (parts[-1] == "old" or parts[-1] == "all")):
        parts = parts[:-1]

    last = parts[-1]
    version = "4.0"
    options = "-".join(parts[1:-1]) or "by"

    # handle templates that contain a certain version
    if last == "old":
        version = "1.0"
    elif last == "all":
        version = "4.0"
    # e.g. 3.0 or 3.0,2.5,2.0
    elif re.fullmatch(r"\d+(?:\.\d+)?(?:,\d+(?:\.\d+)?)*", last):
        if "," in last:
            versions = last.split(",")
            version = max(versions)
        else:
            version = last
    # when version not added to template
    else:
        options = '-'.join(parts[1:]) or "by"

    #return canonical URI
    return f"{base}{options}/{version}/"

# license selection
def get_most_strict_license(licenses: list[str]) -> str:
    """
    Keep max 1 Creative commons license that is the most strict:
    cc-by-sa > cc-by > cc0/pd
    If licenses are even strict, keep the most recent version (4.0 > 3.0)
    """
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
        return (level, version)
    
    best_license = max(cc_pd, key=strictness_key)

    return best_license

# -------------------------------------------------------------
# Extractor
# -------------------------------------------------------------

def extract_from_wikitext(wikitext: str) -> dict:
    """
    Parse Commons wikitext and extract:
    - author: from Information/Artwork-like templates (author/artist/photographer/creator/by/maker)
    - license: from license templates (including {{Self|...}} parameters)
    """
    author = ""
    permission_note = ""
    licenses: list[str] = []
    special_license = None

    code = mw.parse(wikitext or "")

    # 1) Walk all templates (recursive=True to catch deeply-nested ones)
    for template in code.filter_templates(recursive=True):
        name = template_name(template)

        # Information-like templates → author / permission
        if is_info_template(name):
            if not author:
                raw_author = get_param_value(template, AUTHOR_ALIASES)
                if raw_author:
                    author = simplify_author_field(raw_author)
            if not permission_note:
                raw_perm = get_param_value(template, PERMISSION_ALIASES)
                if raw_perm:
                    permission_note = clean_text(raw_perm)
            continue

        # Special case: {{Self|cc-by-sa-4.0|...}}
        if name == "self":
            licenses.extend(license_from_self(template))
            continue

        # Handle {{GFDL|migration=relicense}}
        if name == "gfdl":
            licenses.extend(handle_gfdl(template))

        # License templates → template itself indicates license
        if is_license_template(name):
            licenses.append(normalize_license_name(name))

        # Licenses insides special templates
        special_license = license_from_special_template(name)

    # 2) Deduplicate licenses while preserving order
    seen = set()
    uniq_licenses = []
    for lic in licenses:
        if lic and lic != "self" and lic not in seen:
            seen.add(lic)
            uniq_licenses.append(lic)

     # 3) Return the bestest license
    uniq_license = get_unique_license(uniq_licenses)

    if permission_note and uniq_license == "":
        # check if license is recorded in permission field
        uniq_license = license_from_permission(permission_note)

    if uniq_license == "" and special_license:
        # check if license is hidden in a special template
        uniq_license = special_license

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
