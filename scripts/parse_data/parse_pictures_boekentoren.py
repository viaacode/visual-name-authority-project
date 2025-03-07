"""
Werkwijze:
- gebruik spacy om eerst de titel uit te lezen (response.document.title)
- als het aantal mensen hierna nog 0 is, check dan of er 'Portret van' is en kap de tekst erna af
- sla ook het aantal mensen op, zodat we kunnen corrigeren bij meerdere mensen
- misschien ook nuttig om de licentie mee op te nemen (has_download_license)
"""

import json
import os
from sys import argv
import spacy

FOLDER = argv[1]

MODEL = "nl_core_news_lg"
nlp = spacy.load(MODEL)


for json_file in os.listdir(FOLDER)[:30]:
    with open(f"{FOLDER}/{json_file}", 'r', encoding="utf-8", ) as datafile:
        data = json.load(datafile)
        document = data['response']['document']
        title = document.get('title','')
        person_name = [title]
        text = nlp(title)
        print(json_file)
        for entity in text.ents:
            if entity.label_ == "PERSON":
                person_name.append(entity.text)
        if len(person_name) == 1:
            name = title.split("Portret van ")[1]
            if not 'onbekend' in name:
                person_name.append(name)
        print(person_name)
