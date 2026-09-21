import csv
import os
import json

# slownik .csv
lista_DWA = []

with open('Dzienne wskaźniki aktywności.csv', mode='r', encoding='utf-8') as DWA:
    czytnik = csv.DictReader(DWA)

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
for nazwa_pliku in os.listdir(katalog):
    if nazwa_pliku.endswith(".json"):
        with open(nazwa_pliku, 'r', encoding='utf-8') as plik:
            dane = json.load(plik)
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
                    calkowite_minuty = sekundy_snu // 60

                    wpis = {
                        "data": data_dla_snu,
                        "start": godzina_startu,
                        "koniec": godzina_pobudki,
                        "czas_tekst": f"{calkowite_minuty} min"
                    }
                    wyniki_snu.append(wpis)


#for sen in wyniki_snu:
    #print(f"Data pobudki: {sen['data']} | Zasypianie: {sen['start']} | Pobudka: {sen['koniec']} | Czas: {sen['czas_tekst']}")

# Słownik zbiorczy
analiza_dzienna = {}


for wiersz_csv in lista_DWA:
    data = wiersz_csv["Data"]
    analiza_dzienna[data] = {
        "aktywnosc": wiersz_csv,
        "sen": None
    }
for sen in wyniki_snu:
    data_snu = sen["data"]

    if data_snu in analiza_dzienna:
        analiza_dzienna[data_snu]["sen"] = sen
    else:
        analiza_dzienna[data_snu] = {
            "aktywnosc": None,
            "sen": sen
        }

for data, zawartosc in analiza_dzienna.items():
    print(f"Data: {data}")
    print(f"  -> Aktywność: {zawartosc['aktywnosc']}")
    print(f"  -> Sen: {zawartosc['sen']}")
    print("-" * 50)