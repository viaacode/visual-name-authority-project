import xml.etree.ElementTree as ET
import os
import csv

# constans
FOLDER = '../lh-archiefvormers-export'
XML_TAG_NAMES = {
    'FIRST_NAME': 'RestOfName',
    'LAST_NAME': 'PrimaryName',
    'SUFFIX': 'Suffix',
    'DEATH_PLACE': 'place_of_death',
    'BIRTH_PLACE': 'place_of_birth'
}

# classes
class Person:
    def __init__(self) -> None:
        self.uri = ''
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

    def print_properties(self):
        return [self.uri, self.firstname, self.lastname, self.alias, self.place_of_birth, self.birthdate, 
                self.place_of_death, self.deathdate, self.occupation, self.dbnl, self.odis, self.wikidata, 
                self.viaf, self.rkd, self.picture]

class Alias:
    def __init__(self) -> None:
        self.first = ''
        self.last = ''

# methods
def set_names(person, root) -> None:
    for name in root.findall('Names'):
        if name.find('Qualifier').text is None:
            person.firstname = name.find(XML_TAG_NAMES['FIRST_NAME']).text
            person.lastname = name.find(XML_TAG_NAMES['LAST_NAME']).text
            suffix = name.find(XML_TAG_NAMES['SUFFIX']).text
            if suffix:
                person.firstname += " {}".format(suffix)

        else:
            alias = Alias()
            firstname = name.find(XML_TAG_NAMES['FIRST_NAME']).text
            lastname = name.find(XML_TAG_NAMES['LAST_NAME']).text
            suffix = name.find(XML_TAG_NAMES['SUFFIX']).text
            if firstname:
                alias.first = firstname
            if suffix:
                alias.first += " {}".format(suffix)
            if lastname:
                alias.last = lastname    
            person.alias += "{} {},".format(alias.first, alias.last).strip()
        
    if person.alias.endswith(','):
        person.alias = person.alias[:-1]
        
def set_dates(person, root) -> None:
    dates = root.find('DatesOfExistence')
    if dates:
        structured_dates = dates.find('StructuredDateRange')
        single_date = dates.find('StructuredDateSingle')
        if structured_dates:
            deathdate = structured_dates.find('EndDateStandardized').text
            birthdate = structured_dates.find('BeginDateStandardized').text
            if birthdate:
                person.birthdate = birthdate
            if deathdate:
                person.deathdate = deathdate
        elif single_date:
            date = single_date.find('DateStandardized').text
            match single_date.find('DateRole').text:
                case 'begin':
                    person.birthdate = date
                case 'end':
                    person.deathdate = date

def set_user_places(person, root) -> None:
    places = root.findall('AgentPlaces')
    for place in places:
        type = place.find('PlaceRole').text
        if type == XML_TAG_NAMES['DEATH_PLACE']:
            person.place_of_death = place.find('Subjects').find('Ref').text
        if type == XML_TAG_NAMES['BIRTH_PLACE']:
            person.place_of_birth = place.find('Subjects').find('Ref').text

def set_occupation(person, root) -> None:
    occupations = root.findall('AgentOccupations')
    if occupations:
        for occupation in occupations:
            occupation_note = occupation.find('Notes').find('Content').find('String').text
            person.occupation += "{},".format(occupation_note).strip()          

    if person.occupation.endswith(','):
        person.occupation = person.occupation[:-1]

    person.occupation = person.occupation.replace("\\r\\n", ",")
    
def find_id(value: str) -> str:
    if '?' in value:
        return value.split('=')[-1]
    else:
        return value.split('/')[-1]

def set_external_identifiers(person, root) -> None:
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
                    person.dbnl = identifier
                case 'odis':
                    person.odis = identifier
                case 'wikidata':
                    person.wikidata = identifier
                case 'viaf':
                    person.viaf = identifier
                case 'rkd':
                    person.rkd = identifier

def parse_xml(file) -> None:
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

        persons.append(person)
  
# main      
if __name__ == "__main__":
    persons = []

    for filename in os.listdir(FOLDER):
        print(filename)
        file_path = os.path.join(FOLDER, filename)
        if file_path.endswith('.xml'):
            parse_xml(file_path)

    with open('authorities_letterenhuis.csv', 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        header = ['URI', 'voornaam', 'achternaam', 'alias', 'geboorteplaats', 'geboortedatum', 'sterfplaats', 
                    'sterfdatum', 'beroep', 'dbnl author ID', 'ODIS ID', 'Wikidata ID', 'VIAF ID', 'RKD ID', 'foto URL']
        writer.writerow(header)
        for person in persons:
            writer.writerow(person.print_properties())
