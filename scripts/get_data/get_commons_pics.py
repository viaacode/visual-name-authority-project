from pywikibot import Site, Category, pagegenerators
from sys import argv
from csv import DictReader
from pathlib import Path
import shutil

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


if __name__ == '__main__':
    with open(source_file, 'r') as csv_file:
        reader =  DictReader(csv_file)
        for row in reader:
            category = row["Commons category"]
            if category:
                print(category)
                print("busy with " + row["volledige naam"])
                download_path = "{}/{}".format(output_folder, row['Wikidata ID'])
                Path(download_path).mkdir(parents=True, exist_ok=True)
                download_category(download_path, category)
                print("done\n")


shutil.rmtree('apicache')
