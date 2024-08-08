from pywikibot import Site, Category, pagegenerators
from sys import argv
from csv import DictReader
from pathlib import Path
import shutil
import os

source_file = argv[1]
output_folder = argv[2]

def download_category(download_path, name):
    category_name = "Category:" + name
    site = Site("commons", "commons")
    category = Category(site, category_name)
    generator = pagegenerators.CategorizedPageGenerator(category)
    for page in generator:
        filename = str(page.title())
        if filename.startswith('File:'):
            filename = filename[5:]
        try:
            print("downloading {}".format(filename))
            page.download("{}/{}".format(download_path,filename))
        except Exception as error:
            print(error)

def download_image(download_path, image):
    image_path = "File:" + image
    output_path = "{}/{}".format(download_path, image)
    command = 'wikiget \"{}\" -o \"{}\"'.format(image_path, output_path)
    print("downloading " + image)
    os.system(command)



if __name__ == '__main__':
    with open(source_file, 'r') as csv_file:
        reader =  DictReader(csv_file)
        
        for row in reader:
            category = row["Commons category"]
            image = row["image"]
            
            if category or image:
                print("busy with " + row["volledige naam"])
                download_path = "{}/{}".format(output_folder, row['Wikidata ID'])
                Path(download_path).mkdir(parents=True, exist_ok=True)

                if category:
                    download_category(download_path, category)

                if image:
                    download_image(download_path, image)
  
            print("done\n")


shutil.rmtree('apicache')
os.remove('throttle.ctrl')
