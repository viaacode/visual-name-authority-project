"""Parse Boekentoren JSON records to a row-per-person CSV.

For each JSON file in FOLDER:
  - Detect person names from `response.document.title` via spaCy NER
    (`nl_core_news_lg`) with a rule-based fallback for titles that contain
    "Portret van …".
  - Enrich names using `response.document.display_author` strings
    (VIAF, birth-death years, pseudonym handling).
  - Compute an IIIF image URL from `thumbnail_url` (string only, no download).
  - Decide type ("PORTRET" vs "GROEP") and write one CSV row per depicted person.

Output columns:
  [photo_id, title, type, realname, alias, birthdate, deathdate, viaf,
   license, image_url, status]
"""


import csv
from dataclasses import dataclass, field
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
    """Lightweight container for the depicted person’s attributes.

    Attributes:
        label: Name as originally detected (from title or fallback).
        realname: Normalized real name (may differ if the label is a pseudonym).
        alias: Alias/pseudonym, if applicable.
        birthdate: Birth year (string) if available.
        deathdate: Death year (string) if available.
        viaf: VIAF numeric identifier extracted from text.
        status: Free-text status/flag (e.g., 'NAKIJKEN!!' for manual review).
    """
    label: str = ""
    realname: str = ""
    alias: str = ""
    birthdate: str = ""
    deathdate: str = ""
    viaf: str = ""
    status: str = ""

@dataclass
class Photo:
    """Container for a single photo record and its depicted persons.

    Attributes:
        id: Photo identifier from the JSON record.
        title: Title used for NER and logging.
        type: "PORTRET" for single-person, "GROEP" when multiple persons found.
        persons: List of `Person` entries derived from title/extra info.
        license: string from 'has_download_license'.
        image: Canonical IIIF Image API URL (string only, not downloaded).
    """
    id: str = ""
    title: str = ""
    type: str = "PORTRET"
    persons: list[Person] = field(default_factory=list)
    license: str = ""
    image: str = ""

    def print_properties(self) -> list[list[str]]:
        """Return rows for CSV writing (one row per person for this photo).

        Returns:
            A list of lists, each representing:
            [id, title, type, realname, alias, birthdate, deathdate,
                viaf, license, image, status]
        """
        lines = []

        for person in self.persons:
            lines.append([
                self.id, self.title, self.type, person.realname, person.alias, person.birthdate,
                person.deathdate, person.viaf, self.license, self.image, person.status
            ])
        return lines

def get_person_names(sentence: str) -> list[str]:
    """Extract person names from a title using spaCy NER with a fallback.

    - Run spaCy NER and collect entities labeled 'PERSON'.
    - If none are found and the title contains 'portret van', use the part
      after 'Portret van ' as the name (unless it contains 'onbekend').
    - If no name can be inferred, insert a sentinel ('FOUT!!') and set the
      global `download_image` flag to False (disables IIIF URL generation
      for this record).

    Args:
        sentence: The photo title.

    Returns:
        A list of candidate person names (may be empty or contain a sentinel).
    """
    global download_image
    person_names = []
    text = nlp(sentence)
    for entity in text.ents:
        if entity.label_ == "PERSON":
            person_names.append(entity.text)
    if not person_names:
        lower = sentence.lower()
        if 'portret van' in lower:
            try:
                after = sentence[lower.index("portret van") + len("portret van"):].strip()
                if after and "onbekend" not in after.lower():
                    person_names.append(after)
            except ValueError:
                pass
        if not person_names:
            person_names.append("FOUT!!")
            download_image = False

    return person_names

def get_viaf(sentence: str) -> str:
    """Extract a VIAF numeric identifier from a line containing '(viaf)'.

    Args:
        sentence: A string from `display_author`.

    Returns:
        The first digit sequence after '(viaf)', or an empty string.
    """
    viaf = ""
    parts = sentence.split("(viaf)")
    if len(parts) > 1:
        digits = re.findall(r"\d+", parts[1])
        if digits:
            viaf = digits[0]
    #print(f"viaf : {viaf}")
    return viaf

def get_real_name(sentence: str, person: Person):
    """Populate `realname`/`alias` from an author line with pseudonym handling.

    Heuristics:
        - If the line contains 'pseudoniem', try to split 'pseudoniem van …'
          and set `person.alias` to the current label and `person.realname`
          to the extracted name; otherwise flag for review.
        - Otherwise, attempt to normalize 'Lastname, Firstname …' patterns
          into 'Firstname Lastname' and assign to `person.realname`.
        - Set `person.label` to the final `realname` if no pseudonym case.

    Args:
        sentence: A string from `display_author` with extra person info.
        person: The Person instance to update.
    """
    if 'pseudoniem' in sentence:
        pseudos = sentence.split("pseudoniem van")
        pseudo = pseudos[1].split("(role)dpc")
        if len(pseudo) > 1:
            pseudo = pseudo[0].strip()
            person.alias = person.label
            person.realname = pseudo
        else:
            person.status = "NAKIJKEN!!"
    else:
        realname = sentence.split(" (")
        person.realname = realname
        if len(realname) > 1:
            names = realname[0].split(', ')
            lastname = names[0]
            if len(names) == 2:
                firstname = names[1]
            else:
                firstname = ''
                for i in range(1,len(names)-1):
                    firstname += names[i] + ' '
            person.realname = f"{firstname.strip()} {lastname.strip()}"
        person.label = person.realname

def get_depicted(person_info: str, person: Person) -> Person:
    """Enrich a Person with dates, VIAF, and realname from a detail line.

    - Extract a 'YYYY-YYYY' range for birth/death years.
    - Extract VIAF via `get_viaf`.
    - Normalize real name via `get_real_name`.

    Args:
        person_info: A string describing the depicted person.
        person: The Person instance to update.

    Returns:
        The updated Person.
    """
    dates = re.findall(r"\d{4}-\d{4}", person_info)
    if dates:
        (birth, death) = dates[0].split('-')
        person.birthdate = birth
        person.deathdate = death
    person.viaf = get_viaf(person_info)
    get_real_name(person_info, person)
    return person

def get_depicted_persons(persons_lines: list[str], person: Person):
    """Match and enrich a Person against a list of detail lines.

    If the first token of `person.label` appears in a line, treat that line
    as the detail line for this person and call `get_depicted`.

    Args:
        persons_lines: Candidate strings from `display_author`.
        person: The Person instance to enrich in place.
    """
    for sentence in persons_lines:
        if person.label.split(' ')[0] in sentence:
            person = get_depicted(sentence, person)

def get_persons(json_root, title) -> list[Person]:
    """Build the list of depicted persons for one photo.

    Steps:
        1) Detect names from the title via `get_person_names`.
        2) Filter `display_author` to lines containing 'dpc' (if present).
        3) For each detected name, try to enrich via `get_depicted_persons`.
        4) If counts mismatch (extra info vs detected names), rebuild the
           persons list from the extra info lines and flag entries for review.

    Args:
        json_root: The 'document' dict (`response.document`) for a photo.
        title: The photo title.

    Returns:
        A list of `Person` objects.
    """
    names = get_person_names(title)
    persons: list[Person] = []
    extra_persons_info = json_root.get('display_author')
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

    return persons

def get_image(url: str) -> str:
    """Return a canonical IIIF image URL derived from a thumbnail URL.

    Replaces the tail of the given path with '/full/full/0/default.jpg'.

    Args:
        url: The source thumbnail URL.

    Returns:
        A string containing the derived IIIF image URL.
    """
    url_words = url.split('/')
    iiif_part = '/full/full/0/default.jpg'
    photo_url = '/'.join(url_words[0:6]) + iiif_part
    return photo_url


photos: list[Photo] = []

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

