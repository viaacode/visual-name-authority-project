"""Parse UGent Memorialis JSON records and export to a VNA-formatted CSV.

For each JSON file in `MEMORIALIS_FOLDER`, extract identifiers, names,
birth/death data, occupations, and a picture URL, map them onto a
`scripts.person.Person`, and write all persons to `OUTPUT_FILE` via
`scripts.person.write_csv`.

Environment:
    MEMORIALIS_FOLDER: directory with Memorialis JSON files.
    MEMORIALIS_QIDS: CSV file mapping 'id' -> 'QID' for Wikidata lookup.
"""

import csv
import json
import os
from typing import List
from sys import path, argv
from pathlib import Path

from dotenv import load_dotenv

# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, Event, beautify_string, get_viaf_id, write_csv

OUTPUT_FILE = argv[1]
qids = {}

load_dotenv()

JSON_KEY_NAMES = {
    'ID': '_id',
    'NAME': 'title_t',
    'DEATH': 'death_date_display',
    'BIRTH': 'birth_date_display',
    'OCCUPATION': 'mandate_facet',
    'PICTURE_1': 'thumbnail_display',
    'PICTURE_2': 'thumbnail_link_url_display',
    'PICTURE_3': 'thumbnail_url_display',
    'AUTHORITIES': 'link_display'
}

AUTHORITIES = {
    'VIAF': 'Virtual International Authority File'
}


FOLDER = os.getenv('MEMORIALIS_FOLDER')
QID_FILE = os.getenv('MEMORIALIS_QIDS') # file with id and qid of memorialis agent


def get_person_data(json_data: str) -> Person:
    """Build and return a Person from a single Memorialis JSON payload.

    Expected structure:
        json_data['response']['document'] -> dict with fields in JSON_KEY_NAMES.

    Populates:
        - person.id and person.identifier.uri
        - Names (first/last/full and alias) via `get_names(...)`
        - Picture via `parse_pictures(...)`
        - Occupation via `parse_occupation(...)`
        - Birth/Death via `parse_date_and_place(...)`
        - VIAF from `link_display` (if present)
        - Wikidata QID via `find_wikidata_qid(...)`

    Args:
        json_data: Parsed JSON object for a single record.

    Returns:
        A populated Person instance.
    """
    person = Person()
    document = json_data['response']['document']

    person.id = document.get(JSON_KEY_NAMES['ID'], '')

    person.identifier.uri = f"https://www.ugentmemorialis.be/catalog/{person.id}"
    get_names(person, document[JSON_KEY_NAMES['NAME']])

    parse_pictures(person, document)
    if JSON_KEY_NAMES['OCCUPATION'] in document:
        parse_occupation(person, document[JSON_KEY_NAMES['OCCUPATION']])

    if JSON_KEY_NAMES['BIRTH'] in document:
        person.birth = parse_date_and_place(
            document[JSON_KEY_NAMES['BIRTH']][0])

    if JSON_KEY_NAMES['DEATH'] in document:
        person.death = parse_date_and_place(
            document[JSON_KEY_NAMES['DEATH']][0])

    if JSON_KEY_NAMES['AUTHORITIES'] in document:
        authorities = document[JSON_KEY_NAMES['AUTHORITIES']]
        for authority in authorities:
            parts = authority.split(']')
            if AUTHORITIES['VIAF'] in parts[0]:
                person.identifier.viaf = get_viaf_id(parts[1])

    find_wikidata_qid(person)
    return person

def find_wikidata_qid(person: Person) -> None:
    """Set `person.identifier.wikidata` from the global `qids` mapping if available.

    Uses the person's local `id` as the lookup key.

    Args:
        person: Person to update in place.
    """
    if person.id in qids:
        person.identifier.wikidata = qids[person.id]

def parse_date_and_place(date_and_place: str) -> Event:
    """Split a freeform 'place,date' string into an Event(place, date).

    Heuristics:
        - If the last comma-separated token is all digits -> treat as date.
          The preceding tokens (if any) are joined (', ') as place.
        - If no comma:
            * digits-only string -> date
            * otherwise -> place

    Args:
        date_and_place: Input like 'Ghent, 1901' or 'Antwerp' or '1905'.

    Returns:
        Event with `.place` and `.date` filled accordingly (strings).
    """
    date = ""
    place = ""
    if ',' in date_and_place:
        parts = date_and_place.split(',')
        if parts[-1].strip().isdigit():
            date = parts[-1].strip()
            place = parse_place(parts[0:len(parts) - 1])
        else:
            place = parse_place(parts)
    else:
        if date_and_place.isdigit():
            date = date_and_place
        else:
            place = date_and_place
    return Event(place, date)


def parse_place(parts: List[str]) -> str:
    """Join and normalize a list of place tokens.

    Trims individual tokens and joins them with ', ', then removes any
    trailing comma via `beautify_string`.

    Args:
        parts: List of strings representing place components.

    Returns:
        A cleaned, comma-separated place string.
    """
    place = ''
    for part in parts:
        place += f"{part.strip()}, "
    return beautify_string(place)


def parse_pictures(person: Person, json_data: dict):
    """Pick the first available JPG URL from known picture fields.

    Checks keys in this order:
        1) JSON_KEY_NAMES['PICTURE_1'] (= 'thumbnail_display')
        2) JSON_KEY_NAMES['PICTURE_2'] (= 'thumbnail_link_url_display')
        3) JSON_KEY_NAMES['PICTURE_3'] (= 'thumbnail_url_display')

    The first field found is passed to `get_picture(...)`.

    Args:
        person: Person to update in place.
        json_data: The 'document' dictionary from the JSON payload.
    """
    if JSON_KEY_NAMES['PICTURE_1'] in json_data:
        pictures = json_data[JSON_KEY_NAMES['PICTURE_1']]
        get_picture(person, pictures)
    elif JSON_KEY_NAMES['PICTURE_2'] in json_data:
        pictures = json_data[JSON_KEY_NAMES['PICTURE_2']]
        get_picture(person, pictures)
    elif JSON_KEY_NAMES['PICTURE_3'] in json_data:
        pictures = json_data[JSON_KEY_NAMES['PICTURE_3']]
        get_picture(person, pictures)


def get_picture(person: Person, urls: List[str]) -> None:
    """Assign a JPG URL to `person.picture` from a list, if present.

    Picks the first URL that ends with '.jpg' and does not contain '.pdf'.

    Args:
        person: Person to update.
        urls: List of candidate URLs.
    """
    for url in urls:
        if url.endswith('.jpg'):
            if not '.pdf' in url:
                person.picture = url


def get_names(person: Person, names: List[str]) -> None:
    """Populate name fields from a list of 'Last, First' variants.

    Behavior:
        - `names[0]` must be 'Last, First' and sets:
            person.name.last, person.name.first, person.name.full
        - Additional entries `names[1:]` are appended to `person.name.alias`
          as 'First Last', separated by commas.

    Args:
        person: Person to update.
        names: List of strings from the 'title_t' field.
    """
    first_and_last = names[0].split(',')
    person.name.first = first_and_last[1].strip()
    person.name.last = first_and_last[0].strip()
    person.name.full = f"{person.name.first} {person.name.last}"

    length = len(names)
    if length > 1:
        for index in range(1, length):
            name = names[index]
            if ',' in name:
                first_and_last = name.split(',')
                person.name.alias += f"{first_and_last[1].strip()} {first_and_last[0]}, "
            else:
                person.name.alias += f"{name}, "
        person.name.alias = beautify_string(person.name.alias)


def parse_occupation(person: Person, occupations: List[str]) -> None:
    """Append occupations to `person.occupation` as a comma-separated string.

    Args:
        person: Person to update.
        occupations: List of occupation labels.

    Side Effects:
        - Updates `person.occupation` (trimming the trailing comma).
    """
    for occupation in occupations:
        person.occupation += f"{occupation.strip()}, "

    person.occupation = beautify_string(person.occupation)


if __name__ == "__main__":
    # 1) Load id->QID mapping into global `qids`
    # 2) Iterate JSON files under FOLDER, building Person instances
    # 3) Write VNA CSV to OUTPUT_FILE using write_csv
    persons = []

    with open(QID_FILE, 'r', encoding='utf-8') as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            qids[row['id']] = row['QID']

    for filename in os.listdir(FOLDER):
        file_path = os.path.join(FOLDER, filename)
        if file_path.endswith('.json'):
            print(file_path)
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                persons.append(get_person_data(data))

    write_csv(OUTPUT_FILE, persons)
