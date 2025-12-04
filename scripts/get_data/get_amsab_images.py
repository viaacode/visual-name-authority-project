"""Module for downloading IIIF images of Amsab-ISG.

Reads a CSV file (path from the `AMSAB_FOTOS` environment variable) and,
for each row, downloads images referenced by IIIF Presentation API v3
manifests found in the columns listed in `KEYS`. Images are written
to `<AMSAB_FOLDER>/<URL>/<IDENTIFIER>.jpg`, where `<URL>` is the per-row
person id and `<IDENTIFIER>` is derived from a paired column in `IDENTIFIERS`.

External tools required on PATH: `curl`, `jq`, `wget`.
Environment variables are loaded from a `.env` file via `python-dotenv`.
"""

from csv import DictReader
import os
from time import sleep
from dotenv import load_dotenv

load_dotenv()

# constants
CSV = os.getenv('AMSAB_FOTOS')
OUTPUT_FOLDER = os.getenv('AMSAB_FOLDER')
KEYS = ['PID_IIIF_1', 'PID_IIIF_2', 'PID_IIIF_3', 'PID_IIIF_4', 'PID_IIIF_5', 'Zij-aanzicht_IIIF']
IDENTIFIERS = {
    KEYS[0]: 'PID_OPAC_1',
    KEYS[1]: 'PID_OPAC_2',
    KEYS[2]: 'PID_OPAC_3',
    KEYS[3]: 'PID_OPAC_4',
    KEYS[4]: 'PID_OPAC_5',
    KEYS[5]: 'Zij aanzicht_OPAC'
}


def download_image(url: str, path: str, filename: str):
    """Download an image referenced by a IIIF manifest and save it as JPG.

    Resolves the image URL from a IIIF Presentation API v3 manifest by piping
    `curl <manifest>` into `jq -r '.items[].items[].items[].body.id'`, and then
    downloads the image with `wget` to `<path>/<filename>.jpg`. Creates the
    destination directory if needed. Waits 2 seconds after the download.

    Args:
        url (str): A string containing (or ending with) a IIIF manifest URL.
            The code extracts the manifest URL as `url.split('=')[-1]`, so the
            input may be either the manifest itself or a wrapper URL that
            contains it as the last `=` value.
        path (str): Destination directory where the image file will be saved.
        filename (str): Basename of the output file (without extension).

    Returns:
        None

    Notes:
        - Uses `os.system` to invoke `wget`, `curl`, and `jq`. This does not
          raise Python exceptions on failure; it only returns a shell exit code.
        - The `-nc` flag prevents overwriting an existing file.
        - Assumes IIIF Presentation API v3 structure at `.items[].items[].items[].body.id`.
    """

    iiif_manifest = url.split("=")[-1]
    print(iiif_manifest)
    if not os.path.exists(path):
        os.mkdir(path)
    os.system(
        f"wget -O {path}/{filename}.jpg -nc $(curl {iiif_manifest} | jq -r '.items[].items[].items[].body.id')")
    sleep(2)


def start():
    """Read the CSV and download images for each person row.

    For every row in the CSV located at `AMSAB_FOTOS`:
      1. Read `person_id` from the `URL` column and build the output directory
         as `<AMSAB_FOLDER>/<person_id>`.
      2. For every column name in `KEYS` that has a non-empty value:
         - Extract the paired identifier column from `IDENTIFIERS[key]`.
         - Use the last path segment of that identifier as the output filename.
         - Call `download_image(row[key], path, filename)`.

    Returns:
        None

    Raises:
        FileNotFoundError: If the CSV path from `AMSAB_FOTOS` does not exist.
        KeyError: If required columns (e.g., `URL`, paired identifier columns)
            are missing from the CSV.
    """

    with open(CSV, 'r', encoding='utf-8') as input_file:
        reader = DictReader(input_file)
        for row in reader:
            person_id = row['URL']
            print(person_id)
            for key in KEYS:
                if row[key]:
                    filename = row[IDENTIFIERS.get(key)].split('/')[-1]
                    path = f"{OUTPUT_FOLDER}/{person_id}"
                    download_image(row[key], path, filename)

if __name__ == "__main__":
    start()
