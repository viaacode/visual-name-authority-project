# Scripts for parsindg data

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
LETTERENHUIS_FOLDER=/absolute/path/to/letterenhuis/xml
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
