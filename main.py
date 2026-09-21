import csv

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
