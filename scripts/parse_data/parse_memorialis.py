"""Module for parsing the data of UGent Memorialis and convert it to the VNA CSV-format"""

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
                person.identifierviaf = get_viaf_id(parts[1])

    find_wikidata_qid(person)
    return person

def find_wikidata_qid(person: Person) -> None:

    if person.id in qids:
        person.identifier.wikidata = qids[person.id]

def parse_date_and_place(date_and_place: str) -> Event:
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
    place = ''
    for part in parts:
        place += f"{part.strip()}, "
    return beautify_string(place)


def parse_pictures(person: Person, json_data: dict):
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
    for url in urls:
        if url.endswith('.jpg'):
            if not '.pdf' in url:
                person.picture = url


def get_names(person: Person, names: List[str]) -> None:
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
    for occupation in occupations:
        person.occupation += f"{occupation.strip()}, "

    person.occupation = beautify_string(person.occupation)


if __name__ == "__main__":
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
