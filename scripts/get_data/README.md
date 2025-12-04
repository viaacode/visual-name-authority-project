# Scripts

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

## get_amsab_images.py — Download IIIF images for Amsab-ISG (batch from CSV)

This script reads a CSV (configured via environment variables), looks up **IIIF manifest URLs** in several columns, and downloads the **image file** referenced by each manifest. Files are written into a per-person subfolder, with filenames derived from paired identifier columns.

It uses shell tools (`curl`, `jq`, `wget`) to resolve the IIIF manifest and fetch the image.

### Requirements

* **Python** 3.9+
* **Packages**
    * `python-dotenv` (for loading `.env`)
* External CLI tools (must be available on PATH)
    * `curl`
    * `jq`
    * `wget`

Install Python deps:
```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install python-dotenv
```

### Environment variables

Create a `.env` file next to the script (or export these vars in your shell):

```env
# Input CSV with IIIF manifest URLs and identifiers
AMSAB_FOTOS=/absolute/path/to/input.csv

# Root output folder where per-person subdirectories are created
AMSAB_FOLDER=/absolute/path/to/output
```

The script also defines two mappings:

* `KEYS`: CSV columns that contain IIIF manifest URLs (e.g. `PID_IIIF_1`, …, `Zij-aanzicht_IIIF`)
* `IDENTIFIERS`: map from each `KEYS[i]` to the column holding the corresponding identifier used for the output filename (e.g. `PID_OPAC_1`, …)

### Expected CSV columns

Your input CSV must at least contain:
* `URL` — used to derive the per-person folder name
* For each key in `KEYS`:
    * the IIIF manifest URL column, e.g. `PID_IIIF_1`
    * its paired identifier column from IDENTIFIERS, e.g. `PID_OPAC_1`

Example of the minimal required columns of the CSV:
```csv
URL,PID_IIIF_1,PID_OPAC_1,PID_IIIF_2,PID_OPAC_2,Zij-aanzicht_IIIF,Zij aanzicht_OPAC
...
```

### What it does

For every CSV row:

1. Read the person identifier from `URL`; create an output directory `<AMSAB_FOLDER>/<URL>`.
2. For each IIIF manifest column in `KEYS` that is non-empty:
    * Build the output filename from the paired identifier column (`IDENTIFIERS[key]`), taking the last path segment.
    * Download the image URL found under `.items[].items[].items[].body.id` of the IIIF manifest and write it as `<filename>.jpg` into the person’s folder.
3. Sleep 2 seconds between downloads.

> Note: If the output file already exists, `wget -nc` will skip re-downloading.

### Usage

```bash
# ensure .env is set up and tools are on PATH
python get_amsab_images.py
```

Output tree (example):
```bash
/output-root/
  52772/
    12345.jpg
    67890.jpg
  52773/
    22222.jpg
```

### Caveats / known assumptions

* The script shells out to `curl | jq | wget`. These must exist on your system.
* The **IIIF Presentation API v3** path `.items[].items[].items[].body.id` is assumed.
* Minimal error handling: shell command failures won’t raise Python exceptions; they just run via `os.system`. (You can later improve this script to `subprocess.run(check=True)` or use a pure-Python approach with `requests` + `json`.)

## get_data_kbr.py — KBR OAI-PMH XML Downloader

This script downloads batches of XML records from the **KBR** OAI-PMH server and writes them to disk. It uses a known **resumption token pattern** to page through results and pretty-prints the XML for readability.

* Endpoint: `https://opac.kbr.be/oaiserver.ashx`
* OAI verb: `ListRecords`
* Output: one XML file per page, named like `kbr_oai_pmh_<offset>.xml`

> ⚠️ The script assumes a **specific resumptionToken format** (`!!AUTHOR!<offset>!492043!oai_dc`) and a fixed paging range. Adapt these to your actual use case or to KBR’s current token format if it changes.

### Requirements

* **Python** 3.9+ (recommended)
* **Libraries**:
    * `requests` (HTTP client; used with a session)
    * Python stdlib `xml.dom.minidom` (for pretty printing)

Install:
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install requests
```

### Configuration

Edit the constants at the top of the script:
```python
DOMAIN = "https://opac.kbr.be/oaiserver.ashx"
OAI_VERB = "ListRecords"
FOLDER = "path/to/my_folder"  # change this to an existing folder
```

The page loop and token pattern are currently:
```python
for page in range(0, 492100, 100):
    TOKEN = f"!!AUTHOR!{page}!492043!oai_dc"
```

* `page` acts as the offset (0, 100, 200, …).
* `492043` and `oai_dc` are fixed parts of the token as used in your current setting.
* Adjust these if KBR’s token scheme differs for your collection/metadataPrefix.

> Make sure `FOLDER` exists, or create it beforehand.

### Usage

```bash
python kbr_oai_pmh_download.py
```

The script will:
1. Iterate offsets (`0..492000` step `100`).
2. Build the URL:
`https://opac.kbr.be/oaiserver.ashx?verb=ListRecords&resumptionToken=!!AUTHOR!<offset>!492043!oai_dc`
3. GET the page (timeout 60 s).
4. Pretty-print the XML and save it as `FOLDER/kbr_oai_pmh_<offset>.xml`.

### Output

Files are saved to the configured `FOLDER`:
```bash
kbr_oai_pmh_0.xml
kbr_oai_pmh_100.xml
kbr_oai_pmh_200.xml
...
```

Each file contains the response for that token/page, pretty-printed with `xml.dom.minidom.toprettyxml()` (UTF-8).

### Notes & caveats

* **Token format:** The script **does not** follow OAI-PMH’s normal `resumptionToken` chaining; it constructs tokens directly from a pattern. If the provider changes the format, requests may fail.
* **Rate limiting / politeness:** There’s no throttling or retry logic. Consider adding delays or backoff if you encounter HTTP 429/503.
* **Pretty printing:** `minidom.toprettyxml()` is convenient but memory-heavier. For very large responses, a streaming approach (e.g., `lxml.etree.iterparse`) may be preferable.
* **Error handling:** Minimal. Non-2xx responses or malformed XML will raise exceptions. You can wrap the loop in `try/except` and log failures as needed.
* **Encoding:** The script uses `response.apparent_encoding` to decode text, then writes UTF-8.

## get_data_svm.py — Crawl SVM composers and export to VNA CSV

This script crawls detail pages under https://www.svm.be/componisten
 (one URL per line in a text file), extracts basic person data (name, birth/death date & place), optionally downloads related images, and appends each person as a row to a **VNA**-style CSV via the project’s `scripts.person` utilities.

### What it does

For each input URL:

1. **Fetch HTML** with `requests.Session`.
2. **Parse** with `BeautifulSoup`:
    * Name: from `<title>` (before `|`), then split into family/given names.
    * Life events: from `<div class="text-xl">` as a single text block, parsed into birth/death **place** and **date** (expected `DD/MM/YYYY`).
    * Images: from `<a class="js-modal-image" href="...">`. Files are saved under `PHOTO_FOLDER/<identifier>/` where `<identifier>` is the last URL segment.
3. **Populate** a `Person()` instance (from `scripts.person`), then append to an in-memory list.
4. Write all URLs in a CSV using `write_csv(OUTPUT, persons)`.

### Requirements

* **Python** 3.9+ (recommended)
* **Libraries**
    * `requests`
    * `beautifulsoup4`
* **Local project code**
    * `scripts.person` providing: `Person`, `Event`, `write_csv`, `beautify_string`

Install:
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install requests beautifulsoup4
```

> The script imports `scripts.person` via a relative path tweak:
> 
> ```bash
> path_root = Path(__file__).parents[2]
> path.append(str(path_root))
> from scripts.person import Person, Event, write_csv, beautify_string
> ```
> Ensure you run the script from within the repository so this import resolves.

### Inputs & outputs

* **Input text file** (`argv[1]`): UTF-8 file with one SVM detail URL per line
    
    Example:
    ```csv
    https://www.svm.be/componisten/achternaam-voornaam
    https://www.svm.be/componisten/andere-naam
    ```
* **Output CSV path** (`argv[2]`): destination file for the VNA CSV.
* **Image output**: images are stored under
`<ROOT_FOLDER>/<PHOTO_FOLDER>/<identifier>/filename.ext`, where:
    * `ROOT_FOLDER` = parent directory of the input text file
    * `PHOTO_FOLDER` = literal `'foto'` (constant in the script)
    * `identifier` = last URL segment of the person page

### Usage

```bash
python get_data_svm.py /absolute/path/to/urls.txt /absolute/path/to/output.csv
```

### Notes & assumptions

* **Date parsing** expects `DD/MM/YYYY`. If missing or malformed, the script writes a fallback error token (`FOUT!`) for the date.
* **Throttling**: the script sleeps **2 seconds** between requests to be polite to the server.
* **Images**: downloaded only when `<a class="js-modal-image" ...>` links are present. Missing images are logged.
* **Error handling**: minimal; network or parsing changes on the site may require adjustments.
* **Encodings**: the input text file must be UTF-8 and contain valid URLs.

## get_manifest_images.py — Download images via IIIF manifests

This script reads a CSV file, extracts IIIF Presentation API v3 manifest URLs from a specific column, resolves each manifest to its image URL (`.items[].items[].items[].body.id`), and downloads the image to an output folder. It also writes a small results CSV listing each manifest alongside the downloaded filename (or `FAILED!`).

### What it does

For every row in the input CSV:
1. Read the **IIIF manifest URL** from the `MANIFEST_COLUMN` (default: `manifest`).
2. (Optional) Read a person name from `PERSON_COLUMN` (default: `volledige naam`) — printed for context only.
3. Derive the output filename from the manifest URL: the **second to last** path segment + `.jpg`.
4. Download the image referenced by the manifest into the given output folder.
5. Append `[manifest, filename]` (or `[manifest, FAILED!]`) to a results list.
6. Write all results to `<OUTPUT_FOLDER>/<OUTPUT_FILE>` (default `output.csv`).

> The script uses shell tools `curl | jq | wget` to resolve and fetch images; ensure they’re installed and available in `PATH`.

### Requirements

* **Python** 3.9+ (recommended)
* **External tools (CLI)**
    * `curl` (HTTP)
    * `jq` (JSON parsing)
    * `wget` (downloading)

_(No third-party Python packages are required.)_

### Inputs & configuration

* **Positional CLI arguments**
    * `argv[1]` → `CSV`: path to input CSV
    * `argv[2]` → `OUTPUT_FOLDER`: destination folder for images and results CSV
* **In-script constants (edit as needed)**
    ```python
    OUTPUT_FILE = "output.csv"         # results CSV filename (inside OUTPUT_FOLDER)
    MANIFEST_COLUMN = "manifest"       # column holding IIIF manifest URLs
    PERSON_COLUMN = "volledige naam"   # column with person/name (used for prints only)
    ```

#### Input CSV format

Your CSV should contain at least the two columns referenced above:
```csv
manifest,volledige naam
https://example.org/iiif/3/<id>/manifest.json,Firstname Lastname
https://other.org/iiif/3/<id>/manifest,Another Person
```

### Usage

```bash
python get_manifest_images.py /absolute/path/to/input.csv /absolute/path/to/output_folder
```

* Images are downloaded into `OUTPUT_FOLDER`.
* A results CSV is written to `OUTPUT_FOLDER/output.csv` (or whatever you set in `OUTPUT_FILE`).

### Output

* **Images**: saved directly in `OUTPUT_FOLDER` (filenames like `<manifest-id>.jpg`, derived from the second-to-last path segment of the manifest URL).
* **Results CSV**: `OUTPUT_FOLDER/output.csv`, containing rows of:
  ```csv
  manifest, filename-or-FAILED!
  ```

### How it works (brief)

* For each manifest URL, the script runs: `curl <manifest> | jq -r '.items[].items[].items[].body.id'` to obtain the image URL, then downloads it with: `wget -O <OUTPUT_FOLDER>/<filename> <image-url>`
* A 2-second sleep is applied after each download.

### Notes & limitations

* **Shell tools required**: `curl`, `jq`, and `wget` must be installed and on `PATH`.
* **IIIF assumption**: The JSON path `.items[].items[].items[].body.id` follows IIIF Presentation API v3 and must match your manifests.
* **Error handling**: The script uses `os.system`, which does not raise exceptions on command failure; it returns a status code. The script logs failures as `FAILED!` in the results CSV.
* **Filenames**: If multiple manifests map to the same derived name, later downloads can overwrite earlier files — adjust naming if needed.

### Possible improvements (optional)

* Use `subprocess.run(..., check=True)` to catch command failures explicitly.
* Pure-Python approach (`requests` + `json`) instead of shell tools.
* Collision handling (add suffixes if filename exists, for example).
* Throttling/back-off if the server rate-limits requests.

## get_pictures_by_url.py — Download images from URLs listed in a CSV

This script reads a CSV file, looks up a direct image URL in column `foto`, derives a file name from the last path segment of `uri`, and downloads the image into a target folder using `wget`. Existing files are skipped. The downloader checks `wget`’s exit code and reports failures.

### What it does

For each row in the input CSV:
1. Read `uri` and `foto`.
2. Derive `image_id` as the last path segment of `uri`.
3. Build the destination path `<FOLDER>/<image_id>.jpg`.
4. If `foto` is present and the file does not exist, run `wget -O <dest> <foto>` via `subprocess.run(..., check=True)`.
5. Sleep 2 seconds between successful downloads (politeness).
6. If no `foto` value is present, print “no picture”.

### Requirements

* **Python** 3.8+ (recommended)
* **External tool**: `wget` (must be installed and available on `PATH`)
* CSV must be **UTF-8** (or your chosen `ENCODING`) encoded

_(No third-party Python packages are required.)_

### Configuration (in-script constants)

```python
PHOTO_COLUMN = 'foto'   # column holding the direct image URL
URI_COLUMN   = 'uri'    # column whose last path segment becomes the filename
ENCODING     = 'utf-8'  # CSV text encoding for input file
```

If your CSV uses different headers or encoding, adjust these constants accordingly.

### Input CSV format

Your CSV must include at least:
* `uri` — used to derive the output filename base (the last path segment).
* `foto` — the direct image URL to download.

Example:
```csv
uri,foto
https://example.org/items/12345,https://images.example.org/abc/12345/full/600,/0/default.jpg
https://example.org/items/99999,https://images.example.org/xyz/99999/full/600,/0/default.jpg
```

### Usage

```bash
python get_pictures_by_url.py /absolute/path/to/input.csv /absolute/path/to/output_folder
```

* The first argument is the source CSV path (`SOURCEFILE`).
* The second is the destination folder (`FOLDER`).

Outputs will look like:
```bash
/absolute/path/to/output_folder/12345.jpg
/absolute/path/to/output_folder/99999.jpg
```

### Notes & caveats

* **Error handling**: the script checks `wget`’s return code. On failure it logs an error and (best-effort) removes a zero-byte partial file if present.
* **Rate limiting**: sleeps 2 seconds after each successful download. Adjust if needed.
* **Filename collisions**: if two rows share the same last `uri` segment, they will target the same output filename.
* **Permissions/paths**: ensure `FOLDER` is writable and has sufficient space.
* **Headers are case-sensitive**: `uri`, `foto`.

## get_wiki_pics.py — Download files from Wikimedia Commons by CSV (category or single file)

This script reads a CSV and, for each row:
* If a Commons category is provided, it downloads all files in that category.
* If a single file name is provided, it downloads that one file.

Items are saved in named after the Wikidata ID.

It uses **Pywikibot** to iterate pages in a category (and to download them), and the external `wikiget` command to fetch an individual file by title.

### Requirements

* **Python** 3.9+ (recommended)
* **Python packages**
    * `pywikibot`
* **External CLI**
    * `wikiget` (must be installed and on your `PATH`)
* **CSV encoding**
    * UTF-8

Install Python deps:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install pywikibot
```

> Tip: For read-only downloads from Commons, Pywikibot usually works without logging in. If you maintain a Pywikibot setup, ensure its config (if any) is discoverable (e.g., `user-config.py`).

### Input CSV

The script expects these column headers (case-sensitive):
* `Wikidata ID` – used to name the output subfolder for the row
* `volledige naam` – printed for progress/logging (not used in filenames)
* `Commonscategorie` – Commons category name without the `Category:` prefix (e.g., `Beethoven`)
* `afbeelding` – Commons file title without `File:` (e.g., `Ludwig_van_Beethoven.jpg`)

Example:

```csv
Wikidata ID,volledige naam,Commonscategorie,afbeelding
Q255,Arnold Schoenberg,Schoenberg,Arnold_Schoenberg_1927.jpg
Q7314,Ludwig van Beethoven,Beethoven,
Q5598,Wolfgang Amadeus Mozart,,Wolfgang-amadeus-mozart_1756.jpg
```

### Output

For each row, a directory is created:

```bash
<OUTPUT_FOLDER>/<Wikidata ID>/
```

* If `Commonscategorie` is present: all files in that category are downloaded to this directory.
* If `afbeelding` is present: that single file is downloaded to this directory.

After processing all rows, the script removes two Pywikibot side effects in the working directory:
* the `apicache/` folder
* the `throttle.ctrl` file

### Usage

```bash
python get_pictures_by_url.py /path/to/input.csv /path/to/output_root
```

* First argument = CSV path (`SOURCE_FILE`)
* Second argument = output root directory (`OUTPUT_FOLDER`)

### How it works (brief)

* **Categories**: Creates a Commons `Site` via Pywikibot, builds a `Category` from `Category:<Commonscategorie>`, then uses `pagegenerators.CategorizedPageGenerator` to iterate members. For each page whose title starts with `File:`, it calls `page.download(<path>)`.
* **Single file**: Builds a Commons title File:<afbeelding> and runs:
    ```bash
    wikiget "File:<afbeelding>" -o "<output_path>"
    ```

via `os.system`.

### Notes & caveats

* `wikiget` must be installed and callable from your shell. (It’s a separate tool for downloading wiki files by title.)
* Category downloads rely on what the category contains at runtime (no recursion into subcategories).
* Errors in `download_category` are caught and printed, then the loop continues.
* Filenames are the page titles (minus the `File:` prefix) as provided by Commons.
* Pywikibot may create cache/lock files; the script removes `apicache` and `throttle.ctrl` at the end.

### Possible improvements (optional)

* Sanitize filenames for your filesystem (Commons titles can contain unusual characters).
* Add retry/backoff and explicit error codes for `wikiget`.
* Support recursive category traversal.
* Make column names configurable via flags.