
# Scripts

## Overview

### Scripts for cleaning pictures

* [clean_photos_by_faces.py — Face-based Portrait / Group / Empty Classifier (OpenCV Haar)](#clean_photos_by_facespy--face-based-portrait--group--empty-classifier-opencv-haar)
* [clean_photos_old.py - Portrait / Group / Empty Classifier (Outdated)](#clean_photos_oldpy---portrait--group--empty-classifier)

### Scripts for scraping or crawling data and images

* [get_amsab_images.py — Download IIIF images of Amsab-ISG (batch from CSV)](get_data/README.md#get_amsab_imagespy--download-iiif-images-for-amsab-isg-batch-from-csv)
* [get_data_kbr.py — KBR OAI-PMH XML Downloader](get_data/README.md#get_data_kbrpy--kbr-oai-pmh-xml-downloader)
* [get_data_svm.py — Crawl SVM composers and export to VNA CSV](get_data/README.md#get_data_svmpy--crawl-svm-composers-and-export-to-vna-csv)
* [get_manifest_images.py — Download images via IIIF manifests](get_data/README.md#get_manifest_imagespy--download-images-via-iiif-manifests)
* [get_pictures_by_url.py — Download images from URLs listed in a CSV](get_data/README.md#get_pictures_by_urlpy--download-images-from-urls-listed-in-a-csv)
* [get_wiki_pics.py — Download files from Wikimedia Commons by CSV (category or single file)](get_data/README.md#get_wiki_picspy--download-files-from-wikimedia-commons-by-csv-category-or-single-file)

### Scripts for parsing or extracting data

* [extract_rights_wikitext.py — Extract author and license from Wikimedia Commons Wikitext](parse_data/README.md#extract_rights_wikitextpy--extract-author-and-license-from-wikimedia-commons-wikitext)
* [parse_avg.py - AVG XML → VNA CSV Converter](parse_data/README.md#parse_avgpy---avg-xml--vna-csv-converter)
* [parse_letterenhuis.py - Letterenhuis XML → VNA CSV Converter](parse_data/README.md#parse_letterenhuispy---letterenhuis-xml--vna-csv-converter)
* [parse_memorialis.py - UGent Memorialis → VNA CSV Converter](parse_data/README.md#parse_memorialispy---ugent-memorialis--vna-csv-converter)
* [parse_odis.py - ODIS JSON → VNA CSV Converter](parse_data/README.md#parse_odispy---odis-json--vna-csv-converter)
* [parse_pictures_boekentoren.py - Boekentoren portrait parser → CSV](parse_data/README.md#parse_pictures_boekentorenpy---boekentoren-portrait-parser--csv)

## clean_photos_by_faces.py — Face-based Portrait / Group / Empty Classifier (OpenCV Haar)

This scripts reads a **text file with one image path per line**, detects faces on CPU using **OpenCV’s Haar cascades**, and moves the images into category folders:

* `portrets/` → exactly **1** face that is at least 100x100 pixels
* `group/` → **2 or more** faces
* `empty/` → **0** faces (that are at least 100x100 pixels)

It also writes a summary CSV named `cleanup_portrets.csv`.

> Haar cascades are lightweight and fast on CPU, but less accurate than modern DNNs. For higher accuracy, consider switching to OpenCV DNN (ResNet-SSD).

### Requirements

* **Python** 3.9+ (recommended)
* **Packages:**
  * `opencv-python`

### Install:

All dependencies should already be installed if you followed the main README of this repository.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install opencv-python
```

### Input format

Provide a **UTF-8** text file with **exactly one path per line**.

* Blank lines and lines starting with `#` or `;` are ignored.
* If the **first line** is a simple header like `filename` or `path`, it’s ignored.
* Surrounding single/double quotes are stripped (e.g., from CSV/Excel exports).
* BOM (`utf-8-sig`) is supported.

#### Example `photos.txt`

```bash
./data/photos/img001.jpg
./data/photos/img002.jpg
./data/photos/subdir/img003.png
```

To create a text file with exactly one path per line, you can use this command (macoOS):
* pictures not stored in subidirectores: `realpath path/to/folder/with/photos/*`
* pictures stored in subdirectories: `realpath path/to/folder/with/photos/*/*`

### Output

* Summary CSV with columns `filename`, `location` and `num_faces`
* Images are moved in directories `empty`, `group` and `portret`

#### Structure classified images

* **Without** `--subdirectories`
  Files go directly under the category folder:

```bash
/output-root/
  portrets/
    img001.jpg
  empty/
    img002.jpg
  group/
    img003.png
  cleanup_portrets.csv
```

* **With** `--subdirectories`
  The image’s **parent folder name** is recreated inside the category:

```bash
/output-root/
  portrets/
    subdir/
      img001.jpg
  empty/
    photos/
      img002.jpg
  group/
    subdir/
      img003.png
  cleanup_portrets.csv
```

### Usage

```bash
python clean_photos_by_faces.py /path/to/photos.txt
```

### Arguments

* `source_file` (positional): Text file with one image path per line.
* `--subdirectories`: Preserve the image’s **immediate parent folder** under each category (i.e., `portrets/<parent>/…`).
* `--output-root PATH`: Explicit output root. If not set:
  * with `--subdirectories`: the parent directory of the **first** image is used;
  * without `--subdirectories`: the directory of the **first** image is used.


### Workflow

1. Reads image paths from `source_file`.
2. Determines the **output root** and ensures the classification directories exist: `portrets/`, `empty/`, `group/`.
3. Loads the Haar cascade: `haarcascade_frontalface_default.xml`.
4. For each image:
   * Loads with OpenCV (`cv2.imread`); unreadable/corrupt images are **deleted**.
   * Detects faces (grayscale + `detectMultiScale`).
   * Moves the file into `portrets`, `group`, or `empty`.
   * Logs a row for the summary CSV.
5. Writes `cleanup_portrets.csv` in the output root.

### Detection settings (in code)

At the top of the script:

```python
SCALE_FACTOR = 1.1     # image pyramid scale step
MIN_NEIGHBORS = 5      # higher => fewer, more confident detections
MIN_SIZE = 100         # minimum face width/height in pixels
CASCADE_NAME = "haarcascade_frontalface_default.xml"
```

Tuning tips:

* Increase `MIN_SIZE` to **ignore small faces**; `100` enforces ≥ 100×100 px faces.
* Increase `MIN_NEIGHBORS` to reduce false positives (potentially missing some true faces).
* Lower `SCALE_FACTOR` (e.g., 1.05) to find more faces at the cost of speed.

### Troubleshooting
* “Cannot load cascade” → Ensure OpenCV is installed and `cv2.data.haarcascades` contains `haarcascade_frontalface_default.xml`.
* “Unreadable image” → The file may be corrupt or not an image format OpenCV can read.
* Nothing moves → Check that the input paths are correct and accessible (absolute/relative).

### Notes & possible improvements
* Haar cascades are fast but **less accurate** than modern detectors. For better accuracy (still CPU-friendly), switch to **OpenCV DNN (ResNet-SSD)** and add a confidence threshold; faces ≥ 100×100 px can be enforced the same way.

## clean_photos_old.py - Portrait / Group / Empty Classifier

### Overview

An improved version of this script is `clean_photos_by_faces.py`. 

`clean_photos.py` reads a **plain text file with one image path per line**, uses **Detectron2 (COCO-Keypoints)** to count how many people are in each image, and moves the files into category folders:

* `portrets/` → exactly **1** person
* `group/` → **2** or more persons
* `empty/` → **0** persons

It also writes a summary CSV: `cleanup_portrets.csv`.

### Requirements

* **Python** 3.9+ (recommended)
* **Packages:**
    * `opencv-python`
    * `torch`, `torchvision` (version compatible with Detectron2)
    * `detectron2`

> ⚠️ Detectron2 installation varies by OS and PyTorch build. Follow the official Detectron2 install guide for your environment.

### Installation

Packages are already installed if you followed the main README of this repository.

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

pip install torch torchvision
pip install opencv-python
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```

### Input format (important)

Provide a **UTF-8** text file with **exactly one path per line**:
* Blank lines and lines starting with `#` or `;` are ignored.
* A simple header like `filename` or `path` on the **first line** is ignored.
* Surrounding single/double quotes are stripped.

#### Example (`photos.txt`)
```bash
/data/photos/img001.jpg
/data/photos/img002.jpg
/data/photos/subdir/img003.png
```

### Output

* Images are **moved** (not copied) into `portrets/`, `empty/`, or `group/`.
* A summary CSV `cleanup_portrets.csv` at the output root with columns filename, location and num_faces

### Usage

```bash
python clean_photos.py --subdirectories /path/to/photos.txt 
```

#### Positional arguments

* `source_file` — path to your text file

#### Options
* `--subdirectories`: when images are ordered in subdirectories
* `--threshold FLOAT` — detection score threshold (default 0.7)
* `--output-root PATH` — explicit output directory (default: derived from first image)

### Workflow

1. Read paths line-by-line from the input file.
2. Load Detectron2 COCO-Keypoints model.
3. For each image:
    * Read via OpenCV
    * Count persons (COCO class id `0`)
    * Move file to `portrets/`, `group/`, or `empty/`
    * Append a row to the summary
4. Write `cleanup_portrets.csv` in the output directory.

### Error handling

* **Unreadable/corrupt images** → removed.
* **Missing files** → skipped with a warning.

Absolutely — here’s a copy-pasteable **README.md** for `parse_odis.py`, plus clear, Google-style **docstrings** you can drop straight into the script. I’m not changing behavior; this only documents what’s there.

# Classes

## person.py — Data model and CSV export for Visual Name Authority

This module defines lightweight data classes to represent a person and related metadata in the Visual Name Authority (VNA) project, plus small helpers to extract IDs from well-known identifier URLs and to export a list of people to a VNA-compatible CSV.

### What’s inside

* **Data classes**
  * `Name` — first/last/full name and an optional alias string
  * `Alias` — (optional) first/last components of an alternate name
  * `Event` — a place/date pair (used for birth and death)
  * `Identifier` — common external IDs (URI, Wikidata, ODIS, RKD, DBNL, VIAF, ISNI)
  * `Person` — aggregates the objects above and exposes print_properties() in the VNA column order
* **Helpers**
  * `get_wikidata_id(url)` → `"Q…"`, last path segment
  * `get_dbnl_id(url)` → value after the last `"="`
  * `get_viaf_id(url)` → last path segment if numeric, otherwise `""`
  * `beautify_string(value)` → trims whitespace, drops trailing comma
* **Export**
  * `write_csv(filename, persons)` — writes a CSV with the standard VNA header

### CSV schema produced by write_csv

Header (exact order):
```
URI,ID,volledige naam,voornaam,achternaam,alias,geboorteplaats,geboortedatum,
sterfplaats,sterfdatum,beroep,DBNL ID,ODIS ID,Wikidata ID,VIAF ID,RKD ID,ISNI ID,foto
```

Each row is produced by `Person.print_properties()`.

### Minimal example

```python
from person import Person, Name, Event, Identifier, write_csv

p = Person()
p.id = "123"
p.name = Name(first="Marie", last="Curie", full="Marie Curie", alias="")
p.birth = Event(place="Warsaw", date="1867-11-07")
p.death = Event(place="Passy", date="1934-07-04")
p.occupation = "Physicist; Chemist"
p.identifier = Identifier(
    uri="https://example.org/person/123",
    wikidata="Q7186",
    viaf="44300636",
    isni="0000000121032683",
)

write_csv("people.csv", [p])
```

### Notes

* `Person.print_properties()` defines the exact column order used by write_csv.
* `get_viaf_id()` returns an empty string if the last path segment is not numeric.
* The `Alias` class is available for projects that store richer alias data, but the current CSV export uses the simple `Name.alias` string.
