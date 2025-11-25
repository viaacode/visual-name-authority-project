"""Module for downloading IIIF images of Amsab-ISG"""

from csv import DictReader, writer
import os
from sys import argv
from time import sleep

# constants
CSV = argv[1]
OUTPUT_FOLDER = argv[2]
OUTPUT_FILE = 'output.csv'
MANIFEST_COLUMN = "manifest" # requires a column that contains the link to the manifest
PERSON_COLUMN = "volledige naam" # requires a column that contains the name of a person

lines = []

def download_image(url: str, path: str, filename: str) -> bool:
    """Download the image from a IIIF manifest"""
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

def write_csv(csv_lines):
    """ write results in csv """
    output_path = f'{OUTPUT_FOLDER}/{OUTPUT_FILE}'
    with open(output_path, 'w', encoding='utf-8') as output_file:
        csv_writer = writer(output_file)
        csv_writer.writerows(csv_lines)

def start():
    "get manifest urls and download image"
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
