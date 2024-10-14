"""Module for parsing the XML-files of Letterenhuis and convert the data to the VNA CSV-format"""

import xml.etree.ElementTree as ET
import os
from pathlib import Path
from sys import path
from dotenv import load_dotenv

# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, Alias, write_csv

load_dotenv()

# constans
FOLDER = os.getenv('LETTERENHUIS_FOLDER')
XML_TAG_NAMES = {
    'FIRST_NAME': 'RestOfName',
    'LAST_NAME': 'PrimaryName',
    'SUFFIX': 'Suffix',
    'DEATH_PLACE': 'place_of_death',
    'BIRTH_PLACE': 'place_of_birth'
}

# variables
persons = []

# methods
def set_names(person: Person, root: ET.Element) -> None:
    """
    Parses a person's name data in the Letterenhuis XML and stores the 
    data in a person object

        Parameters:
        person (Person): A person object
        root (Element): The root element of an XML file
    """
    for name in root.findall('Names'):
        if name.find('Qualifier').text is None:
            person.name.first = name.find(XML_TAG_NAMES['FIRST_NAME']).text
            person.name.last = name.find(XML_TAG_NAMES['LAST_NAME']).text
            suffix = name.find(XML_TAG_NAMES['SUFFIX']).text
            if suffix:
                person.name.first += f" {suffix}"

        else:
            alias = Alias()
            firstname = name.find(XML_TAG_NAMES['FIRST_NAME']).text
            lastname = name.find(XML_TAG_NAMES['LAST_NAME']).text
            suffix = name.find(XML_TAG_NAMES['SUFFIX']).text
            if firstname:
                alias.first = firstname
            if suffix:
                alias.first += f" {suffix}"
            if lastname:
                alias.last = lastname
            person.name.alias += f"{alias.get_alias()},".strip()

    if person.name.alias.endswith(','):
        person.name.alias = person.name.alias[:-1]
        
def set_dates(person: Person, root: ET.Element) -> None:
    """
    Parses a person's date of existence data in the Letterenhuis XML and stores the 
    data in a person object

        Parameters:
        person (Person): A person object
        root (Element): The root element of an XML file
    """
    dates = root.find('DatesOfExistence')
    if dates:
        structured_dates = dates.find('StructuredDateRange')
        single_date = dates.find('StructuredDateSingle')
        if structured_dates:
            deathdate = structured_dates.find('EndDateStandardized').text
            birthdate = structured_dates.find('BeginDateStandardized').text
            if birthdate:
                person.birth.date = birthdate
            if deathdate:
                person.death.date = deathdate
        elif single_date:
            date = single_date.find('DateStandardized').text
            match single_date.find('DateRole').text:
                case 'begin':
                    person.birth.date = date
                case 'end':
                    person.death.date = date

def set_user_places(person: Person, root: ET.Element) -> None:
    """
    Parses a person's place data in the Letterenhuis XML and stores the 
    data in a person object

        Parameters:
        person (Person): A person object
        root (Element): The root element of an XML file
    """
    places = root.findall('AgentPlaces')
    for place in places:
        place_type = place.find('PlaceRole').text
        if place_type == XML_TAG_NAMES['DEATH_PLACE']:
            person.death.place = place.find('Subjects').find('Ref').text
        if place_type == XML_TAG_NAMES['BIRTH_PLACE']:
            person.birth.place = place.find('Subjects').find('Ref').text

def set_occupation(person: Person, root: ET.Element) -> None:
    """
    Parses a person's occupation data in the Letterenhuis XML and stores the 
    data in a person object

        Parameters:
        person (Person): A person object
        root (Element): The root element of an XML file
    """
    occupations = root.findall('AgentOccupations')
    if occupations:
        for occupation in occupations:
            occupation_note = occupation.find('Notes').find('Content').find('String').text
            person.occupation += f"{occupation_note},".strip()

    if person.occupation.endswith(','):
        person.occupation = person.occupation[:-1]

    person.occupation = person.occupation.replace("\\r\\n", ",")

def find_id(value: str) -> str:
    """Returns the extenal identifier in a string"""
    if '?' in value:
        return value.split('=')[-1]
    return value.split('/')[-1]

def set_external_identifiers(person: Person, root: ET.Element) -> None:
    """
    Parses a person's external identifiers data in the Letterenhuis XML and stores the 
    data in a person object

        Parameters:
        person (Person): A person object
        root (Element): The root element of an XML file
    """
    docs = root.findall('ExternalDocuments')
    for doc in docs:
        doc_type = doc.find('Title').text
        doc_value = doc.find('Location').text
        if 'dams.antwerpen.be' in doc_type:
            person.picture = doc_value
        else:
            identifier = find_id(doc_value)
            match doc_type:
                case 'dbnl':
                    person.identifier.dbnl = identifier
                case 'odis':
                    person.identifier.odis = identifier
                case 'wikidata':
                    person.identifier.wikidata = identifier
                case 'viaf':
                    person.identifier.viaf = identifier
                case 'rkd':
                    person.identifier.rkd = identifier

def parse_xml(file: str) -> Person:
    """
    Return all data of a person found in a Letterenhuis XML file.

        Parameters:
            file (str): the filepath of the XML file

        Returns:
            person (Person): a person object
    """
    tree = ET.parse(file)
    root = tree.getroot()
    jsonmodel = root.find('JsonmodelType').text

    if  jsonmodel == 'agent_person':
        person = Person()
        # firstname, lastname & aliases
        set_names(person, root)
        # geboorte- en sterfdatum
        set_dates(person, root)     
        #geboorte- en sterfplaats
        set_user_places(person, root)   
        #beroep
        set_occupation(person, root)
        # URI
        person.uri = root.find('URI').text
        # afbeeldingen en externe identifiers
        set_external_identifiers(person, root)

# main
if __name__ == "__main__":

    for filename in os.listdir(FOLDER):
        print(filename)
        file_path = os.path.join(FOLDER, filename)
        if file_path.endswith('.xml'):
            persons.append(parse_xml(file_path))

    write_csv('authorities_letterenhuis.csv', persons)
