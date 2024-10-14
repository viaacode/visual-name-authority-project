"""Module for crawling data of https://www.svm.be/componisten and converting it to 
the VNA CSV-format"""

from datetime import datetime
from pathlib import Path
import os
from sys import path, argv
from time import sleep
from bs4 import BeautifulSoup, ResultSet
from requests import Session


# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, Event, write_csv, beautify_string

# constants
TEXTFILE = argv[1]
ROOT_FOLDER = str(Path(os.path.abspath(TEXTFILE)).parent.absolute())
OUTPUT = argv[2]
PHOTO_FOLDER = 'foto'
ERROR_MESSAGE = 'FOUT!'

#variables
persons = []

"""
"""
def get_life_events(text: str, person: Person): 
    life_events = text.split(' — ')
    life_events = [event.strip() for event in life_events]
    if len(life_events) > 0 and len(life_events[0]) > 2:
        birth_event = split_date_place(life_events[0])
        person.birth.date = birth_event.date
        person.birth.place = birth_event.place
    if len(life_events) > 1 and len(life_events[1]) > 2:
        death_event = split_date_place(life_events[1])
        person.death.date = death_event.date
        person.death.place = death_event.place

def split_date_place(text: str) -> Event:
    data = text.split(',')
    if len(data) > 0:
        place = data[0][2:]
        if len(data) > 1:
            date = datetime.strptime(data[-1].strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
            if len(data) > 2:
                for item in data[1:-1]:
                    place += ',' + item
        else:
            print("[ERROR] No date or place")
            date = ERROR_MESSAGE
        return Event(place, date)
    return Event()


def download_images(tags: ResultSet, directory: str, person: Person, session: Session):
    for tag in tags:
        url = tag['href']
        filename = url.split('/')[-1]
        output_file = "{}/{}".format(directory, filename)
        if not os.path.exists(output_file):
            print(f"[INFO] downloading image {url}")
            image = session.get(url).content
            with open(output_file, 'wb') as handler:
                handler.write(image)
        person.picture += filename + ','


def get_images(html: BeautifulSoup, person: Person, session: Session):
    tags = html.find_all("a", class_="js-modal-image")
    if tags:
        identifier = person.identifier.uri.split('/')[-1]
        folder = f"{ROOT_FOLDER}/{PHOTO_FOLDER}/{identifier}"
        if not os.path.exists(folder):
            os.makedirs(folder)
        download_images(tags, folder, person, session)
        person.picture = beautify_string(person.picture)
    else:
        print(f"[INFO] {person.name.first} {person.name.last} has no images")


def split_names(value: str, person: Person) -> str:
    names = value.split(',')
    if len(names) > 1:
        person.name.first = names[1].strip()
        person.name.last = names[0].strip()

        if len(names) > 2:
            for name in names[2:]:
                person.name.first += name
    else:
        person.name.full = value

def create_svm_person(html: BeautifulSoup, person: Person, session: Session):
    names = html.title.string.split('|')[0].strip()
    split_names(names, person)
    date = html.find("div", class_="text-xl")
    if date:
        date = date.string.replace('\n', '').replace('\t', '').strip()
        get_life_events(date, person)
    get_images(html, person, session)


def get_data_svm():
    with open(TEXTFILE, 'r', encoding='utf-8') as file:
        with Session() as session:
            for url in file:
                print(f"[INFO] retrieving data from {url.strip()}")
                response = session.get(url.strip())
                if response.ok:
                    soup = BeautifulSoup(response.content, "html.parser")
                    person = Person()
                    person.identifier.uri = url.strip()
                    create_svm_person(soup, person, session)
                    persons.append(person)
                sleep(2)


if __name__ == '__main__':
    get_data_svm()
    write_csv(OUTPUT, persons)
