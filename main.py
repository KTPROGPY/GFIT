from csv import DictReader
from os import listdir
from json import load
import pandas as pd

# slownik .csv
lista_DWA = []

with open('Dzienne wskaźniki aktywności.csv', mode='r', encoding='utf-8') as DWA:
    czytnik =  DictReader(DWA)

    for wiersz in czytnik:
        czysty_wiersz = {}
        for klucz, wartosc in wiersz.items():
            if wartosc:
                try:
                    wartosc = float(wartosc)
                except ValueError:
                    pass
                czysty_wiersz[klucz] = wartosc
        lista_DWA.append(czysty_wiersz)

# slownik .json
katalog = '.'
wyniki_snu = []
for nazwa_pliku in listdir(katalog):
    if nazwa_pliku.endswith(".json"):
        with open(nazwa_pliku, 'r', encoding='utf-8') as plik:
            dane = load(plik)
            if dane.get("fitnessActivity") == "sleep":
                if "startTime" in dane and "endTime" in dane and "duration" in dane:
                    czas_snu_tekst = dane["duration"]
                    sekundy_snu = int(czas_snu_tekst[:-1])
                    if sekundy_snu < 7200:
                        continue

                    pelna_data_konca = dane["endTime"]
                    rozdzielone_koniec = pelna_data_konca.split('T')
                    data_dla_snu = rozdzielone_koniec[0]
                    godzina_pobudki = rozdzielone_koniec[1][:-1]
                    pelna_data_start = dane["startTime"]
                    godzina_startu = pelna_data_start.split('T')[1][:-1]


                    wpis = {
                        "Data": data_dla_snu,
                        "start": godzina_startu,
                        "koniec": godzina_pobudki,
                        "czas_tekst": sekundy_snu
                    }
                    wyniki_snu.append(wpis)


# DF baza

tabela_aktywnosc = pd.DataFrame(lista_DWA)
tabela_sen = pd.DataFrame(wyniki_snu)

tabela_danych = pd.merge(tabela_aktywnosc, tabela_sen, on='Data', how='outer')
tabela_danych['Punkty kardio'] = tabela_danych['Punkty kardio'].fillna(0)
tabela_danych['Minuty intensywnego treningu'] = tabela_danych['Minuty intensywnego treningu'].fillna(0)

tabela_danych['Data'] = pd.to_datetime(tabela_danych['Data'])
tabela_danych['start'] = pd.to_datetime(tabela_danych['start'], errors='coerce').dt.time
tabela_danych['koniec'] = pd.to_datetime(tabela_danych['koniec'], errors='coerce').dt.time

print(tabela_danych.info())
