"""Module for parsing person data for Visual Name Authority"""

from typing import List
from csv import writer
from dataclasses import dataclass, field

@dataclass
class Name():

    """
    Class for storing all kinds of names of a person.

    Attributes:
        first (str): First name of a person.
        last (str): Last name of a person.
        full (str): Full name of a person. Is mostly a combination of the first and last name
        alias (str): Identifier from RKD.
    """

    first: str = ""
    last: str = ""
    full: str = ""  # mss hier {first} {last} van maken en werken met Name objecten?
    alias: str = "" # misschien hier met een alias object werken?

@dataclass
class Alias:
    """
    Class for storing data of an alias or alternative name(s) of a person.

    Attributes:
        first (str): The first name(s) of the alias.
        last (str): The last name(s) of the alias.
    """
    first: str = ''
    last: str = ''

    def get_alias(self) -> str:
        """Returns the alternative name of a person."""
        return self.first + ' ' + self.last

@dataclass
class Event():

    """
   Class for storing data of an event.

        Attributes:
            place (str): the place where the event took place
            date (str): the date when the event took place
    """

    place: str = ''
    date: str = ''

@dataclass
class Identifier():

    """
        A class for storing all kinds of identifiers of a person.

        Attributes:
            uri (str): a URI as identifier.
            wikidata (str): Identifier from Wikidata.
            odis (str): Identifier from ODIS.
            rkd (str): Identifier from RKD.
            dbnl (str): Identifier from the Digital Library for Dutch Literature.
            viaf (str): Identifier from VIAF.
            isni (str): Identifier from ISNI
    """

    uri: str = ''
    wikidata: str = ''
    odis: str = ''
    rkd: str = ''
    dbnl: str = ''
    viaf: str = ''
    isni: str = ''

@dataclass
class Person():
    """
    Class representing a person.

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

    id: str = ""
    name: Name = field(default_factory=Name)
    birth: Event = field(default_factory=Event)
    death: Event = field(default_factory=Event)
    occupation: str = ''
    picture: str = ''
    identifier: Identifier = field(default_factory=Identifier)

    def print_properties(self) -> List[str]:
        """
        Returns a list of person properties for general use.

        Returns:
            List[str]: A list containing person properties in a specific order.
        """
        return [self.identifier.uri, self.id, self.name.full, self.name.first,
                self.name.last, self.name.alias, self.birth.place, self.birth.date,
                self.death.place, self.death.date, self.occupation, self.identifier.dbnl,
                self.identifier.odis, self.identifier.wikidata, self.identifier.viaf,
                self.identifier.rkd, self.identifier.isni, self.picture]



def get_wikidata_id(url: str) -> str:
    """
    Extracts the wikidata QID from the Wikidata URI.

    Returns:
        str: the Wikidata QID.
    """
    identifier = url.split('/')[-1]
    return identifier

def get_dbnl_id(url: str) -> str:
    """
    Extracts the DBNL ID from the DBNL URI.

    Returns:
        str: the DBNL ID.
    """
    identifier = url.split('=')[-1]
    return identifier

def get_viaf_id(url: str) -> str:
    """
    Extracts the VIAF ID from the VIAF URI.

    Returns:
        str: the Wikidata QID.
    """
    identifier = url.split('/')[-1].strip()
    if identifier.isdigit():
        return identifier
    return ""

def beautify_string(value: str) -> str:
    """
    Returns a string where leading and trailing whitespaces and commas are removed
    """
    value = value.strip()
    if value.endswith(','):
        value = value[:-1]
    return value

def write_csv(filename, persons: List[Person]):
    """
    Writes all data of a person in a CSV, 
    following the Visual Name Authority CSV fomat.
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = writer(csv_file)
        header = ['URI', 'ID', 'volledige naam', 'voornaam', 'achternaam', 'alias', 
                  'geboorteplaats', 'geboortedatum', 'sterfplaats', 
                    'sterfdatum', 'beroep', 'DBNL ID', 'ODIS ID', 'Wikidata ID', 'VIAF ID', 
                    'RKD ID', 'ISNI ID', 'foto']
        csv_writer.writerow(header)
        for person in persons:
            csv_writer.writerow(person.print_properties())
