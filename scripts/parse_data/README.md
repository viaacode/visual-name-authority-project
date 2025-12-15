# Scripts for parsindg data

## extract_rights_wikitext.py — Extract `author` and `license` from Wikimedia Commons Wikitext

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

## parse_avg.py - AVG XML → VNA CSV Converter

This script parses an EAC-CPF XML export from Archief voor Vrouwengeschiedenis (AVG) and converts selected fields to the Visual Name Authority (VNA) CSV format using the shared `scripts.person` utilities.

For each `<eac-cpf>` record, the script extracts:
* **Name**: last/first from `identity/nameEntry` (expects `"Last, First"`), builds full name.
* **Alias**: from `identity/nameEntryParallel` (expects `"Last, First"`; optional).
* **Dates**: birth and death, split from a single string (e.g., `"1 janvier 1900 - 2 février 1980"`) found under `description/existDates/dateRange`. Dates are parsed with the **French** locale and emitted as **ISO** (`YYYY-MM-DD`).
* **Pictures**: IDs gathered from `relations/resourceRelation` attribute `id_carhif`, accumulated into a comma-separated string.

The resulting list of `Person` objects is written as a VNA-compatible CSV via `write_csv`.

### Requirements

* **Python** 3.9+ (recommended)
* **Local project module**: `scripts.person` (must be importable from repo root)
* **System locale**: a **French** locale (e.g. `fr_FR` or `fr_FR.UTF-8`) must be available for date parsing

> If `locale.setlocale(locale.LC_ALL, 'fr_FR')` fails on your system, install/enable a French locale or adjust the locale code in `format_date()` to one that exists (e.g., `'fr_FR.UTF-8'` on many Linux distributions).

### Input: expected XML structure (paths)

The script uses these XPath-like selectors:
```
eac-cpf
 └─ cpfDescription
     ├─ identity
     │   ├─ nameEntry                (text: "Last, First")
     │   └─ nameEntryParallel        (text: "Last, First")  [optional]
     ├─ description
     │   └─ existDates
     │       └─ dateRange            (text: "DD MMMM YYYY - DD MMMM YYYY")
     └─ relations
         └─ resourceRelation         (@id_carhif = picture ID)
```

The attribute name for picture IDs is `id_carhif`.

### Usage

```bash
python avg_to_vna.py /path/to/avg.xml /path/to/output.csv
```

* `argv[1]` = `FILE`: path to the EAC-CPF XML
* `argv[2]` = `OUTPUT`: destination CSV path

The script will write the standard VNA header and one row per parsed person.

### Notes & assumptions

* **Name parsing**: expects `"Last, First"` strings; the first comma splits last/first.
* **Dates**: expects a **single** line in French, with a hyphen separating birth and death (death side may be missing). Examples:
`1 janvier 1900 - 2 février 1980`, `15 mars 1920 -`.
* **Pictures**: the script removes slashes from `id_carhif` values and joins multiple IDs with commas; trailing comma is removed via `beautify_string`.
* **Encoding**: ElementTree will read XML encoding as declared; CSV is written by `write_csv` in UTF-8.
* **Project import**: the script prepends the repo root to `sys.path` to import `scripts.person`.

## parse_letterenhuis.py - Letterenhuis XML → VNA CSV Converter

This script parses **Letterenhuis** XML authority files and converts selected fields to the **Visual Name Authority (VNA)** CSV format using the shared `scripts.person` helpers.

For each XML file in a folder, it extracts:

- **Names**
  - First name: `Names/RestOfName`
  - Last name: `Names/PrimaryName`
  - Optional suffix appended to first name: `Names/Suffix`
  - Aliases (where `Names/Qualifier` is present): stored as `"First [Suffix] Last"`, multiple values comma-separated
- **Dates of existence**
  - Birth/death from:
    - `DatesOfExistence/StructuredDateRange/BeginDateStandardized` & `EndDateStandardized`, or
    - `DatesOfExistence/StructuredDateSingle[DateRole=begin|end]/DateStandardized`
- **Places**
  - Birth place: `AgentPlaces[PlaceRole='place_of_birth']/Subjects/Ref`
  - Death place: `AgentPlaces[PlaceRole='place_of_death']/Subjects/Ref`
- **Occupation**
  - One or more notes at `AgentOccupations/Notes/Content/String`, concatenated (commas) and with literal `\r\n` converted to commas
- **External identifiers & picture**
  - `ExternalDocuments`:
    - If `Title` contains `dams.antwerpen.be`, treat `Location` as a **picture** URL
    - Otherwise, map `Title` → `{dbnl|odis|wikidata|viaf|rkd}` and extract the identifier from `Location` (after the last `=` or last `/`)

The resulting `Person` objects are written to a VNA-compatible CSV via `write_csv`.

### Requirements

- **Python** 3.9+ (recommended)
- **Python packages**
  - `python-dotenv` (to load the input folder from `.env`)
- **Local project module**
  - `scripts.person` (must be importable from the repo root)

Install:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install python-dotenv
```

### Environment

Provide a `.env` file (or export an environment variable) with:

```env
LETTERENHUIS_FOLDER=/absolute/path/to/letterenhuis/directory/with/xml
```

The script reads all `*.xml` files in this folder.

### Usage

```bash
python parse_letterenhuis.py
```

Output: a CSV named `authorities_letterenhuis.csv` alongside the script (path is hard-coded in the final `write_csv` call).

### Input structure (expected elements)

```xml
<root>
  <JsonmodelType>agent_person</JsonmodelType>
  <Names>                               (repeated)
    <Qualifier>…</Qualifier>             # if absent → main name; if present → alias
    <PrimaryName>Last</PrimaryName>
    <RestOfName>First</RestOfName>
    <Suffix>Jr./Sr./…</Suffix>
  </Names>

  <DatesOfExistence>
    <StructuredDateRange>
      <BeginDateStandardized>YYYY-MM-DD</BeginDateStandardized>
      <EndDateStandardized>YYYY-MM-DD</EndDateStandardized>
    </StructuredDateRange>
    <!-- or -->
    <StructuredDateSingle>
      <DateRole>begin|end</DateRole>
      <DateStandardized>YYYY-MM-DD</DateStandardized>
    </StructuredDateSingle>
  </DatesOfExistence>

  <AgentPlaces>                          (repeated)
    <PlaceRole>place_of_birth|place_of_death</PlaceRole>
    <Subjects><Ref>Place label</Ref></Subjects>
  </AgentPlaces>

  <AgentOccupations>                     (repeated)
    <Notes><Content><String>Writer</String></Content></Notes>
  </AgentOccupations>

  <ExternalDocuments>                    (repeated)
    <Title>viaf|rkd|dbnl|odis|wikidata|…</Title>
    <Location>https://…</Location>
  </ExternalDocuments>

  <URI>https://…</URI>
</root>
```

### Notes & caveats

- **CSV header/order**: determined by `scripts.person.write_csv` and `Person.print_properties()`.
- **Aliases & occupations**: values are aggregated into comma-separated strings; trailing commas are removed.
- **Cleanup**: occupations replace literal `\r\n` with commas.
- **Identifier extraction**: `find_id()` returns the substring after the last `=` if present, else after the last `/`.

## parse_memorialis.py - UGent Memorialis → VNA CSV Converter

This script converts **UGent Memorialis** JSON records into the **Visual Name Authority (VNA)** CSV format using the shared `scripts.person` utilities.

For each JSON file in a folder, the script extracts:

- **Identifiers**
  - Local `id` → `Person.id`
  - Canonical URI → `https://www.ugentmemorialis.be/catalog/<id>` → `Person.identifier.uri`
  - Optional **VIAF** ID (if present in *link_display* entries)
  - Optional **Wikidata** QID (looked up from a separate *id → QID* CSV)
- **Names**
  - First/last name from `title_t[0]` (expects `"Last, First"`)
  - Additional names from `title_t[1:]` → concatenated into `Person.name.alias` (“First Last”)
- **Life events**
  - Birth and death (year and/or place) from `"birth_date_display"` / `"death_date_display"` strings, parsed into:
    - `Person.birth = Event(place, date)`
    - `Person.death = Event(place, date)`
- **Occupations**
  - From `mandate_facet` (list), concatenated into a comma-separated string
- **Picture**
  - First available JPG from (in order): `thumbnail_display`, `thumbnail_link_url_display`, `thumbnail_url_display`

Finally, a list of `Person` objects is written to a VNA-compatible CSV via `write_csv`.

### Requirements

- **Python** 3.9+ (recommended)
- **Python packages**
  - `python-dotenv` (for environment variables)
- **Local project module**
  - `scripts.person` (must be importable from the repo root)

Install:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install python-dotenv
```

### Environment

Provide a `.env` file (or export these vars):

```env
MEMORIALIS_FOLDER=/absolute/path/to/memorialis/json
MEMORIALIS_QIDS=/absolute/path/to/id_to_qid.csv
```

- `MEMORIALIS_FOLDER` — directory containing the JSON files
- `MEMORIALIS_QIDS` — CSV mapping file with headers `id,QID` (used to fill `Person.identifier.wikidata`)

### Input structure (expected JSON keys)

Within each JSON file, the script expects an object with at least:

```json
{
  "response": {
    "document": {
      "_id": "...",
      "title_t": ["Last, First", "Last, Given Other", "..."],
      "birth_date_display": ["Ghent, 1901", "..."],
      "death_date_display": ["1955, Antwerp", "..."],
      "mandate_facet": ["Professor", "Rector"],
      "thumbnail_display": ["https://.../image.jpg"],
      "thumbnail_link_url_display": ["https://.../image.jpg"],
      "thumbnail_url_display": ["https://.../image.jpg"],
      "link_display": [
        "[Virtual International Authority File] https://viaf.org/viaf/44300636/",
        "..."
      ]
    }
  }
}
```

> The script checks picture fields in the order `thumbnail_display`, then `thumbnail_link_url_display`, then `thumbnail_url_display`. The first **JPG** URL wins.

### Usage

```bash
python parse_memorialis.py /absolute/path/to/output.csv
```

- Positional argument: output CSV path (`OUTPUT_FILE`)
- The script reads JSON files from `MEMORIALIS_FOLDER` and the ID→QID mapping from `MEMORIALIS_QIDS`.

### Output

A CSV with the standard VNA header as defined by `scripts.person.write_csv` (see your `person.py`).

### Notes & caveats

- **Name parsing** assumes `title_t[0] == "Last, First"`. Additional entries populate `alias` as “First Last”.
- **Date/place parsing** in `parse_date_and_place()` is heuristic:
  - If the **last comma-separated token** is all digits → treated as the **date** (e.g., a year).
  - Remaining tokens are concatenated as **place** (commas preserved and trimmed).
  - Otherwise, the entire string becomes either date (if digits only) or place.
- **VIAF extraction**: looks for list entries in `link_display` whose prefix contains “Virtual International Authority File”, then extracts the numeric VIAF ID from the bracketed URL part.
- **Wikidata QID**: looked up via `MEMORIALIS_QIDS` mapping. Records without a mapping remain empty.

## parse_odis.py - ODIS JSON → VNA CSV Converter

`parse_odis.py` converts agent/person records exported from **ODIS** (Onderzoekssteunpunt en Databank Intermediaire Structuren) in JSON format into a **Visual Name Authority (VNA)**-compatible CSV, using the shared utilities from `scripts.person`.

For each ODIS agent object in the JSON, the script extracts:

- **Identifiers**
  -  top-level `URL` → `Person.identifier.uri`
  - **External authorities** from each `STEEKKAART.PS_BIJLAGEN[]`:
    - VIAF → (numeric part derived from the URL; see note below)
    - Wikidata → QID from URL
    - DBNL → ID from URL query param
    - ODIS -> extracted from `"RUBRIEK"` and `"ID"`
- **Names**
  - From each `STEEKKAART.PS_NAMEN[]`:
    - Items with `NAAMSOORT` containing `"voornaam"` → `Person.name.first` (concatenated)
    - Items with `NAAMSOORT` containing `"familienaam"` → the first becomes `Person.name.last`; the rest are appended to `Person.name.alias`
    - All other `NAAMSOORT` values → appended to `Person.name.alias`
- **Birth / Death**
  - `STEEKKAART.PS_GEBOORTEPLAATS`, `STEEKKAART.PS_GEBOORTEDATUM`
  - `STEEKKAART.PS_OVERLIJDENSPLAATS`, `STEEKKAART.PS_OVERLIJDENSDATUM`
- **Pictures**
  - From `STEEKKAART.PS_ILLUSTRATIES[]`: the code appends `"ID: <ID>"` (comma-separated) to `Person.picture`

Finally, the script writes a CSV using `scripts.person.write_csv(OUTPUT, persons)`, which emits the VNA header and column order defined by your project.

### Requirements

- **Python** 3.9+ (recommended)
- Local project module `scripts.person` resolvable from the repository root (the script prepends `Path(__file__).parents[2]` to `sys.path`)

Install project deps as you normally do for this repo.

### Input JSON (essential fields)

A simplified example of the structure the script expects:

```json
[
  {
    "URL": "https://odis.be/xyz/123",
    "RUBRIEK": "PS",
    "ID": "123",
    "OMSCHRIJVING": "Jeanke Peeters",
    "STEEKKAART": [
      {
        "PS_NAMEN": [
          {"NAAMSOORT": "voornaam", "NAAM": "Jan"},
          {"NAAMSOORT": "familienaam", "NAAM": "Peeters"},
          {"NAAMSOORT": "alias", "NAAM": "J. Peeters"}
        ],
        "PS_GEBOORTEPLAATS": "Antwerpen",
        "PS_GEBOORTEDATUM": "1901-01-01",
        "PS_OVERLIJDENSPLAATS": "Brussel",
        "PS_OVERLIJDENSDATUM": "1977-03-14",
        "PS_ILLUSTRATIES": [{"ID": "IMG-001"}],
        "PS_BIJLAGEN": [
          {"B_LINKTXT": "Wikidata", "B_URL": "https://www.wikidata.org/wiki/Q42"},
          {"B_LINKTXT": "Virtual International Authority File (VIAF)", "B_URL": "https://viaf.org/viaf/44300636/"},
          {"B_LINKTXT": "Digitale Bibliotheek voor de Nederlandse Letteren", "B_URL": "https://www.dbnl.org/auteurs/auteur.php?id=mult002"}
        ]
      }
    ]
  }
]
```

## Usage

```bash
python parse_odis.py /absolute/path/to/odis.json /absolute/path/to/output.csv
```

- `argv[1]` → input JSON file path (`FILE`)
- `argv[2]` → output CSV path (`OUTPUT`)

The script will iterate all top-level records and write the CSV using the VNA header/order from `scripts.person.write_csv`.

## Notes & caveats

- **Name logic** is simple and string-based:
  - “voornaam” → first names, concatenated with spaces
  - “familienaam” → the first is `last`; the remainder go to `alias`
  - any other `NAAMSOORT` → appended to `alias`
- **Pictures**: `PS_ILLUSTRATIES[].ID` values are concatenated into `person.picture` as `"ID: <ID>"`, comma-separated.
- **String cleanup** uses `beautify_string` to trim whitespace and trailing commas.

## parse_pictures_boekentoren.py - Boekentoren portrait parser → CSV

This script parses **Boekentoren** JSON records (one file per record in a folder), tries to **extract depicted person names** from the record **title** using **spaCy NER** (`nl_core_news_lg`), optionally falls back to a simple rule for titles like “Portret van …”, enriches each person with VIAF, birth/death years and “real name” detection heuristics, and writes a **row-per-depicted-person** CSV.

### What the script does

For each JSON file in `FOLDER`:

1. Read `response.document` and collect:
   - `id` → photo ID
   - `title` → used for name extraction (NER)
   - `has_download_license` → license flag
   - `thumbnail_url` → turned into a IIIF image URL (string only; not downloaded)
   - `display_author` → extra lines with biographical hints (pseudonyms, VIAF, dates)
2. Detect person names:
   - Run **spaCy** NER (model `nl_core_news_lg`) on `title`; collect `Person` entities.
   - If none are found and the title contains “Portret van …”, take the substring after that phrase (unless it contains “onbekend”).
   - If still none, mark the record for manual review (`download_image` global is set to `False`) and insert a sentinel (`"FOUT!!"`).
3. For each detected name, try to enrich from `display_author`:
   - Extract **VIAF**: digits following *(viaf) …*
   - Extract **birth/death years**: pattern `YYYY-YYYY`
   - Detect **pseudonym**: if the line contains *pseudoniem van …*, copy the label as alias and set the real name accordingly.
4. Decide **type**: `"PORTRET"` if one person, `"GROEP"` if multiple.
5. Build a **IIIF URL** from `thumbnail_url` by replacing the tail with `/full/full/0/default.jpg` (string only).
6. Write all photo/person pairs to `boekentoren.csv`.

Each output row contains:

```
photo_id, title, type, realname, alias, birthdate, deathdate, viaf, license, image_url, status
```

> Note: the script does **not** download images; it only computes a IIIF URL string (the variable name `download_image` controls whether the URL string is built when no person name was found).

### Requirements

- **Python** 3.9+ (recommended)
- **spaCy** with the Dutch model `nl_core_news_lg`

Install:

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install spacy
python -m spacy download nl_core_news_lg
```

### Input format

Directory of JSON files. Each file must contain at least:

```json
{
  "response": {
    "document": {
      "id": "…",
      "title": "…",
      "thumbnail_url": "https://…/iiif/…/…",
      "has_download_license": true,
      "display_author": [
        "Lastname, Firstname (YYYY-YYYY) (viaf) 44300636 (role)dpc …",
        "…"
      ]
    }
  }
}
```

Only the keys actually used by the script are required.

### Usage

```bash
python parse_pictures_boekentoren.py /absolute/path/to/json_folder
```

- The script writes a CSV named **`boekentoren.csv`** in the current working directory.

### Notes & caveats

- **Language model**: NER relies on `nl_core_news_lg`. If the model misses names, the “Portret van …” fallback kicks in; otherwise the record is flagged for review (`status`, `download_image=False`).
- **Heuristics**: *pseudoniem van …* is used to swap alias/real name when present. The parsing of `(role)dpc`, VIAF, and date ranges is string-based and may need adaptation if the source format changes.
- **Groups**: If more than one depicted person is inferred, the `type` is set to `"GROEP"` and one CSV row is emitted per person.
- **IIIF URL**: The function **does not fetch** the image; it only builds a canonical IIIF delivery URL from `thumbnail_url`.
