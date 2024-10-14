"""Script to download XML-files from the OAI-PMH server of KBR"""

import xml.dom.minidom
import requests

DOMAIN = 'https://opac.kbr.be/oaiserver.ashx'
OAI_VERB = 'ListRecords'
FOLDER = 'path/to/my_folder' # change this

for page in range(0,492100,100):
    token = f"!!AUTHOR!{page}!492043!oai_dc"
    url = f"{DOMAIN}?verb={OAI_VERB}&resumptionToken={token}"
    response = requests.get(url, timeout=60)
    response.encoding = response.apparent_encoding
    xml_data = xml.dom.minidom.parseString(response.text)

    with open(f"{FOLDER}/kbr_oai_pmh_{page}.xml", 'w', encoding='utf-8') as file:
        file.write(xml_data.toprettyxml())
