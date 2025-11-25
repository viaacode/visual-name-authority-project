# Scripts

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

## clean_photos.py - Portrait / Group / Empty Classifier

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
