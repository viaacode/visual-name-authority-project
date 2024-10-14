"""Module for parsing the XML-file of Archief voor Vrouwengeschiedenis (AVG) and 
converting the data to the VNA CSV-format"""


import xml.etree.ElementTree as ET
import locale
from datetime import datetime
from sys import path, argv
from pathlib import Path

# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, beautify_string, write_csv

FILE = argv[1]
OUTPUT = argv[2]

# constants
XML_TAG_NAMES = {
    'PERSON': 'eac-cpf',
    'FULLNAME': './cpfDescription/identity/nameEntry',
    'ALIAS' : './cpfDescription/identity/nameEntryParallel',
    'DATE': './cpfDescription/description/existDates/dateRange',
    'PICTURE_TAG': './cpfDescription/relations/resourceRelation',
    'PICTURE_ID': 'id_carhif'
    }

persons = []

def split_date(person: Person, date: str):
    dates = date.split('-')
    birthdate = dates[0].strip()
    person.birth.date = format_date(birthdate)


    if len(dates) > 1:
        deathdate = dates[1].strip()
        person.death.date = format_date(deathdate)

def format_date(date):
    locale.setlocale(locale.LC_ALL, 'fr_FR')
    return datetime.strptime(date, '%d %B %Y').strftime('%Y-%m-%d')

def split_name(name: str):
    names = name.split(',')
    return names

def parse_pictures(person: Person, elements: list[ET.Element]):
    for element in elements:
        picture_id = element.get(XML_TAG_NAMES['PICTURE_ID'])
        picture_id = picture_id.replace('/', '')
        person.picture += picture_id + ','
    person.picture = beautify_string(person.picture)


def parse_xml(input_file):
    tree = ET.parse(input_file)
    root = tree.getroot()
    xml_persons = root.findall(XML_TAG_NAMES['PERSON'])

    for xml_person in xml_persons:
        person = Person()

        #fullname, firstname, lastname
        names = split_name(xml_person.find(XML_TAG_NAMES['FULLNAME']).text)
        person.name.first = names[1].strip()
        person.name.last = names[0].strip()
        person.name.full = f'{person.name.first} {person.name.last}'

        #alias
        alias = xml_person.find(XML_TAG_NAMES['ALIAS'])
        try:
            aliases = split_name(alias.text)
            if len(aliases) > 1:
                person.alias = "{} {}".format(aliases[1].strip(), aliases[0].strip())
            else:
                person.alias = aliases[0]
        except Exception as error:
            print(f"{person.name.full} has no alias")
            print(error)

        #birth & death date
        split_date(person, xml_person.find(XML_TAG_NAMES['DATE']).text)

        #pictures
        pictures = xml_person.findall(XML_TAG_NAMES['PICTURE_TAG'])
        parse_pictures(person,pictures)
        persons.append(person)


if __name__ == '__main__':
    parse_xml(FILE)
    write_csv(OUTPUT, persons)
