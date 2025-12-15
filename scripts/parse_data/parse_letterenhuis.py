"""Parse Letterenhuis XML authority records and export to VNA CSV.

For each XML file in the folder specified by the `LETTERENHUIS_FOLDER`
environment variable, extract name (main and aliases), dates of existence,
places of birth/death, occupation notes, external identifiers, and an
optional picture URL. Map values onto `scripts.person.Person` and write a
VNA-formatted CSV via `write_csv`.
"""

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
    """Populate main name and aliases from the <Names> group.

    Behavior:
        - A <Names> element WITHOUT <Qualifier> is treated as the main name:
          * First name: RestOfName
          * Last name:  PrimaryName
          * Suffix (if present) is appended to the first name with a space.
        - A <Names> element WITH <Qualifier> is treated as an alias and
          contributes "First [Suffix] Last" to `person.name.alias` as a
          comma-separated list.

    Args:
        person: Target Person instance to mutate.
        root:   Parsed XML root element of a single record.

    Side Effects:
        - Mutates `person.name.first`, `person.name.last`, and
          `person.name.alias` (comma-separated).
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
    """Populate birth and death dates from <DatesOfExistence>.

    Behavior:
        - Prefer StructuredDateRange:
            BeginDateStandardized → person.birth.date
            EndDateStandardized   → person.death.date
        - Else, use StructuredDateSingle with DateRole 'begin' or 'end'.

    Args:
        person: Target Person instance to mutate.
        root:   Parsed XML root element of a single record.

    Side Effects:
        - Mutates `person.birth.date` and/or `person.death.date` when present.
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
    """Populate birth and death places from <AgentPlaces>.

    Behavior:
        - For each <AgentPlaces>, read <PlaceRole>:
            'place_of_birth' → person.birth.place
            'place_of_death' → person.death.place
        - Place label is read from <Subjects>/<Ref>.

    Args:
        person: Target Person instance to mutate.
        root:   Parsed XML root element of a single record.

    Side Effects:
        - Mutates `person.birth.place` / `person.death.place` when present.
    """
    places = root.findall('AgentPlaces')
    for place in places:
        place_type = place.find('PlaceRole').text
        if place_type == XML_TAG_NAMES['DEATH_PLACE']:
            person.death.place = place.find('Subjects').find('Ref').text
        if place_type == XML_TAG_NAMES['BIRTH_PLACE']:
            person.birth.place = place.find('Subjects').find('Ref').text

def set_occupation(person: Person, root: ET.Element) -> None:
    """Aggregate occupation notes into a single comma-separated string.

    Behavior:
        - For each <AgentOccupations>, read Notes/Content/String and append
          to `person.occupation`, separated by commas.
        - Remove a trailing comma if present.
        - Replace literal '\\r\\n' with commas.

    Args:
        person: Target Person instance to mutate.
        root:   Parsed XML root element of a single record.

    Side Effects:
        - Mutates `person.occupation`.
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
    """Return an external identifier parsed from a URL-like string.

    If the value contains '?', the identifier is the substring after the
    last '='. Otherwise it is the substring after the last '/'.

    Args:
        value: URL or URL-like string.

    Returns:
        The extracted identifier string.
    """

    if '?' in value:
        return value.split('=')[-1]
    return value.split('/')[-1]

def set_external_identifiers(person: Person, root: ET.Element) -> None:
    """Populate picture URL and external IDs from <ExternalDocuments>.

    Behavior:
        - If Title contains 'dams.antwerpen.be', treat Location as a picture
          URL and assign to `person.picture`.
        - Else map Title to one of {dbnl, odis, wikidata, viaf, rkd} and
          extract an identifier from Location using `find_id`.

    Args:
        person: Target Person instance to mutate.
        root:   Parsed XML root element of a single record.

    Side Effects:
        - Mutates `person.picture` and fields on `person.identifier`.
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
    """Parse one Letterenhuis XML file into a Person (if agent_person).

    Steps:
        1) Parse XML and check <JsonmodelType>. Only 'agent_person' is handled.
        2) Call:
            - set_names
            - set_dates
            - set_user_places
            - set_occupation
            - set_external_identifiers
        3) Assign the record URI (root/<URI>) to the Person instance.

    Args:
        file: Filesystem path to a single XML file.

    Returns:
        A Person instance populated from the file if `agent_person`;
        otherwise None (implicit) if the type does not match.
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
        person.identifier.uri = root.find('URI').text
        # afbeeldingen en externe identifiers
        set_external_identifiers(person, root)

# main
if __name__ == "__main__":
    # Processes all .xml files in LETTERENHUIS_FOLDER and writes a VNA CSV.
    for filename in os.listdir(FOLDER):
        print(filename)
        file_path = os.path.join(FOLDER, filename)
        if file_path.endswith('.xml'):
            persons.append(parse_xml(file_path))

    write_csv('authorities_letterenhuis.csv', persons)
