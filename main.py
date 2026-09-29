from csv import DictReader
from os import listdir
from json import load
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates

# slownik .csv
lista_DWA = []

with open('Dzienne wskaźniki aktywności.csv', mode='r', encoding='utf-8') as DWA:
    czytnik = DictReader(DWA)

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
                        "czas_snu": sekundy_snu
                    }
                    wyniki_snu.append(wpis)

# DF baza

tabela_aktywnosc = pd.DataFrame(lista_DWA)
tabela_sen = pd.DataFrame(wyniki_snu)

tabela_danych = pd.merge(tabela_aktywnosc, tabela_sen, on='Data', how='outer')
tabela_danych['Czas snu (min)'] = tabela_danych['czas_snu'] // 60
tabela_danych['Punkty kardio'] = tabela_danych['Punkty kardio'].fillna(0)
tabela_danych['Minuty intensywnego treningu'] = tabela_danych['Minuty intensywnego treningu'].fillna(0)
tabela_danych['Data'] = pd.to_datetime(tabela_danych['Data'])
tabela_danych = tabela_danych.sort_values(by='Data').reset_index(drop=True)
tabela_danych['Średnia waga (kg)'] = tabela_danych['Średnia waga (kg)'].interpolate(method='linear')
# tabela_danych['start'] = pd.to_datetime(tabela_danych['start'], errors='coerce').dt.time
# tabela_danych['koniec'] = pd.to_datetime(tabela_danych['koniec'], errors='coerce').dt.time
sensowne_kolumny = [
    'Data',
    'Liczba kroków',
    'Kalorie (kcal)',
    'Odległość (m)',
    'Punkty kardio',
    'Minuty intensywnego treningu',
    'Średnie tętno (bpm)',
    'Najniższe tętno (bpm)',
    'Najwyższe tętno (bpm)',
    'Średnia waga (kg)',
    'Liczba minut ruchu',
    'Min. wysycenie tlenem (%)',
    'Średnie wysycenie tlenem (%)',
    'Czas snu (min)'
]
tabela_danych = tabela_danych[sensowne_kolumny]


# print(tabela_danych.info())

# Funkcje


def statystyki(dane, parametr, data_od, data_do):
    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)

    dane = dane[(dane['Data'] >= data_od) & (dane['Data'] <= data_do)]
    czyste_dane = dane.dropna(subset=[parametr])

    if czyste_dane.empty:
        return None, None, None

    srednia = czyste_dane[parametr].mean()
    odchylenie = czyste_dane[parametr].std()

    roznica = abs(czyste_dane[parametr] - srednia)
    aberracje = czyste_dane[roznica > (2 * odchylenie)]

    return srednia, odchylenie, aberracje[['Data', parametr]]


# test
print(statystyki(tabela_danych, parametr='Najniższe tętno (bpm)', data_od='2026-05-01', data_do='2026-08-30'))


def rysuj_wykres(dane, parametr, data_od, data_do):
    srednia, odchylenie, aberracje = statystyki(dane, parametr, data_od, data_do)

    if srednia is None:
        print(f"Brak danych dla parametru '{parametr}' w wybranym zakresie.")
        return None

    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)
    dane = dane[(dane['Data'] >= data_od) & (dane['Data'] <= data_do)]
    czyste_dane = dane.dropna(subset=[parametr]).sort_values('Data')

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(czyste_dane['Data'], czyste_dane[parametr], label=parametr, marker='o', zorder=3)
    ax.axhline(srednia, color='green', linestyle='--', label=f'Średnia: {srednia:.1f}', zorder=2)

    # Poprawione wcięcie – rysujemy kropki anomalii, jeśli istnieją
    if not aberracje.empty:
        ax.scatter(aberracje['Data'], aberracje[parametr], color='red', s=100, zorder=5, label='Anomalie')

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel(parametr)  # Usunięte zbędne klamry wokół zmiennej
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=15, maxticks=30))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    ax.legend()
    plt.tight_layout()
    plt.show()
    return fig


# test
rysuj_wykres(tabela_danych, parametr='Czas snu (min)', data_od='2026-05-01', data_do='2026-08-30')


def rysuj_wykresy(dane, data_od, data_do, parametr_1, parametr_2):
    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)
    dane = dane[(dane['Data'] >= data_od) & (dane['Data'] <= data_do)]

    srednia_k7_1 = f'{parametr_1}_srednia'
    srednia_k7_2 = f'{parametr_2}_srednia'
    dane[srednia_k7_1] = dane[parametr_1].rolling(window=7, min_periods=1).mean()
    dane[srednia_k7_2] = dane[parametr_2].rolling(window=7, min_periods=1).mean()

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(dane['Data'], dane[parametr_1], marker='o', linestyle='none', color='lightblue', label=f'{parametr_1}')
    ax1.plot(dane['Data'], dane[srednia_k7_1], linewidth=2, color='blue', label=f'{parametr_1} (średnia 7-dniowa)')
    ax1.set_ylabel(parametr_1, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()
    ax2.plot(dane['Data'], dane[parametr_2], marker='^', linestyle='none', color='salmon', label=f'{parametr_2}')
    ax2.plot(dane['Data'], dane[srednia_k7_2], linewidth=2, color='red', label=f'{parametr_2} (średnia 7-dniowa)')
    ax2.set_ylabel(parametr_2, color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.setp(ax1.get_xticklabels(), rotation=45)
    linie_ax1, etykiety_ax1 = ax1.get_legend_handles_labels()
    linie_ax2, etykiety_ax2 = ax2.get_legend_handles_labels()
    ax1.legend(linie_ax1 + linie_ax2, etykiety_ax1 + etykiety_ax2, loc='upper left')
    plt.tight_layout()
    plt.show()

    return fig


# test
rysuj_wykresy(
    tabela_danych,
    data_od='2026-05-01',
    data_do='2026-08-30',
    parametr_1='Czas snu (min)',
    parametr_2='Najniższe tętno (bpm)'
)


def heatmapa_korelacji(dane, lista_parametrow, data_od, data_do):
    df_wykres = dane.copy()
    df_wykres['Data'] = pd.to_datetime(df_wykres['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)
    df_wykres = df_wykres[(df_wykres['Data'] >= data_od) & (df_wykres['Data'] <= data_do)]
    czyste_dane = df_wykres[lista_parametrow].dropna()

    if czyste_dane.empty:
        print("Brak danych do wygenerowania korelacji.")
        return None

    macierz_korelacji = czyste_dane.corr()

    fig, ax = plt.subplots(figsize=(12, 10))

    img = ax.imshow(macierz_korelacji, cmap='coolwarm', vmin=-1, vmax=1)

    ax.set_xticks(range(len(lista_parametrow)))
    ax.set_yticks(range(len(lista_parametrow)))

    ax.set_xticklabels(lista_parametrow, rotation=45, ha='right')
    ax.set_yticklabels(lista_parametrow)


    for i in range(len(lista_parametrow)):
        for j in range(len(lista_parametrow)):
            wartosc = macierz_korelacji.iloc[i, j]
            kolor_tekstu = 'white' if abs(wartosc) > 0.5 else 'black'
            ax.text(j, i, f"{wartosc:.2f}", ha='center', va='center', color=kolor_tekstu, fontsize=9, fontweight='bold')

    plt.colorbar(img, label='Współczynnik korelacji')
    ax.set_title("Macierz korelacji parametrów zdrowotnych", pad=20)
    plt.subplots_adjust(bottom=0.25, left=0.25, top=0.9, right=0.9)
    plt.show()

    return fig



parametry_do_badania = [
    'Liczba kroków',
    'Kalorie (kcal)',
    'Odległość (m)',
    'Punkty kardio',
    'Minuty intensywnego treningu',
    'Średnie tętno (bpm)',
    'Najniższe tętno (bpm)',
    'Najwyższe tętno (bpm)',
    'Średnia waga (kg)',
    'Liczba minut ruchu',
    #'Min. wysycenie tlenem (%)',
    'Średnie wysycenie tlenem (%)',
    'Czas snu (min)'
]

# test
heatmapa_korelacji(
    tabela_danych,
    lista_parametrow=parametry_do_badania,
    data_od='2026-01-01',
    data_do='2026-08-30'
)