"""Download images from URLs listed in a CSV.

Reads a UTF-8 (or configured `ENCODING`) CSV with at least:
    - `URI_COLUMN` : used to derive the output file's base name
                     (last path segment of the value).
    - `PHOTO_COLUMN`: direct image URL to fetch.

For each row:
  * If the photo URL is present and the target file does not yet exist,
    download via `wget -O <FOLDER>/<image_id>.jpg <url>` using
    `subprocess.run(check=True)`.
  * Sleep 3 seconds after a successful download.
  * Skip rows with empty photo URL and files that already exist.

Notes:
    - Requires `wget` on PATH; downloads are executed via subprocess.
    - The output folder is created if missing.
"""
from csv import DictReader
from sys import argv
from time import sleep
import os
import subprocess

SOURCEFILE = argv[1]
FOLDER = argv[2]
PHOTO_COLUMN = 'foto'
URI_COLUMN = 'uri'
ENCODING = 'utf-8'

def get_picture(url: str, filename: str) -> bool:
    """Download a single image to the given filename using `wget`.

    Invokes:
        wget -O <filename> <url>

    Args:
        url: Direct URL to the image resource.
        filename: Full filesystem path (including extension) where the image
            will be written. Parent directories should already exist.

    Returns:
        bool: True if `wget` exited with status 0; False on non-zero exit.
        On failure, a zero-byte file (if created) is best-effort removed.

    Side Effects:
        - Spawns an external process (`wget`).
        - Writes the downloaded file to disk on success.

    Raises:
        None directly. Internally catches `subprocess.CalledProcessError` and
        converts it to a False return value.
    """
    print(f"getting picture {url}")
    try:
        subprocess.run(
            ["wget", "-O", filename, url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("f[ERROR] wget failed (exit {e.returncode}) for {url}")
        if e.stderr:
            print(e.stderr.strip())
        try:
            if os.path.exists(filename) and os.path.getsize(filename) == 0:
                os.remove(filename)
        except OSError:
            pass
        return False

def main():
    """Read the source CSV and download images row-by-row.

    Workflow:
        1) Ensure the output folder exists.
        2) Iterate over rows from `SOURCEFILE` using the specified `ENCODING`.
        3) Derive `image_id` from the last path segment of `row[URI_COLUMN]`.
        4) Build `<FOLDER>/<image_id>.jpg` as the destination filename.
        5) If `row[PHOTO_COLUMN]` is present and the destination does not exist:
             - Call `get_picture(url_string, filename)`.
             - On success: sleep 2 seconds (politeness).
             - On failure: log a warning and continue.
        6) If no photo URL: print 'no picture' and continue.
        7) If the destination already exists: print a notice and skip.

    Environment/Globals:
        - `SOURCEFILE`: Path to the input CSV (argv[1]).
        - `FOLDER`: Output directory for downloaded images (argv[2]).
        - `PHOTO_COLUMN`, `URI_COLUMN`, `ENCODING`: in-script constants.

    Side Effects:
        - Creates the output directory if missing.
        - Spawns external `wget` processes.
        - Writes images to `FOLDER`.
        - Emits progress and error messages to stdout/stderr.

    Returns:
        None
    """
    os.makedirs(FOLDER, exist_ok=True)

    with open(SOURCEFILE, 'r', encoding=ENCODING) as source:
        reader = DictReader(source)
        for row in reader:
            image_id = row[URI_COLUMN].split('/')[-1]
            url_string = row[PHOTO_COLUMN]
            print(f"busy with {image_id}")

            if not url_string:
                print("no picture")
                continue

            filename = f'{FOLDER}/{image_id}.jpg'
            if os.path.exists(filename):
                print(f"image {filename} already exists")
                continue

            ok = get_picture(url_string, filename)
            if ok:
                sleep(2)
            else:
                print(f'[WARN] download failed for {url_string}')

if __name__ == '__main__':
    main()
