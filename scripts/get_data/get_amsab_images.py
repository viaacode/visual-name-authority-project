"""Module for downloading IIIF images of Amsab-ISG"""

from csv import DictReader
import os
from time import sleep
from dotenv import load_dotenv

load_dotenv()

# constants
CSV = os.getenv('AMSAB_FOTOS')
OUTPUT_FOLDER = os.getenv('AMSAB_FOLDER')
MANIFEST = "https://iiif.amsab.be/iiif/3/manifest/52772"
KEYS = ['PID_IIIF_1', 'PID_IIIF_2', 'PID_IIIF_3', 'PID_IIIF_4', 'PID_IIIF_5', 'Zij-aanzicht_IIIF']
IDENTIFIERS = {
    KEYS[0]: 'PID_OPAC_1',
    KEYS[1]: 'PID_OPAC_2',
    KEYS[2]: 'PID_OPAC_3',
    KEYS[3]: 'PID_OPAC_4',
    KEYS[4]: 'PID_OPAC_5',
    KEYS[5]: 'Zij aanzicht_OPAC'
}


def download_image(url, path, filename):
    """ download the image from a IIIF manifest"""
    iiif_manifest = url.split("=")[-1]
    print(iiif_manifest)
    if not os.path.exists(path):
        os.mkdir(path)
    os.system(
        f"wget -O {path}/{filename}.jpg -nc $(curl {iiif_manifest} | jq -r '.items[].items[].items[].body.id')")
    sleep(2)


def start():
    "get manifest urls and download image"
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
