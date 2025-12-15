"""Download Wikimedia Commons files per CSV row by category and/or single file.

For each row in `SOURCE_FILE`:
  - If 'Commonscategorie' is present, download all files in that Commons
    category into `<OUTPUT_FOLDER>/<Wikidata ID>/`.
  - If 'afbeelding' is present, download that one Commons file title into the
    same directory.

Technologies:
  - Pywikibot `Site`, `Category`, and `pagegenerators` for listing and
    downloading category members (files).
  - External `wikiget` command for downloading a file by title.

After processing, the script removes `apicache` and `throttle.ctrl` created by
Pywikibot in the current working directory.

CSV must be UTF-8 and include headers:
  'Wikidata ID', 'volledige naam', 'Commonscategorie', 'afbeelding'.
"""

from csv import DictReader
import os
from pathlib import Path
import shutil
from sys import argv
from pywikibot import Site, Category, pagegenerators

SOURCE_FILE = argv[1]
OUTPUT_FOLDER = argv[2]

def download_category(download_path: str | Path, name: str) -> None:
    """Download all file pages in a Commons category into a directory.

    Builds 'Category:<name>' on the 'commons' wiki, iterates category members,
    and downloads each page whose title starts with 'File:' into `download_path`.
    Non-file pages are skipped.

    Args:
        download_path (str | pathlib.Path): Destination directory for files.
        name (str): Commons category name without the 'Category:' prefix.

    Side Effects:
        - Network calls to Wikimedia Commons via Pywikibot.
        - Writes one file per 'File:' page to `download_path`.
        - Prints progress and any exceptions encountered.

    Notes:
        - Category traversal is shallow: members only, not subcategories.
        - Filenames match the page title minus the 'File:' prefix.
    """
    category_name = "Category:" + name
    site = Site("commons", "commons")
    category = Category(site, category_name)
    generator = pagegenerators.CategorizedPageGenerator(category)
    for page in generator:
        filename = str(page.title())
        if filename.startswith('File:'):
            filename = filename[5:]
        try:
            print(f"downloading {filename}")
            page.download(f"{download_path}/{filename}")
        except Exception as error:
            print(error)

def download_image(download_path: str | Path, image):
    """Download a single Commons file by title using the `wikiget` CLI.

    Constructs the Commons title as 'File:<image>' and invokes:
        wikiget "File:<image>" -o "<download_path>/<image>"

    Args:
        download_path (str | pathlib.Path): Destination directory for the file.
        image (str): Commons file title WITHOUT the 'File:' prefix.

    Side Effects:
        - Spawns an external 'wikiget' process via `os.system`.
        - Writes the downloaded file to the destination path.
        - Prints progress messages.

    Notes:
        - Requires 'wikiget' to be installed and in PATH.
        - Exit codes are not checked here; failures will print but not raise.
    """
    image_path = "File:" + image
    output_path = f"{download_path}/{image}"
    command = f'wikiget \"{image_path}\" -o \"{output_path}\"'
    print("downloading " + image)
    os.system(command)


if __name__ == '__main__':
    with open(SOURCE_FILE, 'r', encoding='utf-8') as csv_file:
        reader =  DictReader(csv_file)

        for row in reader:
            commons_category = row["Commonscategorie"]
            image_file = row["afbeelding"]

            if commons_category or image_file:
                # Creates <OUTPUT_FOLDER>/<Wikidata ID>/ and downloads category &/or file
                print(f"busy with {row['Wikidata ID']}: {row['volledige naam']}")
                PATH = f"{OUTPUT_FOLDER}/{row['Wikidata ID']}"
                Path(PATH).mkdir(parents=True, exist_ok=True)

                if commons_category:
                    download_category(PATH, commons_category)

                if image_file:
                    download_image(PATH, image_file)

                print("done\n")

    # Clean up Pywikibot artifacts in the current working directory:
    shutil.rmtree('apicache')
    os.remove('throttle.ctrl')
