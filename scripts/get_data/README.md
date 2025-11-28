# Scripts

## extract_rights_wikitext.pyt

Extract `author` and `license` from Wikimedia Commons Wikitext

This script reads a CSV file with a column named `Wikitext`, parses the wikitext using **mwparserfromhell**, and extracts:

* `author` — from Information/Artwork-like templates (e.g., `author`, `artist`, `photographer`, `creator`, `by`, `maker`) with support for language wrappers and `{{Creator:Name}}` transclusions.
* `license` — from license templates (e.g., Creative Commons, PD, GFDL), {{Self|…}} parameters, special templates, and (as a fallback) permission notes.

The extracted values are appended as **new columns** to the input rows and written to a new CSV.

### Requirements

* Python 3.9+ (recommended)
* Packages:
    * `mwparserfromhell`
    * `pandas`

Install:
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install mwparserfromhell pandas
```

### Input

* A CSV file containing a column named `Wikitext` whose cells hold the raw Commons wikitext of the file pages.

Example minimal CSV:
```csv
Wikitext
"{{Information|author={{Creator:Jane Doe}}|permission={{CC-BY-SA-4.0}}}}"
"{{Information|author={{en|1=John Smith}}|permission=PD}}"
```

### Usage

```bash
python extract_commons_author_license.py INPUT.csv OUTPUT.csv
```

* `INPUT.csv` – CSV with a `Wikitext` column
* `OUTPUT.csv` – output CSV; script appends derived columns and writes the result

### Output

The script writes a CSV to `OUTPUT.csv` that includes all original columns plus:

* `profielfoto_maker` — extracted author/creator (mapped from author)
* `profielfoto_licentie` — extracted license URI (mapped from license)

Column names are controlled by `HEADER_OUTPUT_ROWS` in the script:

```python
HEADER_OUTPUT_ROWS = {
  "license": 'profielfoto_licentie',
  "author":  'profielfoto_maker'
}
```

### How it works (high-level)

1. **Parse wikitext** with `mwparserfromhell`
2. **Author extraction:**
    * Reads from Information-like templates (`author`, `artist`, `photographer`, `creator`, `by`, `maker`).
    * Supports `{{Creator:Name}}`.
    * Supports language wrappers (`{{en|…}}`, `{{nl|1=…}}`, `{{lang|nl|…}}`, `{{lang-nl|…}}`) and picks from preferred languages (default `nl`, then `en`).
    * Detects `{{Unknown|author}}`.
3. **License extraction:**
    * Detects standard license templates and common prefixes (`CC`, `PD`, `GFDL`).
    * Interprets `{{Self|…}}` parameters.
    * Handles GFDL migration (`{{GFDL|migration=relicense}} → cc-by-sa-3.0` URI).
    * Looks for special templates (e.g., `wikiportrait`, `nationaal archief`).
    * Falls back to a permission note if needed.
    * Normalizes to `canonical URIs` when possible.
4. **Write** merged dataframe to CSV.

### Notes & limits

* The license mapping (`LICENSE_URI`) is partial and can be extended.
* Wikitext on Commons is diverse; edge cases may require tuning the template and alias sets.
* If multiple licenses are present, the script selects the “most strict” Creative Commons license (BY-SA > BY > CC0/PD) and the highest version where relevant.