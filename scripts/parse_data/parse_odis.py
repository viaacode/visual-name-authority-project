"""Convert ODIS person JSON to a VNA-formatted CSV.

Reads an ODIS export (list of agent records), builds `scripts.person.Person`
objects by mapping names, birth/death data, pictures, and external authorities,
and writes all persons with `write_csv(OUTPUT, persons)`.
"""
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
    """Build a Person from a single ODIS agent object.

    Populates:
        - identifier.uri from top-level 'URL'
        - identifier.odis from "<RUBRIEK>_<ID>"
        - name.full from 'OMSCHRIJVING'
        - name.first/last/alias from each STEEKKAART.PS_NAMEN[]
        - birth/death (place/date) from STEEKKAART.{PS_GEBOORTEPLAATS,
          PS_GEBOORTEDATUM, PS_OVERLIJDENSPLAATS, PS_OVERLIJDENSDATUM}
        - picture as a comma-separated list of 'ID: <ID>' from
          STEEKKAART.PS_ILLUSTRATIES[]
        - external authorities via `parse_authorities(...)`

    Args:
        json_data: A dict representing one agent/person record from ODIS.

    Returns:
        Person: A fully-populated Person instance for the record.
    """
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
    """Map ODIS name parts to Person.name fields.

    Rules:
        - If NAAMSOORT contains 'voornaam'  → append NAAM to person.name.first
        - If NAAMSOORT contains 'familienaam':
            * First occurrence becomes person.name.last
            * Additional family names are appended to person.name.alias
        - Otherwise → NAAM is appended to person.name.alias

    Trailing spaces/commas are removed with `beautify_string`.

    Args:
        person: Target Person to mutate.
        names:  List of name dicts with keys NAAMSOORT and NAAM.
    """
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
    """Extract external IDs (VIAF, Wikidata, DBNL) from ODIS 'bijlagen'.

    Behavior:
        - VIAF: take the numeric ID from the URL (second-to-last path segment)
                and assign to `person.identifier.viaf`.
        - Wikidata: set `person.identifier.wikidata` using QID parsed from the URL.
        - DBNL: set `person.identifier.dbnl` using the 'id=' query parameter.

    Args:
        person: Target Person to update.
        authorities: List of attachment dicts with 'B_LINKTXT' and 'B_URL'.
    """
    for authority in authorities:
        authority_type = authority['B_LINKTXT']
        authority_url = authority['B_URL']
        if authority_type:
            if authority_type == AUTHORITIES['VIAF']:
                identifier = authority_url.split('/')[-2]
                person.identifier.viaf = identifier
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
