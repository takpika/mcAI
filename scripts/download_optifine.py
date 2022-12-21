import requests
from bs4 import BeautifulSoup

req = requests.get("https://optifine.net/adloadx?f=OptiFine_1.19.2_HD_U_H9.jar")
if req.status_code != 200:
    exit(1)
soup = BeautifulSoup(req.text, 'html.parser')
for elm in soup.find_all('a'):
    if elm.get_text() == "Download" and elm.get("onclick") == "onDownload()":
        print("https://optifine.net/%s" % (elm.get("href")))
        break