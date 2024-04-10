import csv
import json
from person import Person, beautify_string, get_dbnl_id, get_wikidata_id
from typing import List

JSON_KEY_NAMES = {
    'NAMES': 'PS_NAMEN',
    'NAME': 'NAAM',
    'NAME_TYPE': 'NAAMSOORT',
    'DEATH_PLACE': 'PS_OVERLIJDENSPLAATS',
    'BIRTH_PLACE': 'PS_GEBOORTEPLAATS',
    'DEATH_DATE': 'PS_OVERLIJDENSDATUM',
    'BIRTH_DATE': 'PS_GEBOORTEDATUM',
    'SEX': 'PS_GESLACHT',
    'PICTURE': 'PS_ILLUSTRATIES',
    'AUTHORITIES': 'PS_BIJLAGEN'
}

AUTHORITIES = {
    'VIAF': 'Virtual International Authority File (VIAF)',
    'WIKIDATA': 'Wikidata',
    'BELELITE': 'Belelite',
    'DBNL': 'Digitale Bibliotheek voor de Nederlandse Letteren'
}

file = "Data/KADOC_ODIS/20240327_export_ODIS_PS_KADOC.json"

def get_person_data(json_data: dict) -> Person:
    person = Person()
    person.uri = "{}_{}".format(json_data['RUBRIEK'], json_data['ID'])
    person.fullname = "{}".format(json_data['OMSCHRIJVING'])

    steekkaarten = json_data['STEEKKAART']
    for steekkaart in steekkaarten:
        names = steekkaart['PS_NAMEN']
        parse_names(person, names)            
        
        person.birthdate = steekkaart.get(JSON_KEY_NAMES['BIRTH_DATE'], '')
        person.deathdate = steekkaart.get(JSON_KEY_NAMES['DEATH_DATE'], '')
        person.place_of_birth = steekkaart.get(JSON_KEY_NAMES['BIRTH_PLACE'], '')
        person.place_of_death = steekkaart.get(JSON_KEY_NAMES['DEATH_PLACE'], '')
        person.sex = steekkaart.get(JSON_KEY_NAMES['SEX'], '')
        
        pictures = steekkaart.get(JSON_KEY_NAMES['PICTURE'])
        if pictures:
            for picture in pictures:
                person.picture += 'ID: {}, '.format(picture.get('ID'))
            person.picture = beautify_string(person.picture)

        authorities = steekkaart.get(JSON_KEY_NAMES['AUTHORITIES'], [])
        if authorities:
            parse_authorities(person, authorities)
    return person

def parse_names(person: Person, names: List[dict]) -> None:
    lastnames = []
    for name in names:
        naamsoort = name['NAAMSOORT']
        naam = name['NAAM'].rstrip()
        if 'voornaam' in naamsoort:
            person.firstname += '{} '.format(naam)
        elif 'familienaam' in naamsoort:
            lastnames.append(naam)
        else:
            person.alias += '{}, '.format(naam)
    person.lastname = lastnames[0]
    lastnames_length = len(lastnames)
    if lastnames_length > 1:
        for index in range(1, lastnames_length):
            person.alias += '{}, '.format(lastnames[index])

    person.firstname = beautify_string(person.firstname)
    person.alias = beautify_string(person.alias)

def parse_authorities(person: Person, authorities: List[dict]) -> None:
    for authority in authorities:
        authority_type = authority['B_LINKTXT']
        authority_url = authority['B_URL']
        if authority_type == AUTHORITIES['VIAF']:
            id = authority_url.split('/')[-2]
            person.viaf = id
        if authority_type == AUTHORITIES['WIKIDATA']:
            person.wikidata = get_wikidata_id(authority_url)
        if authority_type.strip() == AUTHORITIES['BELELITE']:
            id = authority_url.split('/')[-1]
            person.belelite = id
        if authority_type.strip() == AUTHORITIES['DBNL']:
            person.dbnl = get_dbnl_id(authority_url)

# main
if __name__ == "__main__":

    persons = []

    with open(file, "r", encoding='utf-8') as json_file:
        data = json.load(json_file)
        for agent in data:
            person = get_person_data(agent)
            persons.append(person)

    with open('authorities_KADOC.csv', 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        header = ['ODIS ID', 'volledige naam', 'voornaam', 'achternaam', 'alias', 'geboorteplaats', 'geboortedatum', 'sterfplaats', 
                    'sterfdatum', 'Geslacht', 'DBNL ID', 'Wikidata ID', 'VIAF ID', 'Belelite', 'foto ID']
        writer.writerow(header)
        for person in persons:
            writer.writerow(person.print_kadoc_properties())
