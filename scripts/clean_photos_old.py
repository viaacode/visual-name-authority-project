#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Photo Cleaner — Portrait / Group / Empty Classifier

Reads a text file with image paths, runs Detectron2 (COCO-Keypoints) to count
people per image, and moves files into category folders:

- portrets/  -> exactly 1 person
- group/     -> more than 1 person
- empty/     -> 0 persons

Also writes a summary CSV: cleanup_portrets.csv

CLI
----
Example:
    python script.py photos.txt --subdirectories

Notes:
    - Detectron2 installation depends on your system & PyTorch version.
    - Unreadable/corrupt images are removed (see side effects on functions).
"""

from argparse import ArgumentParser, Namespace
import csv
import logging
from pathlib import Path
import shutil
from typing import Iterable, List

# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
import cv2

# Workflow:
# 1) Read list of image paths from SOURCE_FILE.
# 2) Detect number of persons per photo using Detectron2 (COCO-Keypoints).
# 3) Move file to:
#    - ./portrets/ if exactly 1 person,
#    - ./empty/    if 0 persons,
#    - ./group/    if more than 1 person.
# 4) Write summary CSV (cleanup_portrets.csv).

# ---------- variables ----------
cfg = get_cfg()


# ---------- I/O helpers ----------

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

def create_dirs(base: Path) -> None:
    """
    Create (or ensure) the three destination category directories.

    Args:
        base: Output root directory under which `portrets`, `empty`, and `group` live.

    Returns:
        None
    """
    portrets = base / "portrets"
    empty = base / "empty"
    group = base / "group"
    for directory in (portrets, empty, group):
        directory.mkdir(parents=True, exist_ok=True)
        logging.info("%s created", directory)


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

    If a name collision occurs, appends a numeric suffix (`_1`, `_2`, ...) to the
    stem before moving.

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


# ---------- person detection ----------

# setup detection model
def setup_detection_model(threshold: float) -> DefaultPredictor:
    """
    Initializes a detection model by configuring its parameters.

    This function sets up the model with specific configurations for the COCO-Keypoints
    model, including device configuration, merging the model, setting a threshold,
    and saving the model weights.

    Args:
        None

    Returns:
        A DefaultPredictor object, that accepts BGR imges, which is the configured detection model.
    """
    logging.info("Setting up Detectron2 model")
    cfg.MODEL.DEVICE = 'cpu' # Set the device to CPU to avoid GPU usage.  This is a common practice
    cfg.merge_from_file(model_zoo.get_config_file(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml")) # Load the configuration file
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold  # Set threshold for the scoring model
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml") # Retrieve the model checkpoint URL
    logging.info("done with setting up model")
    return DefaultPredictor(cfg)


def count_persons_in_image(predictor: DefaultPredictor, image) -> int:
    """Count detected persons (COCO class id = 0) in an image.

    Args:
        predictor: A configured `DefaultPredictor`.
        img_bgr: A BGR image array as returned by `cv2.imread`.

    Returns:
        Number of detected persons.

    Notes:
        - If `pred_classes` is not present (very unlikely), falls back to
          the number of instances (which may overcount non-person classes).
    """
    outputs = predictor(image)
    instances = outputs["instances"]
    count_instances = len(instances)

    try:
        classes = instances.pred_classes.tolist()
        logging.info("using classes")
        return sum(1 for klasse in classes if klasse == 0)
    except AttributeError:
        logging.info("using count_instances")
        return count_instances


# ---------- pipeline ----------

def setup_logging() -> None:
    """
    Configure logging for CLI usage.
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


def proces_images(arguments: Namespace):
    """Run the full classification/move pipeline and write a summary CSV.

    Steps:
        1. Read image list.
        2. Resolve output root and ensure category directories.
        3. Initialize predictor.
        4. For each image:
            - Read, and remove unreadable files.
            - Count persons.
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

    predictor = setup_detection_model(arguments.threshold)
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

            num_persons = count_persons_in_image(predictor, img)

            if num_persons == 1:
                category = "portrets"
            elif num_persons == 0:
                category = "empty"
            else:
                category = "group"

            destination_directory = find_directory(img_path, category, location, subdirectories)
            destination_path = move_file(img_path, destination_directory)
            summary_rows.append([img_path, str(destination_path), str(num_persons)])

            logging.info("%s -> %s (%s faces)", img_path, destination_directory, str(num_persons))

        except OSError as e:
            logging.exception("Error processing %s: %s", img_path, e)

    write_summary_csv(location, summary_rows)

def setup_parser() -> Namespace:
    """Parse CLI arguments.

    Args:
        None

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
    proces_images(argument_list)
