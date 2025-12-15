"""Parse Archief voor Vrouwengeschiedenis (AVG-Carhif) XML in EAC-CPF format and 
export selected fields to a VNA CSV.

For each <eac-cpf> record, extracts:
  - name: from ./cpfDescription/identity/nameEntry ("Last, First")
  - alias: from ./cpfDescription/identity/nameEntryParallel (optional)
  - birth/death dates: from ./cpfDescription/description/existDates/dateRange,
    expecting French month names; outputs ISO (YYYY-MM-DD)
  - picture IDs: from ./cpfDescription/relations/resourceRelation @id_carhif

Results are mapped to `Person` objects from `scripts.person` and written
to CSV with `write_csv(OUTPUT, persons)`.
"""


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

def split_date(person: Person, date: str) -> None:
    """Split a 'birth - death' string and populate `person.birth/death.date`.

    Expects a hyphen-delimited string where each side is a full date
    written in French (e.g., '1 janvier 1900 - 2 février 1980'). Empty/missing
    sides are allowed.

    Args:
        person: Target person instance to mutate.
        date: Raw date range string from the XML node.

    Side Effects:
        - Mutates `person.birth.date` and, if present, `person.death.date`,
          converting through `format_date` to ISO 'YYYY-MM-DD'.
    """

    dates = date.split('-')
    birthdate = dates[0].strip()
    person.birth.date = format_date(birthdate)

    if len(dates) > 1:
        deathdate = dates[1].strip()
        person.death.date = format_date(deathdate)

def format_date(date) -> str:
    """Parse a French date string and return an ISO 'YYYY-MM-DD' string.

    The function sets the process locale to French ('fr_FR') and uses
    `datetime.strptime(date, '%d %B %Y')`.

    Args:
        date: A date like '1 janvier 1900'.

    Returns:
        A string formatted as 'YYYY-MM-DD'.
    """

    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR')
    except locale.Error:
        print("[ERROR] No french locale!")
        print("[ERROR] Can't format date!")
        return date

    try:
        formatted_date = datetime.strptime(date, '%d %B %Y').strftime('%Y-%m-%d')
    except ValueError:
        print("[ERROR] Date not formatted as a french string")
        return date

    return formatted_date

def split_name(name: str) -> list[str]:
    """Return [last, first, ...] by splitting on commas.

    The first item is treated as the last name, the second as the first name;
    additional items (if any) are preserved in the result list.

    Args:
        name: A string like 'Last, First'.

    Returns:
        list[str]: The comma-split tokens (unstripped).
    """
    names = name.split(',')
    return names

def parse_pictures(person: Person, elements: list[ET.Element]) -> None:
    """Collect picture IDs from resourceRelation elements into `person.picture`.

    Reads the `id_carhif` attribute from each element, removes any '/',
    concatenates them with commas, and trims the trailing comma via
    `beautify_string`.

    Args:
        person: Target person instance to mutate.
        elements: List of <resourceRelation> XML elements.

    Side Effects:
        - Mutates `person.picture` to a comma-separated list of IDs.
    """
    for element in elements:
        picture_id = element.get(XML_TAG_NAMES['PICTURE_ID'])
        picture_id = picture_id.replace('/', '')
        person.picture += picture_id + ','
    person.picture = beautify_string(person.picture)


def parse_xml(input_file):
    """Parse the AVG EAC-CPF XML and populate the global `persons` list.

    Steps:
        1) Load the XML and find all `XML_TAG_NAMES['PERSON']` (e.g., 'eac-cpf').
        2) For each record:
           - Parse name from `./cpfDescription/identity/nameEntry` ('Last, First') 
           into `Person.name`.
           - Parse alias from `./cpfDescription/identity/nameEntryParallel` (optional), 
           swapping 'Last, First' → 'First Last'.
           - Parse birth/death dates from `./cpfDescription/description/existDates/dateRange` 
           via `split_date`.
           - Gather picture IDs from nodes matching `./cpfDescription/relations/resourceRelation` 
           via `parse_pictures`.
        3) Append each populated `Person` to the global `persons` list.

    Args:
        input_file: Path to the AVG XML file.

    Side Effects:
        - Reads from disk, populates `persons` (a process-wide list).
    """
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
                person.name.alias = f"{aliases[1].strip()} {aliases[0].strip()}"
            else:
                person.name.alias = aliases[0]
        except(TypeError, ValueError, IndexError) as error:
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
    # Writes the VNA CSV using the shared header/ordering from scripts.person.
    write_csv(OUTPUT, persons)
