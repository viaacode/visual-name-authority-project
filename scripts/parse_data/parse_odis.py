"""Module for reading and writing JSON"""
import json
from typing import List
from sys import path, argv
from pathlib import Path

# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, Event, beautify_string, get_dbnl_id, get_wikidata_id, write_csv

JSON_KEY_NAMES = {
    'URI': 'URL',
    'NAMES': 'PS_NAMEN',
    'NAME': 'NAAM',
    'NAME_TYPE': 'NAAMSOORT',
    'DEATH_PLACE': 'PS_OVERLIJDENSPLAATS',
    'BIRTH_PLACE': 'PS_GEBOORTEPLAATS',
    'DEATH_DATE': 'PS_OVERLIJDENSDATUM',
    'BIRTH_DATE': 'PS_GEBOORTEDATUM',
    'PICTURE': 'PS_ILLUSTRATIES',
    'AUTHORITIES': 'PS_BIJLAGEN'
}

AUTHORITIES = {
    'VIAF': 'Virtual International Authority File (VIAF)',
    'WIKIDATA': 'Wikidata',
    'DBNL': 'Digitale Bibliotheek voor de Nederlandse Letteren'
}

FILE = argv[1]
OUTPUT = argv[2]

def get_person_data(json_data: dict) -> Person:
    person = Person()
    person.identifier.uri = f"{json_data[JSON_KEY_NAMES['URI']]}"
    person.identifier.odis = f"{json_data['RUBRIEK']}_{json_data['ID']}"
    print(person.identifier.odis)
    person.name.full = f"{json_data['OMSCHRIJVING']}"

    steekkaarten = json_data['STEEKKAART']
    for steekkaart in steekkaarten:
        names = steekkaart['PS_NAMEN']
        parse_names(person, names)

        person.birth = Event(steekkaart.get(JSON_KEY_NAMES['BIRTH_PLACE'], ''), 
                             steekkaart.get(JSON_KEY_NAMES['BIRTH_DATE'], ''))
        person.death = Event(steekkaart.get(JSON_KEY_NAMES['DEATH_PLACE'], ''), 
                             steekkaart.get(JSON_KEY_NAMES['DEATH_DATE'], ''))
                
        pictures = steekkaart.get(JSON_KEY_NAMES['PICTURE'])
        if pictures:
            for picture in pictures:
                person.picture += f'ID: {picture.get('ID')}, '
            person.picture = beautify_string(person.picture)

        authorities = steekkaart.get(JSON_KEY_NAMES['AUTHORITIES'], [])
        if authorities:
            parse_authorities(person, authorities)
    return person

def parse_names(person: Person, names: List[dict]) -> None:
    lastnames = []
    for name in names:
        naamsoort = name['NAAMSOORT']
        naam = name['NAAM']
        if naam:
            naam = naam.rstrip()
            if 'voornaam' in naamsoort:
                person.name.first += f'{naam} '
            elif 'familienaam' in naamsoort:
                lastnames.append(naam)
            else:
                person.name.alias += f'{naam}, '
    person.name.last = lastnames[0]
    lastnames_length = len(lastnames)
    if lastnames_length > 1:
        for index in range(1, lastnames_length):
            person.name.alias += f'{lastnames[index]}, '

    person.name.first = beautify_string(person.name.first)
    person.name.alias = beautify_string(person.name.alias)

def parse_authorities(person: Person, authorities: List[dict]) -> None:
    for authority in authorities:
        authority_type = authority['B_LINKTXT']
        authority_url = authority['B_URL']
        if authority_type:
            if authority_type == AUTHORITIES['VIAF']:
                identifier = authority_url.split('/')[-2]
                person.viaf = identifier
            if authority_type == AUTHORITIES['WIKIDATA']:
                person.identifier.wikidata = get_wikidata_id(authority_url)
            if authority_type.strip() == AUTHORITIES['DBNL']:
                person.identifier.dbnl = get_dbnl_id(authority_url)

# main
if __name__ == "__main__":

    persons = []

    with open(FILE, "r", encoding='utf-8') as json_file:
        data = json.load(json_file)
        for agent in data:
            persons.append(get_person_data(agent))

    write_csv(OUTPUT, persons)
