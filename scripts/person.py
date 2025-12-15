"""Data model and CSV export helpers for Visual Name Authority (VNA).

Defines light dataclasses to represent a person (name, birth/death events,
identifiers, etc.), plus a CSV writer that emits rows in the standard VNA
column order. Also includes small helpers to extract common external IDs
(Wikidata, DBNL, VIAF) from their canonical URLs.
"""

from typing import List
from csv import writer
from dataclasses import dataclass, field


# ----------------------------------------------
# Dataclasses
# ----------------------------------------------

@dataclass
class Name():

    """
    Class for personal name fields.

    Attributes:
        first (str): Given name(s).
        last (str): Family name(s).
        full (str): Full display name (often "{first} {last}", but not enforced).
        alias (str): Alternate/other name label to export (free text).
    """

    first: str = ""
    last: str = ""
    full: str = ""
    alias: str = ""

@dataclass
class Alias:
    """Structured representation of an alternate name.

    Attributes:
        first: Given name(s) of the alias.
        last: Family name(s) of the alias.
    """
    first: str = ""
    last: str = ""

    def get_alias(self) -> str:
        """Return the alias as a single string: 'first last'."""
        return self.first + " " + self.last

@dataclass
class Event:
    """Place/date pair for a life event (e.g., birth or death).

    Attributes:
        place: Human-readable place name.
        date: Event date in ISO format (YYYY-MM-DD) or free text if unknown.
    """
    place: str = ""
    date: str = ""

@dataclass
class Identifier:
    """External identifiers commonly used in VNA.

    Attributes:
        uri: Canonical URI for the person in this dataset.
        wikidata: Wikidata QID (e.g., 'Q42').
        odis: ODIS identifier.
        rkd: RKDartists ID (string).
        dbnl: DBNL author identifier.
        viaf: VIAF identifier.
        isni: ISNI identifier.
    """
    uri: str = ""
    wikidata: str = ""
    odis: str = ""
    rkd: str = ""
    dbnl: str = ""
    viaf: str = ""
    isni: str = ""


@dataclass
class Person:
    """Aggregate representation of a person used for VNA export.

    Attributes:
        id: Local/system identifier for the person (string).
        name: Name fields (first/last/full/alias).
        birth: Birth event (place/date).
        death: Death event (place/date).
        occupation: Occupation(s) or role(s) as free text.
        picture: Comma-separated list of picture filenames or URIs.
        identifier: External identifiers (URI, Wikidata, VIAF, etc.).
    """
    id: str = ""
    name: Name = field(default_factory=Name)
    birth: Event = field(default_factory=Event)
    death: Event = field(default_factory=Event)
    occupation: str = ""
    picture: str = ""
    identifier: Identifier = field(default_factory=Identifier)

    def print_properties(self) -> List[str]:
        """Return the person's fields in the standard VNA column order.

        Order:
            [URI, ID, volledige naam, voornaam, achternaam, alias,
             geboorteplaats, geboortedatum, sterfplaats, sterfdatum,
             beroep, DBNL ID, ODIS ID, Wikidata ID, VIAF ID, RKD ID,
             ISNI ID, foto]

        Returns:
            A list of strings ready to be written as a CSV row.
        """
        return [self.identifier.uri, self.id, self.name.full, self.name.first,
                self.name.last, self.name.alias, self.birth.place, self.birth.date,
                self.death.place, self.death.date, self.occupation, self.identifier.dbnl,
                self.identifier.odis, self.identifier.wikidata, self.identifier.viaf,
                self.identifier.rkd, self.identifier.isni, self.picture]


# ----------------------------------------------
# ID extractors
# ----------------------------------------------

def get_wikidata_id(url: str) -> str:
    """Extract the Wikidata QID from a Wikidata URL.

    Example:
        'https://www.wikidata.org/wiki/Q42' -> 'Q42'

    Args:
        url: A Wikidata entity URL.

    Returns:
        The last path segment (e.g., 'Q42').
    """
    identifier = url.split("/")[-1]
    return identifier


def get_dbnl_id(url: str) -> str:
    """Extract the DBNL ID from a DBNL URL or query string.

    Example:
        'https://www.dbnl.org/auteurs/auteur.php?id=mult002' -> 'mult002'

    Args:
        url: A DBNL URL containing an 'id=' parameter.

    Returns:
        The substring after the last '=' character.
    """
    identifier = url.split("=")[-1]
    return identifier


def get_viaf_id(url: str) -> str:
    """Extract the VIAF numeric ID from a VIAF URL.

    Example:
        'https://viaf.org/viaf/44300636/' -> '44300636'

    Args:
        url: A VIAF URL.

    Returns:
        The last path segment if it consists only of digits; otherwise an
        empty string.
    """
    identifier = url.split("/")[-1].strip()
    if identifier.isdigit():
        return identifier
    return ""


# ----------------------------------------------
# String cleanup
# ----------------------------------------------

def beautify_string(value: str) -> str:
    """Trim whitespace and remove a single trailing comma.

    Args:
        value: Input string.

    Returns:
        The cleaned string (leading/trailing spaces removed; if the string
        ends with ',', that comma is dropped).
    """
    value = value.strip()
    if value.endswith(","):
        value = value[:-1]
    return value


# ----------------------------------------------
# CSV writer
# ----------------------------------------------

def write_csv(filename: str, persons: List[Person]):
    """Write a list of Person objects as a VNA-formatted CSV.

    The header and column order match `Person.print_properties()`.

    Args:
        filename: Output CSV path.
        persons: Iterable of Person instances to write.

    Returns:
        None. The file is written with UTF-8 encoding and newline='' to avoid
        extra blank lines on Windows.
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
