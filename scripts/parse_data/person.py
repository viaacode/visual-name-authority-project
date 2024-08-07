from typing import List
from csv import writer

class Person:
    """
    Represents a person entity with various attributes.

    Attributes:
        uri (str): The URI for the person.
        id (str): The unique identifier for the person.
        fullname (str): The full name of the person.
        firstname (str): The first name(s) of the person.
        lastname (str): The last name(s) of the person.
        alias (str): Any alias or alternative name(s) of the person.
        birthdate (str): The date of birth of the person.
        deathdate (str): The date of death of the person.
        place_of_birth (str): The place of birth of the person.
        place_of_death (str): The place of death of the person.
        sex (str): The sex of the person.
        occupation (str): The occupation or profession of the person.
        picture (str): Information about the picture of the person.
        dbnl (str): Identifier for the person from the Digital Library for Dutch Literature.
        odis (str): Identifier for the person from ODIS.
        wikidata (str): Identifier for the person from Wikidata.
        viaf (str): Identifier for the person from VIAF.
        rkd (str): Identifier for the person from RKD.
        isni (str): Identifier for the person from ISNI
    """

    def __init__(self) -> None:
        self.uri = ''
        self.id = ''
        self.fullname = ''
        self.firstname = ''
        self.lastname = ''
        self.alias = ''
        self.birthdate = ''
        self.deathdate = ''
        self.place_of_birth = ''
        self.place_of_death = ''
        self.occupation = ''
        self.picture = ''
        self.dbnl = ''
        self.odis = ''
        self.wikidata = ''
        self.viaf = ''
        self.rkd = ''
        self.isni = ''

    def print_properties(self) -> List[str]:        
        """
        Returns a list of person properties for general use.

        Returns:
            List[str]: A list containing person properties in a specific order.
        """
        return [self.uri, self.id, self.fullname, self.firstname, self.lastname, self.alias, self.place_of_birth, self.birthdate, 
                self.place_of_death, self.deathdate, self.occupation, self.dbnl, self.odis, self.wikidata, 
                self.viaf, self.rkd, self.isni, self.picture]

class Alias:
    """
    Represents an alias or alternative name(s) of a person.

    Attributes:
        first (str): The first name(s) of the alias.
        last (str): The last name(s) of the alias.
    """
    def __init__(self) -> None:
        self.first = ''
        self.last = ''

def get_wikidata_id(url: str) -> str:
    """
        Extracts the wikidata QID from the Wikidata URI.

        Returns:
            str: the Wikidata QID.
        """
    id = url.split('/')[-1]
    return id

def get_dbnl_id(url: str) -> str:
    """
        Extracts the DBNL ID from the DBNL URI.

        Returns:
            str: the DBNL ID.
    """
    id = url.split('=')[-1]
    return id

def get_viaf_id(url: str) -> str:
    """
        Extracts the VIAF ID from the VIAF URI.

        Returns:
            str: the Wikidata QID.
        """
    id = url.split('/')[-1].strip()
    if id.isdigit():
        return id
    else:
        return ""

def beautify_string(value: str) -> str:
    value = value.strip()
    if value.endswith(','):
        value = value[:-1]
    return value

def write_csv(filename, persons: List[Person]):
     with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = writer(csv_file)
        header = ['URI', 'ID', 'volledige naam', 'voornaam', 'achternaam', 'alias', 
                  'geboorteplaats', 'geboortedatum', 'sterfplaats', 
                    'sterfdatum', 'beroep', 'DBNL ID', 'ODIS ID', 'Wikidata ID', 'VIAF ID', 
                    'RKD ID', 'ISNI ID', 'foto']
        csv_writer.writerow(header)
        for person in persons:
            csv_writer.writerow(person.print_properties())