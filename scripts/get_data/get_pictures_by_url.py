import requests
from csv import DictReader
from sys import argv
from time import sleep

source_file = argv[1]
FOLDER = argv[2]

def get_picture(url: str, id: str, session: requests.Session) -> None:
    image = session.get(url).content
    print("getting picture {}".format(url))
    with open('{}/{}.jpg'.format(FOLDER, id), 'wb') as handler:
        handler.write(image)

with open(source_file, 'r', encoding='utf-8') as source:
    reader = DictReader(source)
    with requests.Session() as session:
        for row in reader:
            id = row['URI'].split('/')[-1]
            url = row['foto']
            print("busy with {}".format(id))
            if url:
                get_picture(url, id, session)
            else:
                print('no picture')
            sleep(3)