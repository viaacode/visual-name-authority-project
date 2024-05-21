import json
from person import Person, beautify_string, get_dbnl_id, get_wikidata_id, write_csv
from typing import List
from sys import argv

JSON_KEY_NAMES = {
    'URI': 'URL',
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
    'DBNL': 'Digitale Bibliotheek voor de Nederlandse Letteren'
}

file = argv[1]
output = argv[2]

def get_person_data(json_data: dict) -> Person:
    person = Person()
    person.uri = "{}".format(json_data[JSON_KEY_NAMES['URI']])
    person.odis = "{}_{}".format(json_data['RUBRIEK'], json_data['ID'])
    print(person.odis)
    person.fullname = "{}".format(json_data['OMSCHRIJVING'])

    steekkaarten = json_data['STEEKKAART']
    for steekkaart in steekkaarten:
        names = steekkaart['PS_NAMEN']
        parse_names(person, names)            
        
        person.birthdate = steekkaart.get(JSON_KEY_NAMES['BIRTH_DATE'], '')
        person.deathdate = steekkaart.get(JSON_KEY_NAMES['DEATH_DATE'], '')
        person.place_of_birth = steekkaart.get(JSON_KEY_NAMES['BIRTH_PLACE'], '')
        person.place_of_death = steekkaart.get(JSON_KEY_NAMES['DEATH_PLACE'], '')
        
        sex = steekkaart.get(JSON_KEY_NAMES['SEX'], '')
        set_sex(person, sex)
        
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
        naam = name['NAAM']
        if naam:
            naam = naam.rstrip()
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
        if authority_type:
            if authority_type == AUTHORITIES['VIAF']:
                id = authority_url.split('/')[-2]
                person.viaf = id
            if authority_type == AUTHORITIES['WIKIDATA']:
                person.wikidata = get_wikidata_id(authority_url)
            if authority_type.strip() == AUTHORITIES['DBNL']:
                person.dbnl = get_dbnl_id(authority_url)

def set_sex(person: Person, sex: str) -> None:
    if sex == 'man':
        person.sex = 'mannelijk'
    if sex == 'vrouw':
        person.sex = 'vrouwelijk'

# main
if __name__ == "__main__":

    persons = []

    with open(file, "r", encoding='utf-8') as json_file:
        data = json.load(json_file)
        for agent in data:
            person = get_person_data(agent)
            persons.append(person)
    
    write_csv(output, persons)

    
