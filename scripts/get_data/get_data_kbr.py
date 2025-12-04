"""Download paged XML records from the KBR OAI-PMH server.

This script issues repeated OAI-PMH `ListRecords` requests against
`https://opac.kbr.be/oaiserver.ashx` using a known resumption token pattern
(`!!AUTHOR!<offset>!492043!oai_dc`) and writes each response to a separate
pretty-printed XML file in `FOLDER`.

Notes:
    - The resumption token is constructed, not read from the server responses.
      If KBR changes its token format, adjust the pattern accordingly.
    - Files are written as UTF-8 with indentation via `xml.dom.minidom`.
    - Network errors or invalid XML will raise exceptions unless handled by the caller.
"""

import xml.dom.minidom
import requests

DOMAIN = 'https://opac.kbr.be/oaiserver.ashx'
OAI_VERB = 'ListRecords'
FOLDER = 'path/to/my_folder' # change this

session = requests.Session()
for page in range(0,492100,100):
    TOKEN = f"!!AUTHOR!{page}!492043!oai_dc"
    URL = f"{DOMAIN}?verb={OAI_VERB}&resumptionToken={TOKEN}"
    response = session.get(URL, timeout=60)
    response.encoding = response.apparent_encoding
    xml_data = xml.dom.minidom.parseString(response.text)

    with open(f"{FOLDER}/kbr_oai_pmh_{page}.xml", 'w', encoding='utf-8') as file:
        file.write(xml_data.toprettyxml())
