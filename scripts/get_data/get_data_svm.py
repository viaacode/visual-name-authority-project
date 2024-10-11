from bs4 import BeautifulSoup, ResultSet
from datetime import datetime
from pathlib import Path
import os
from requests import Session
from sys import path, argv, exit
from time import sleep

# import local packages
path_root = Path(__file__).parents[2]
path.append(str(path_root))
from scripts.person import Person, Event, split_names, write_csv, beautify_string

# lees de file uit
# haal de url op met requests

textfile = argv[1]
root_folder = str(Path(os.path.abspath(textfile)).parent.absolute())
output = argv[2]
persons = []
photo_folder = 'foto'


def get_life_events(text: str, person: Person): 
    life_events = text.split(' — ')
    life_events = [event.strip() for event in life_events]
    if len(life_events) > 0:
        birth_event = split_date_place(life_events[0])
        person.birthdate = birth_event.date
        person.place_of_birth = birth_event.place
    if len(life_events) > 1 and len(life_events[1]) > 2:
        death_event = split_date_place(life_events[1])
        person.deathdate = death_event.date
        person.place_of_death = death_event.place

def split_date_place(text: str) -> Event:
    data = text.split(',')
    if len(data) > 1:
        place = data[0][2:]
        date = datetime.strptime(data[1].strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
        return Event(place, date)
    if len(data) == 1:
        print("[ERROR] Maybe no date or place")
        exit()
    else: 
        return Event()
    
def donwload_images(tags: ResultSet, directory: str, person: Person, session: Session):
    for tag in tags:
        url = tag['href']
        filename = url.split('/')[-1]
        output_file = "{}/{}".format(directory, filename)
        if not os.path.exists(output_file):
            print("[INFO] downloading image {}".format(url))
            image = session.get(url).content
            with open(output_file, 'wb') as handler:
                handler.write(image)
        person.picture += filename + ','

    
def get_images(html: BeautifulSoup, person: Person, session: Session):
    tags = html.find_all("a", class_="js-modal-image")
    if tags:
        id = person.uri.split('/')[-1]
        folder = "{}/{}/{}".format(root_folder, photo_folder, id)
        if not os.path.exists(folder):
            os.makedirs(folder)
        donwload_images(tags, folder, person, session)
        person.picture = beautify_string(person.picture)


def create_svm_person(html: BeautifulSoup, person: Person, session: Session):
    names = html.title.string.split('|')[0].strip()
    split_names(names, person)
    date = html.find("div", class_="text-xl").string.replace('\n', '').replace('\t', '').strip()
    get_life_events(date, person)
    get_images(html, person, session)


def get_data_svm():
    with open(textfile, 'r') as file:
        with Session() as session:
            for url in file:
                print("[INFO] retrieving data from {}".format(url))
                response = session.get(url.strip())
                soup = BeautifulSoup(response.content, "html.parser")
                person = Person()
                person.uri = url.strip()
                create_svm_person(soup, person, session)
                persons.append(person)
                sleep(2)


if __name__ == '__main__':
    get_data_svm()
    write_csv(output, persons)