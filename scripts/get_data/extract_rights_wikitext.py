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

def normalize_whitespace(text: str) -> str:
    """Collapse irregular whitespace into single spaces.

    Useful when converting wikitext or HTML-like markup to plain text, where
    newlines, tabs, and repeated spaces can occur.

    Args:
        text: Input string (may be None or empty).

    Returns:
        A string with all runs of whitespace reduced to single spaces.
    """
    return " ".join((text or "").split())

def clean_text(wikicode: mw.wikicode.Wikicode) -> str:
    """Render mwparserfromhell `Wikicode` to plain text.

    Uses `strip_code(normalize=True, collapse=True)` and normalizes whitespace.

    Args:
        wikicode: Parsed wikitext node or text.

    Returns:
        Plain text with normalized whitespace.
    """
    text = mw.parse(str(wikicode or "")).strip_code(normalize=True, collapse=True)
    return normalize_whitespace(text)

def template_name(template: mw.nodes.Template) -> str:
    """Return a normalized template name for matching.

    Lowercases and removes an optional 'Template:' prefix.

    Args:
        template: A template node.

    Returns:
        The normalized template name (lowercase, prefix-stripped).
    """
    name = clean_text(template.name).lower()
    name = re.sub(r"^template\s*:\s*", "", name)
    return name

def is_info_template(name: str) -> bool:
    """Check whether a name matches an Information-like template.

    Args:
        name: Template name (any case).

    Returns:
        True if the name is in `INFO_TEMPLATES` or contains 'information'.
    """
    name = name.lower()
    return name in INFO_TEMPLATES or "information" in name

def get_param_value(template: mw.nodes.Template, param_names: set[str]) -> str | None:
    """Return the first non-empty value of any parameter in `param_names`.

    Parameter names are matched case-insensitively.

    Args:
        template: Template to inspect.
        param_names: Set of parameter names to try, e.g. {"author", "creator"}.

    Returns:
        The raw string value if found, otherwise None.
    """
    for param in template.params:
        param_name = clean_text(param.name).lower()
        if param_name in param_names:
            value = str(param.value).strip()
            if value:
                return value
    return None

# -------------------------------------------------------------
# Author detection helpers
# -------------------------------------------------------------

def detect_unknown_author(templates: list[mw.nodes.Template]) -> bool:
    """Detect usage of `{{Unknown|author}}` in a template list.

    Args:
        templates: Templates to scan (recursive extraction already applied).

    Returns:
        True if a template named 'Unknown' with value 'author' is present.
    """
    for template in templates:
        if str(template.name).strip().lower() != "unknown":
            continue
        for param in template.params:
            if clean_text(param.value).strip().lower() == "author":
                return True
    return False

def extract_creator_name(templates: list[mw.nodes.Template]) -> str | None:
    """Extract a name from `{{Creator:Name}}` transclusions.

    Args:
        templates: Templates to scan.

    Returns:
        The creator's name (string) if found, else None.
    """
    for template in templates:
        creator_text = str(template.name).strip()
        if creator_text.lower().startswith("creator:"):
            return normalize_whitespace(creator_text.split(":", 1)[1])
    return None

def collect_language_hits(templates: list[mw.nodes.Template]) -> list[tuple[str]]:
    """Collect (lang_code, text) pairs from language-wrapped templates.

    Handles:
      - `{{en|...}}`, `{{nl|1=...}}`
      - `{{lang|nl|...}}`
      - `{{lang-nl|...}}`

    Args:
        templates: Templates to scan.

    Returns:
        A list of (language_code, text) pairs, language code normalized to
        two/three-letter primary code (e.g., 'nl', 'en').
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
    """Select a text variant by preferred languages.

    Args:
        lang_hits: List of (language_code, text) pairs.
        preferred: Language preference tuple (default: ('nl','en')).

    Returns:
        The first matching text for the preferred languages, otherwise the
        first available text, or None if none found.
    """
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
    """Normalize an author field value extracted from a template.

    Resolution order:
      1) `{{Creator:Name}}` → 'Name'
      2) Language-wrapped values → pick preferred language
      3) `{{Unknown|author}}` → `UNKNOWN`
      4) Fallback: plain stripped text of the wikitext

    Args:
        value: Raw template value for the author-like field.

    Returns:
        A single-line author string (or empty string).
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
    """Return True if the template name signals a license template.

    Matches explicit names, or known prefixes (CC, PD, GFDL, etc.).

    Args:
        name: Template name.

    Returns:
        True if recognized as a license template, else False.
    """
    n = name.strip().lower()
    if n in LICENSE_EXACT:
        return True
    return any(n.startswith(prefix) for prefix in LICENSE_PREFIXES)

def normalize_license_name(name: str) -> str:
    """Normalize a license template name and map to a URI if possible.

    Lowercases, strips 'Template:' prefix, collapses whitespace, then
    passes the result to `get_license_uri`.

    Args:
        name: Template name or license-like token.

    Returns:
        Canonical license URI if recognized, otherwise the normalized text.
    """
    text = name.strip().lower()
    text = re.sub(r"^template\s*:\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return get_license_uri(text)

def license_from_self(template: mw.nodes.Template) -> list[str]:
    """Extract license URIs from a `{{Self|...}}` template.

    Iterates parameters, normalizes them, and returns all recognized
    license URIs (excluding the literal 'self').

    Args:
        template: The `Self` template node.

    Returns:
        List of license URI strings (may be empty).
    """
    results = []
    for param in template.params:
        val = normalize_license_name(clean_text(param.value))
        if val and val != "self":
            results.append(val)
    return results

def handle_gfdl(template: mw.nodes.Template) -> list[str]:
    """Process `{{GFDL}}` and `{{GFDL|migration=relicense}}`.

    If `migration=relicense`, returns the CC BY-SA 3.0 URI, otherwise GFDL.

    Args:
        template: The GFDL template node.

    Returns:
        A single-element list containing the license URI.
    """
    migration = get_param_value(template, {"migration"})
    if migration and clean_text(migration).lower() == "relicense":
        return [LICENSE_URI.get("ccbysa30")]
    return [LICENSE_URI.get("gfdl")]

def license_from_special_template(wikitext: str) -> str:
    """Return a license URI if wikitext matches a special-known template.

    Currently checks 'wikiportrait' and 'nationaal archief' and maps to
    known CC URIs.

    Args:
        wikitext: Template name or raw snippet.

    Returns:
        License URI string if detected, otherwise empty string.
    """
    text = wikitext.strip().lower()
    if any(text.startswith(template) for template in SPECIAL_TEMPLATES):
        if 'nationaal archief' in text:
            return LICENSE_URI["ccbysa30"]
        if 'wikiportrait' in text:
            return LICENSE_URI["ccby30"]
    return ""

def license_from_permission(permission_note: str) -> str:
    """Infer a license URI from a permission text field.

    Converts to a lowercase hyphenated token and checks against
    known keys in `LICENSE_URI`.

    Args:
        permission_note: Free-text permission field.

    Returns:
        License URI string if detected, otherwise empty string.
    """
    perm_lower = permission_note.lower().replace(" ", "-").split('/', maxsplit=1)[0]
    for key, _ in LICENSE_URI.items():
        if key.lower() in perm_lower:
            return get_license_uri(perm_lower)
    return ""

def get_unique_license(licenses: list[str]) -> str:
    """Choose a single license URI from a list of candidates.

    Rules:
      - If multiple, pick the most strict Creative Commons license using
        `get_most_strict_license`.
      - If exactly one and it's not GFDL, return it; if GFDL, map to CC BY-SA 3.0.
      - If none, return empty string.

    Args:
        licenses: Candidate license URIs/tokens.

    Returns:
        A single license URI (or empty string).
    """
    count = len(licenses)
    if count > 1:
        return get_most_strict_license(licenses)
    if count == 1:
        if "GFDL" not in licenses:
            return licenses[0]
        return LICENSE_URI.get('ccbysa30')
    return ""

def get_license_uri(text: str) -> str:
    """Map a license token to a canonical URI where possible.

    Handles:
      - Public domain variants (`pd`)
      - CC0 variants (`cc0`, `cc-zero`, `gencat`)
      - Creative Commons codes (delegates to `get_cc_uri`)
      - GFDL variants

    Args:
        text: License token or template-like name.

    Returns:
        Canonical URI string if recognized; otherwise returns the input text.
    """
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
    """Build a Creative Commons license URI from a normalized CC code.

    Logic:
      - Default version is 4.0 unless specified.
      - `-all` → 4.0
      - `-old` → 1.0
      - `3.0` or `3.0,2.5,2.0` → take the highest
      - Jurisdiction suffixes are dropped for canonical URIs.

    Args:
        text: Normalized CC code (e.g., 'cc-by-sa-4.0', 'cc-by-3.0-nl').

    Returns:
        A full CC license URI.
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
    """Return the strictest CC/PD-style license from a list.

    Order:
      - BY-SA (strictest)
      - BY
      - CC0 / Public Domain
    For ties, prefer the highest version number.

    Args:
        licenses: Candidate license URIs (or strings containing the code).

    Returns:
        The selected license URI.
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
    """Extract `author` and `license` from Commons wikitext.

    Scans all templates (recursively). For Information-like templates,
    extracts author and permission fields. For license templates, collects
    normalized license URIs. Applies special-cases and fallback matching.

    Args:
        wikitext: Raw Commons wikitext for a single file page.

    Returns:
        Dict with keys:
          - "author": extracted author string (may be empty or `UNKNOWN`)
          - "license": canonical license URI (may be empty if unknown)
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
    """CLI entry point.

    Reads `INPUT` CSV (expects a `Wikitext` column). For each row, parses and
    extracts `author` and `license`, appends them under the column names defined
    in `HEADER_OUTPUT_ROWS`, and writes the result to `OUTPUT`.

    Raises:
        FileNotFoundError: If `INPUT` does not exist.
        KeyError: If `WIKITEXT_COL` is missing in the CSV.
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
