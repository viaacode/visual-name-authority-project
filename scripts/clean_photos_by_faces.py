#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Cleaner — Face-based Portrait / Group / Empty Classifier (OpenCV Haar)

Reads a text file with one image path per line, detects faces on CPU using
OpenCV's Haar cascades, and moves images into:

- portrets/  -> exactly 1 face
- group/     -> 2 or more faces
- empty/     -> 0 faces

Writes a summary CSV: cleanup_portrets.csv

Example:
    python script.py photos.txt

Notes:
    - Haar cascades are lightweight & CPU-friendly, but less accurate than modern DNNs.
"""

#---------- Imports ----------
from argparse import ArgumentParser, Namespace
import csv
import logging
from pathlib import Path
import shutil
from typing import Iterable, List

import cv2

# Workflow:
# 1) Read list of image paths from SOURCE_FILE.
# 2) Detect number of faces per photo.
# 3) Move file to:
#    - ./portrets/ if exactly 1 face,
#    - ./empty/    if 0 facas,
#    - ./group/    if more than 1 face.
# 4) Write summary CSV (cleanup_portrets.csv).

# ---------- Constants ----------
SCALE_FACTOR: float = 1.1 # image pyramid scale factor
MIN_NEIGHBORS: int = 5 # min neigbors
MIN_SIZE: int = 100 # minimum face size in px
CASCADE_NAME = "haarcascade_frontalface_default.xml" # Cascade file in cv2.data.haarcascades


# ---------- I/O helpers ----------

def create_dirs(base: Path):
    """Create (or ensure) the three destination category directories.

    Args:
        base: Output root directory under which `portrets`, `empty`, and `group` live.

    Returns:
        A tuple `(portrets_path, empty_path, group_path)`.
    """
    portrets = base / "portrets"
    empty = base / "empty"
    group = base / "group"
    for directory in (portrets, empty, group):
        directory.mkdir(parents=True, exist_ok=True)
        logging.info("%s created", directory)


def get_paths_list(
    source_file: Path,
    comments: Iterable[str] = ("#", ";"),
    strip_wrapping_quotes: bool = True,
    skip_header_keywords: Iterable[str] = ("path", "file", "filename", "image", "filepath"),
    check_exists: bool = False,
) -> List[Path]:
    """
    Read a text file with exactly one entry (path) per line.

    - Skips blank lines and comment lines.
    - Optionally strips surrounding single/double quotes.
    - Optionally skips a header line if it matches common header keywords.
    - Optionally checks existence of files.

    Returns:
        List[Path]: Paths in file order.

    Raises:
        ValueError: if source_file is empty
    """
    if not source_file.exists():
        raise FileNotFoundError(source_file)

    paths: List[Path] = []
    with source_file.open("r", encoding="utf-8-sig") as file:  # utf-8-sig strips BOM if present
        for index, line in enumerate(file):
            string = line.strip()
            if not string:
                continue
            if any(string.startswith(comment) for comment in comments):
                continue
            # Skip a simple header row like "filename" or "path"
            if index == 0 and string.lower() in skip_header_keywords:
                continue
            if strip_wrapping_quotes and len(string) >= 2 and string[0] == string[-1] and string[0] in {"'", '"'}:
                string = string[1:-1].strip()
                if not string:
                    continue
            filepath = Path(string).expanduser()
            if check_exists and not filepath.exists():
                logging.warning("%f does not exist", filepath)
                continue
            paths.append(filepath)

    if not paths:
        raise ValueError("No paths found in the file.")
    
    return paths


def find_directory(img_path: Path, category: str, output_dir: Path, subdirectories) -> Path:
    """Compute destination directory for a classified image.

    Args:
        image_path: Source image path.
        category: One of {'portrets', 'empty', 'group'}.
        ouput_dur: Output directory.

    Returns:
        The directory where the image should be placed.
    """

    if subdirectories:
        destination = output_dir / category / img_path.parent.name
        logging.info("Destination is %s", destination)
        return destination

    destination = output_dir / category
    logging.info("Destination is %s", destination)
    return output_dir / category


def move_file(source_image: Path, destination: Path) -> Path:
    """Move a file into a destination directory without overwriting existing files.

    Args:
        source_image: Source file path.
        destionation: Destination directory path (created if missing).

    Returns:
        The final destination file path.

    Raises:
        FileNotFoundError: If `path` does not exist

    Side Effects:
        - Creates `destionation` if not present.
        - Moves `path` to `destination`
    """

    destination.mkdir(parents=True, exist_ok=True)
    destination_file = destination / source_image.name

    if not source_image.exists():
        raise FileNotFoundError(f"Source not found: {source_image}")

    if destination_file.exists():
        logging.warning("%s already exists", destination_file)
        return destination_file
    
    shutil.move(str(source_image), str(destination_file))
    return destination_file


# ---------- Face detector ----------

def setup_face_detector() -> cv2.CascadeClassifier:
    """Construct and return an OpenCV Haar-cascade face detector.

    Loads the cascade file identified by the global ``CASCADE_NAME`` from
    OpenCV’s bundled ``cv2.data.haarcascades`` directory, validates that the
    classifier initialized correctly, and returns a ready-to-use
    :class:`cv2.CascadeClassifier`.

    The returned detector expects grayscale input when calling
    `detectMultiScale`. Convert BGR images with
    `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)` first. Typical parameters include
    `scaleFactor=1.1`, `minNeighbors=5`, and `minSize=(100, 100)` if you
    want to ignore faces smaller than 100×100 px.

    Returns:
        cv2.CascadeClassifier: Initialized Haar face detector.

    Raises:
        RuntimeError: If the cascade file cannot be found or loaded (i.e., the
            classifier is empty).
    """

    cascade_path = Path(cv2.data.haarcascades) / CASCADE_NAME
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise RuntimeError(f"Failed to load cascade: {cascade_path}")
    logging.info("Loaded Haar cascade: %s", cascade_path)
    return detector


def count_faces(detector: cv2.CascadeClassifier, img_bgr) -> int:
    """Count faces in a BGR image using a Haar-cascade detector.

    Converts the input image to grayscale and runs ``detectMultiScale`` with
    module-level parameters ``SCALE_FACTOR``, ``MIN_NEIGHBORS``, and ``MIN_SIZE``.
    Returns the number of detections that meet those thresholds.

    Args:
        detector (cv2.CascadeClassifier): Initialized Haar face detector (e.g. from
            :func:`setup_face_detector`).
        img_bgr: BGR image array as returned by ``cv2.imread`` with shape (H, W, 3).

    Returns:
        int: Number of detected faces (>= 0). If no faces are found, returns 0.

    Notes:
        - The image is converted to grayscale internally (``cv2.cvtColor``).
        - ``SCALE_FACTOR`` (>1.0) controls the image pyramid scale step (smaller values
          find more faces but are slower).
        - ``MIN_NEIGHBORS`` trades recall for precision (higher → fewer, more confident
          detections).
        - ``MIN_SIZE`` is the minimum face size in pixels, applied to both width and height
          (e.g., ``(100, 100)`` to ignore smaller faces).
        - Depending on OpenCV version, ``detectMultiScale`` may return an empty sequence or
          an array; this function treats both as zero detections.

    Raises:
        cv2.error: If the input image is invalid (e.g., wrong type/shape).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=SCALE_FACTOR,
        minNeighbors=MIN_NEIGHBORS,
        flags=cv2.CASCADE_SCALE_IMAGE,
        minSize=(MIN_SIZE, MIN_SIZE),
    )
    return 0 if faces is None else int(len(faces))


# ---------- Pipeline ----------

def setup_logging() -> None:
    """Configure logging for CLI usage.

    Args:
        verbose: When True, sets log level to DEBUG; otherwise INFO.

    Side Effects:
        - Configures the global logging handler/format for the process.
    """
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def write_summary_csv(directory: str, data):
    """Write a summary to ``<directory>/cleanup_portrets.csv``.

    Args:
        directory (str): Path to an existing output directory. This function
            does not create the directory.
        data (Iterable[Iterable[Any]]): Rows to write. Typically the first row
            is a header, e.g. ``["filename", "location", "num_faces"]``.

    Returns:
        None

    Notes:
        - The file is **overwritten** if it already exists.
    """
    logging.info("Writing summary CSV")
    with open(f"{directory}/cleanup_portrets.csv", "w", encoding="utf-8") as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerows(data)
    output_csv.close()


def proces_images(arguments: Namespace) -> Path:
    """Run the full classification/move pipeline and write a summary CSV.

    Steps:
        1. Read image list.
        2. Resolve output directory and ensure category directories.
        3. Initialize predictor.
        4. For each image:
            - Read, and remove unreadable files.
            - Count faces.
            - Move file to category directory.
            - Append to summary rows.
        5. Write `cleanup_portrets.csv`.

    Args:
        arguments: Runtime configuration for this run.

    Returns:
        The output root directory where the summary CSV is placed.

    Side Effects:
        - May create directories and move or delete files (unless dry-run).
        - Writes a CSV file: `cleanup_portrets.csv`.

    Raises:
        FileNotFoundError: If the input CSV does not exist.
        ValueError: If the input CSV yields no image paths.
        OSError: If there is a system related error.
    """

    summary_rows = [["filename", "location", "aantal gezichten"]]
    list_photos = get_paths_list(arguments.source_file)
    logging.info("Found %d image(s) to process.", len(list_photos))
    
    #determine output root
    subdirectories = False
    if arguments.subdirectories:
        subdirectories = True

    if arguments.output_root:
        location = arguments.output_root
    else:
        directory = list_photos[0].parent
        location = directory.parent if subdirectories else directory
    logging.info("Output root: %s", location)
    create_dirs(location)
    
    detector = setup_face_detector()
    for img_path in list_photos:
        try:
            if not img_path.exists():
                logging.warning("File not found, skipping: %s", img_path)
                continue

            img = cv2.imread(str(img_path))

            if img is None:
                logging.warning("Unreadable/corrupt image, removing: %s", img_path)
                try:
                    img_path.unlink(missing_ok=True)
                except OSError as e:
                    logging.error("Failed to remove %s: %s", img_path, e)
                continue

            num_faces = count_faces(detector, img)

            if num_faces == 1:
                category = "portrets"
            elif num_faces == 0:
                category = "empty"
            else:
                category = "group"

            destination_directory = find_directory(img_path, category, location, subdirectories)
            destination_path = move_file(img_path, destination_directory)
            summary_rows.append([img_path, str(destination_path), str(num_faces)])

            logging.info("%s -> %s (%s faces)", img_path, destination_directory, str(num_faces))

        except OSError as e:
            logging.exception("Error processing %s: %s", img_path, e)

    write_summary_csv(location, summary_rows)
    return location


def setup_parser() -> Namespace:
    """Parse CLI arguments.

    Returns:
        A Namespace object containing all arguments
    """
    parser = ArgumentParser(
        description="Classify photos into portrets/group/empty using Detectron2 and move them accordingly."
    )
    parser.add_argument("source_file", type=Path,
                   help="Path to a text file with image paths (1 column).")
    parser.add_argument("--subdirectories", action="store_true",
                   help="images are in subdirectories that should be preserverd.")
    parser.add_argument("--threshold", type=float, default=0.7,
                   help="Detection score threshold (default: 0.7).")
    parser.add_argument("--output-root", type=Path, default=None,
                   help="Explicit output root directory.")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    argument_list = setup_parser()
    setup_logging()
    output = proces_images(argument_list)
    logging.info("Done. Output directory: %s", output)
