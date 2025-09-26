import requests
from csv import DictReader
from sys import argv
from time import sleep
import os

SOURCEFILE = argv[1]
FOLDER = argv[2]

def get_picture(url: str, filename: str) -> None:
    #image = session.get(url).content
    print(f"getting picture {url}")
        #with open('{}.format(filename), 'wb') as handler:
            #handler.write(image)
    os.system(f"wget -O {filename} {url}")

with open(SOURCEFILE, 'r', encoding='utf-8') as source:
    reader = DictReader(source)
    #with requests.Session() as session:
    for row in reader:
        image_id = row['URI'].split('/')[-1]
        url = row['foto']
        print(f"busy with {image_id}")
        if url:
            FILENAME = f'{FOLDER}/{image_id}.jpg'
            if not os.path.exists(FILENAME):
                get_picture(url, FILENAME)
                sleep(3)
            else:
                print(f'image {FILENAME} already exists')
        else:
            print('no picture')
