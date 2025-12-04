"""Download images referenced by IIIF Presentation API v3 manifests listed in a CSV.

For each row in the input CSV, the script:
  1) reads a manifest URL from `MANIFEST_COLUMN`,
  2) resolves the image URL via `curl | jq` at JSON path
     `.items[].items[].items[].body.id`, and
  3) downloads the image with `wget` into `OUTPUT_FOLDER`.

A small results CSV (manifest → filename/FAILED!) is written to
`<OUTPUT_FOLDER>/<OUTPUT_FILE>`.

Notes:
    - Requires CLI tools `curl`, `jq`, and `wget` to be available on PATH.
    - Uses `os.system(...)`; command failures are logged as `FAILED!` rows.
    - Sleeps 2 seconds between downloads to be polite.
"""

from csv import DictReader, writer
import os
from sys import argv
from time import sleep

# constants
CSV = argv[1]
OUTPUT_FOLDER = argv[2]
OUTPUT_FILE = 'output.csv' # change this
MANIFEST_COLUMN = "manifest" # requires a column that contains the link to the manifest
PERSON_COLUMN = "volledige naam" # requires a column that contains the name of a person

lines = []

def download_image(url: str, path: str, filename: str) -> bool:
    """Download an image from a IIIF manifest into `path/filename`.

    Resolves the image URL by piping `curl <manifest>` into:
        jq -r '.items[].items[].items[].body.id'
    and downloads the result with:
        wget -O <path>/<filename> <image-url>

    Args:
        url: IIIF Presentation API v3 manifest URL.
        path: Destination directory where the image will be saved.
        filename: Target filename (including extension, e.g., 'abc.jpg').

    Returns:
        True if the shell commands were invoked (not necessarily success),
        False if an `OSError` occurred when launching them.

    Notes:
        - This function uses `os.system(...)`, which does not raise an
          exception on non-zero exit codes; it only returns a status code.
          Failures will still return True from this function unless an
          `OSError` is raised during process creation.
        - Sleeps 2 seconds after the attempt.
    """
    iiif_manifest = url
    print(iiif_manifest)
    try:
        os.system(
            f"wget -O {path}/{filename} $(curl {iiif_manifest} | jq -r '.items[].items[].items[].body.id')")
        sleep(2)
        return True
    except OSError as e:
        print(f"{iiif_manifest} failed with error {e}")
        return False

def write_csv(csv_lines:list[list[str]]):
    """Write the results list to `<OUTPUT_FOLDER>/<OUTPUT_FILE>` as CSV.

    Each row should be a two-element list: `[manifest, filename-or-FAILED!]`.

    Args:
        csv_lines: Iterable of rows to write (e.g., `lines` global).

    Returns:
        None

    Notes:
        - The file is opened with UTF-8 encoding and overwritten if it exists.
    """
    output_path = f'{OUTPUT_FOLDER}/{OUTPUT_FILE}'
    with open(output_path, 'w', encoding='utf-8') as output_file:
        csv_writer = writer(output_file)
        csv_writer.writerows(csv_lines)

def start():
    """Main entry point: read CSV, download images, write results CSV.

    Steps:
        1) Open the input CSV specified by `CSV`.
        2) For each row:
            - Read `manifest` from `MANIFEST_COLUMN`.
            - If present:
                * Print the person name from `PERSON_COLUMN` (for context).
                * Derive `filename` from the manifest URL's second-to-last
                  path segment, plus a `.jpg` extension.
                * Attempt to download via `download_image(...)`.
                * Append `[manifest, filename]` or `[manifest, 'FAILED!']`
                  to the global `lines` list.
            - If missing: append `[manifest, '']`.
        3) Call `write_csv(lines)` to persist the results.

    Returns:
        None

    Side Effects:
        - Network calls via external tools (curl, jq, wget).
        - Writes images to `OUTPUT_FOLDER`.
        - Writes a results CSV to `OUTPUT_FOLDER/OUTPUT_FILE`.
    """
    with open(CSV, 'r', encoding='utf-8') as input_file:
        reader = DictReader(input_file)
        for row in reader:
            manifest = row[MANIFEST_COLUMN]
            if len(manifest) > 0:
                person = row[PERSON_COLUMN]
                print(person)
                filename = f"{manifest.split('/')[-2]}.jpg"
                path = f"{OUTPUT_FOLDER}"
                if download_image(manifest, path, filename):
                    lines.append([manifest, filename])
                else:
                    lines.append([manifest, "FAILED!"])
            else:
                lines.append([manifest, ''])
    write_csv(lines)

if __name__ == "__main__":
    start()
