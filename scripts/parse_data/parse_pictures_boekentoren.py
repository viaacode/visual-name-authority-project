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

import csv
from dataclasses import dataclass
import json
import os
import re
from sys import argv
import spacy


FOLDER = argv[1]
download_image = True

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
    status: str = ""

@dataclass
class Photo:
    id: str = ""
    title: str = ""
    type: str = "PORTRET"
    persons = [Person]
    license: str = ""
    image: str = ""

    def print_properties(self) -> list[list[str]]:

        lines = []

        for person in self.persons:
            line = [self.id, self.title, self.type, person.realname, person.alias, person.birthdate, person.deathdate, person.viaf, self.license, self.image, person.status]
            lines.append(line)
        
        return lines



def get_person_names(sentence: str) -> list[str]:
    """ 
    method to distillate person name from the title of an image using 
    named entity recognition
    """
    #print(sentence)
    person_names = []
    text = nlp(sentence)
    for entity in text.ents:
        if entity.label_ == "PERSON":
            person_names.append(entity.text)
    if len(person_names) == 0:
        if 'portret van' in sentence.lower():
            name = photo.title.split("Portret van ")[1]
            if not 'onbekend' in name:
                person_names.append(name)
        else:
            person_names.append('FOUT!!')
            global download_image
            download_image = False

    return person_names

def get_viaf(sentence: str) -> str:
    viaf = ""
    parts = sentence.split("(viaf)")
    if len(parts) > 1:
        viaf = re.findall(r"\d+", parts[1])[0]
    #print(f"viaf : {viaf}")
    return viaf

def get_real_name(sentence: str, person: Person):
    #print("sentence : " + sentence)
    #print("label : " + person.label)
    #if person.label.split(' ')[0] in sentence:
    if 'pseudoniem' in sentence:
        #print(person.label.split(' ')[0])
        pseudos = sentence.split("pseudoniem van")
        #pseudos = re.split(r'\([a-zA-Z]+\)\S+', sentence)
        #print("pseudos")
        #print(pseudos)
        pseudo = pseudos[1].split("(role)dpc")
        #print(pseudo)
        if len(pseudo) > 1:
            pseudo = pseudo[0].strip()
            person.alias = person.label
            person.realname = pseudo
        else:
            person.stats = "NAKIJKEN!!"
    else:
        realname = sentence.split(" (")
        person.realname = realname
        #print(realname)
        if len(realname) > 1:
            names = realname[0].split(', ')
            #print(names)
            lastname = names[0]
            if len(names) == 2:
                firstname = names[1]
            else:
                firstname = ''
                for i in range(1,len(names)-1):
                    firstname += names[i] + ' '
            person.realname = f"{firstname.strip()} {lastname.strip()}"
            #print(person.realname)
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
        if person.label.split(' ')[0] in sentence:
            person = get_depicted(sentence, person)

def get_persons(json_root, title) -> list[Person]:
    names = get_person_names(title)
    #print(names)
    persons = []
    extra_persons_info = json_root.get('display_author')
    #print(extra_persons_info)
    for name in names:
        person = Person(label=name)
        if extra_persons_info:
            extra_persons_info = [item for item in extra_persons_info if "dpc" in item]
            get_depicted_persons(extra_persons_info, person)
            if person.alias == '':
                person.realname = person.label
        persons.append(person)

    if extra_persons_info:
        depicted_persons = [item for item in extra_persons_info if "dpc" in item]
        if len(depicted_persons) != len(persons):
            alias = persons[0].label
            print(f"NAKIJKEN, personen: {len(persons)}, extra info: {len(extra_persons_info)}")
            persons.clear()
            for depicted_person in depicted_persons:
                person = Person(label=alias, alias=alias, status = "NAKIJKEN!!")
                person = get_depicted(depicted_person, person)
                persons.append(person)
            
    
    #for person in persons:
        #print(f"person: {person.realname} born with alias {person.alias} in {person.birthdate} with viaf {person.viaf}")
    
    return persons

def get_image(url: str) -> str:
    url_words = url.split('/')
    iiif_part = '/full/full/0/default.jpg'
    photo_url = '/'.join(url_words[0:6]) + iiif_part
    return photo_url


photos = []

for json_file in os.listdir(FOLDER):
    photo = Photo()
    if os.path.isfile(os.path.join(FOLDER, json_file)):
        with open(f"{FOLDER}/{json_file}", 'r', encoding="utf-8", ) as datafile:
            print(json_file)
            data = json.load(datafile)
            document = data['response']['document']
            photo.id = document.get('id', '')
            photo.title = document.get('title','')
            print(f"{photo.id}: {photo.title}")
            photo.license = document.get('has_download_license', '')
            photo.persons = get_persons(document, photo.title)
            if download_image:
                photo.image = get_image(document.get('thumbnail_url'))
            if len(photo.persons) > 1:
                photo.type = "GROEP"
            #if person_names:
                #get_depicted(person_names)
            photos.append(photo)
            download_image = True

with open('boekentoren.csv', 'w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)    
    for photo in photos:
        for prop in photo.print_properties():
            csv_writer.writerow(prop)
