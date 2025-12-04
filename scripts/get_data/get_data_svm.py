"""Crawler for https://www.svm.be/componisten that exports person data to VNA CSV.

Reads a UTF-8 text file with one SVM person URL per line, scrapes structured data
(name, birth/death date and place) and associated images, and writes a CSV via
the project's `scripts.person` helpers (`Person`, `Event`, `write_csv`).

Notes:
    - Dates are expected as DD/MM/YYYY in a `<div class="text-xl">` string
      that contains "birth — death" separated by an em dash.
    - Images are discovered via `<a class="js-modal-image" href="...">`.
    - A polite delay (2 seconds) is applied between HTTP requests.
"""

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

def get_life_events(text: str, person: Person):
    """Parse a "birth — death" string into Person.birth/Person.death.

    The input typically looks like "° Place, DD/MM/YYYY — ✝ Place, DD/MM/YYYY"
    but the function mainly relies on the " — " separator and delegates the
    "place, date" parsing to `split_date_place`.

    Args:
        text: Raw life-events text extracted from the page (single line).
        person: Mutable Person instance whose `birth` and `death` fields will
            be populated with `.date` (YYYY-MM-DD) and `.place` (string).

    Side Effects:
        - Mutates `person.birth.date`, `person.birth.place`,
          `person.death.date`, and `person.death.place`.
    """
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
    """Split a "place, DD/MM/YYYY" fragment into an Event(place, date).

    The function assumes the last comma-separated token is the date in
    `DD/MM/YYYY` and everything before that is the place (commas preserved).

    Args:
        text: A fragment like "° City, 01/02/1900" or "Place, Subplace, 31/12/1990".

    Returns:
        Event: with `.place` and `.date` set. If parsing fails or the fragment
        is incomplete, `.date` is set to the error token `ERROR_MESSAGE`.

    Notes:
        - Date is formatted to ISO `YYYY-MM-DD` using `datetime.strptime(..., '%d/%m/%Y')`.
    """

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
    """Download all image links in `tags` and append their filenames to Person.picture.

    For each `<a class="js-modal-image" href="...">` tag, the image is downloaded
    (if not already present) into `directory`. The basename is appended
    (comma-separated) to `person.picture`.

    Args:
        tags: BeautifulSoup ResultSet of <a> tags with `href` to the image file.
        directory: Destination directory (created by caller).
        person: Person object whose `.picture` will aggregate the filenames.
        session: Shared requests Session used for HTTP GET.

    Side Effects:
        - Writes image files to `directory`.
        - Mutates `person.picture` by appending filenames and trailing commas.
    """
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
    """Find and download person images, storing filenames on Person.picture.

    Looks for `<a class="js-modal-image">` anchors. If present:
      - The output subfolder is `<ROOT_FOLDER>/<PHOTO_FOLDER>/<identifier>`,
        where `identifier` is taken from the last segment of `person.identifier.uri`.
      - Files are downloaded via `download_images(...)`.
      - `person.picture` is finally normalized with `beautify_string`.

    If no images are found, an informational message is logged.

    Args:
        html: Parsed BeautifulSoup document for a person page.
        person: Person instance (must have `.identifier.uri` set).
        session: Shared requests Session for HTTP.

    Side Effects:
        - Creates the subfolder if needed; writes image files.
        - Updates `person.picture`.
    """
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


def split_names(value: str, person: Person):
    """Split a "Last, First[, Middle...]" string into Person.name fields.

    If a comma is present:
      - `person.name.last` is set to the text before the first comma.
      - `person.name.first` is set to the text after the first comma
        (additional tokens are concatenated without extra commas).
    If no comma is present, `person.name.full` is set to the original string.

    Args:
        value: Raw name value (usually from <title>).
        person: Person instance to mutate.
    """
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
    """Populate a Person instance from an SVM composer detail page.

    Steps:
        1) Extract the name from the <title> text (before the first '|') and
           feed it into `split_names(...)`.
        2) Extract the life event block from <div class="text-xl"> and pass it
           to `get_life_events(...)`.
        3) Discover and download images with `get_images(...)`.

    Args:
        html: Parsed BeautifulSoup document.
        person: Newly created Person instance to fill.
        session: Shared requests Session for HTTP.
    """
    names = html.title.string.split('|')[0].strip()
    split_names(names, person)
    date = html.find("div", class_="text-xl")
    if date:
        date = date.string.replace('\n', '').replace('\t', '').strip()
        get_life_events(date, person)
    get_images(html, person, session)


def get_data_svm():
    """Main crawl loop: read URLs, scrape each, collect Person objects.

    Reads the text file given in `TEXTFILE` (one URL per line, UTF-8). For each
    URL:
        - Fetch page content via a shared `requests.Session`.
        - Parse with BeautifulSoup.
        - Create and populate a `Person` with `create_svm_person(...)`.
        - Append it to the `persons` list.
        - Sleep 2 seconds (politeness).

    Side Effects:
        - Mutates the global `persons` list.
        - Performs network requests and file I/O (image downloads).
    """
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
    # This runs the crawl and
    # writes the final CSV to the path provided as argv[2]`.
    get_data_svm()
    write_csv(OUTPUT, persons)
