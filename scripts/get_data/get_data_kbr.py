import xml.dom.minidom
import requests

DOMAIN = 'https://opac.kbr.be/oaiserver.ashx'
OAI_VERB = 'ListRecords'
FOLDER = 'path/to/my_folder' # change this

for page in range(0,492100,100):
  token = "!!AUTHOR!{}!492043!oai_dc".format(page)
  url = "{}?verb={}&resumptionToken={}".format(DOMAIN, OAI_VERB, token)
  response = requests.get(url)
  response.encoding = response.apparent_encoding
  xml_data = xml.dom.minidom.parseString(response.text)

  with open("{}/kbr_oai_pmh_{}.xml".format(FOLDER, page), 'w', encoding='utf-8') as file:
    file.write(xml_data.toprettyxml())