"""
Werkwijze:
- gebruik spacy om eerst de titel uit te lezen (response.document.title)
- als het aantal mensen hierna nog 0 is, check dan of er 'Portret van' is en kap de tekst erna af
- sla ook het aantal mensen op, zodat we kunnen corrigeren bij meerdere mensen
- misschien ook nuttig om de licentie mee op te nemen (has_download_license)

wat bewaren:
- id foto
- titel
- namen
- geboortedatum
- sterfdatum
- alias
- is het een portret of groep
- licentie
"""

from dataclasses import dataclass
import json
import os
import re
from sys import argv
import spacy


FOLDER = argv[1]

MODEL = "nl_core_news_lg"
nlp = spacy.load(MODEL)

@dataclass
class Person:
    label: str = ""
    realname: str = ""
    alias: str = ""
    birthdate: str = ""
    deathdate: str = ""
    viaf: str = ""

@dataclass
class Photo:
    id: str = ""
    title: str = ""
    type: str = "PORTRET"
    persons = []
    license: str = ""

def get_person_names(sentence: str) -> list[str]:
    """ 
    method to distillate person name from the title of an image using 
    named entity recognition
    """
    person_names = []
    text = nlp(sentence)
    for entity in text.ents:
        if entity.label_ == "PERSON":
            person_names.append(entity.text)
    if len(person_names) == 0:
        name = photo.title.split("Portret van ")[1]
        if not 'onbekend' in name:
            person_names.append(name)
    #print(f"{sentence}: {person_names}")
    # idee, als er meer dan 1 naam in zit, maak dan een peson 1 en een person 2
    # geef dan de namen door en geef dan de info bij de juiste persoon
    return person_names

def get_viaf(sentence: str) -> str:
    viaf = ""
    parts = sentence.split("(viaf)")
    if len(parts) > 1:
        viaf = re.findall(r"\d+", parts[1])[0]
    #print(f"viaf : {viaf}")
    return viaf

def get_real_name(sentence: str, person: Person):
    if person.label.split(' ')[0] in sentence:
        pseudos = re.split(r'\([a-zA-Z]+\)\S+', sentence)
        pseudo = pseudos[1].split("pseudoniem van")
        if len(pseudo) > 1:
            pseudo = pseudo[1].strip()
            person.alias = person.label
            person.realname = pseudo
    else:
        realname = sentence.split(" (")
        if len(realname) > 1:
            (lastname, firstname) = realname[0].split(', ')
            person.realname = f"{firstname} {lastname}"
            person.label = person.realname

def get_depicted(person_info: str, person: Person) -> Person:
    dates = re.findall(r"\d{4}-\d{4}", person_info)
    if dates:
        (birth, death) = dates[0].split('-')
        person.birthdate = birth
        person.deathdate = death
    person.viaf = get_viaf(person_info)
    get_real_name(person_info, person)
    return person

def get_depicted_persons(persons_lines: list[str], person: Person):
    for sentence in persons_lines:
        #print(sentence)
        if person.label.split(' ')[0] in sentence:
            person = get_depicted(sentence, person)

def get_persons(json_root, title) -> list[Person]:
    names = get_person_names(title)
    persons = []
    extra_persons_info = json_root.get('display_author')
    for name in names:
        person = Person(label=name)
        if extra_persons_info:
            extra_persons_info = [item for item in extra_persons_info if "dpc" in item]
            get_depicted_persons(extra_persons_info, person)
            if person.alias == '':
                person.realname = person.label
        persons.append(person)
    
    depicted_persons = [item for item in extra_persons_info if "dpc" in item]
    if len(depicted_persons) > len(persons):
        alias = persons[0].label
        print(f"NAKIJKEN, personen: {len(persons)}, extra info: {len(extra_persons_info)}")
        for depicted_person in depicted_persons:
            person = Person(label=alias, alias=alias)
            persons.append(get_depicted(depicted_person, person))
        persons.pop(0)
    
    for person in persons:
        print(f"person: {person.realname} born with alias {person.alias} in {person.birthdate} with viaf {person.viaf}")
    
    return persons

for json_file in os.listdir(FOLDER)[:30]:
    photo = Photo()
    with open(f"{FOLDER}/{json_file}", 'r', encoding="utf-8", ) as datafile:
        data = json.load(datafile)
        document = data['response']['document']
        photo.id = document.get('id', '')
        photo.title = document.get('title','')
        photo.license = document.get('has_download_license', '')
        photo.persons = get_persons(document, photo.title)
        if len(photo.persons) > 1:
            photo.type = "GROEP"
        #if person_names:
            #get_depicted(person_names)
        print(f"photo: {photo.id}, {photo.type}, {photo.title}, {photo.license}")
