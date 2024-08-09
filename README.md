# Visual Name Authority Project

Bevat de visualisatie van het datamodel en de scripts gebruikt voor het voorbereiden van de metadata en foto's voor het Visual Name Authority-project.

## Installatie

De scripts vereisen minstens python 3.11

1. Creëer een virtuele environment. 

```
python3 -m pip install virtualenv # als virtualenv niet geïnstalleerd is
mkvirtualenv visual_name_authority
```

2. Installeer de nodige packages

```
cat requirements.txt | xargs -n 1 -L 1 pip install
```

## Gebruik 

Voordat je de scripts kan gebruiken, moet je je virtuele environment activeren:

```
workon visual_name_authority
```

