from csv import DictReader
from os import listdir
from json import load
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# wczytanie dzennego wskaznika aktywnosci
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

# wczytanie snu
katalog = '.'
wyniki_snu = []
for nazwa_pliku in listdir(katalog):
    # Dodany warunek "derived not in...", żeby pętla ignorowała duży plik z tętnem
    if nazwa_pliku.endswith(".json") and "derived" not in nazwa_pliku:
        with open(nazwa_pliku, 'r', encoding='utf-8') as plik:
            dane = load(plik)
            if dane.get("fitnessActivity") == "sleep":
                if "startTime" in dane and "endTime" in dane and "duration" in dane:
                    czas_snu_tekst = dane["duration"]
                    sekundy_snu = int(czas_snu_tekst[:-1])
                    if sekundy_snu < 7200:
                        continue

                    pelna_data_konca = dane["endTime"]
                    data_dla_snu = pelna_data_konca.split('T')[0]

                    wpis = {
                        "Data": pd.to_datetime(data_dla_snu),
                        "start_pelny": pd.to_datetime(dane["startTime"][:-1]),
                        "koniec_pelny": pd.to_datetime(pelna_data_konca[:-1]),
                        "czas_snu": sekundy_snu
                    }
                    wyniki_snu.append(wpis)

tabela_aktywnosc = pd.DataFrame(lista_DWA)
tabela_sen = pd.DataFrame(wyniki_snu)
tabela_aktywnosc['Data'] = pd.to_datetime(tabela_aktywnosc['Data'])
tabela_sen['Data'] = pd.to_datetime(tabela_sen['Data'])

# wczytanie tetna
nazwa_pliku_fit = 'derived_com.google.heart_rate.bpm_com.google.android.gms_merge_heart_rate_bpm.json'
with open(nazwa_pliku_fit, 'r', encoding='utf-8') as plik:
    dane_json = load(plik)

lista_tetna = []
for punkt in dane_json.get("Data Points", []):
    try:
        wartosc_bpm = punkt["fitValue"][0]["value"]["fpVal"]
        czas_sekundy = int(punkt["startTimeNanos"]) / 1_000_000_000
        lista_tetna.append({
            "PelnyCzas": pd.to_datetime(czas_sekundy, unit='s'),
            "Tetno": float(wartosc_bpm)
        })
    except (KeyError, IndexError, ValueError):
        continue

df_tetno = pd.DataFrame(lista_tetna)
df_tetno['PelnyCzas'] = df_tetno['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert('Europe/Warsaw').dt.tz_localize(None)

# obliczenia
dane_nocne_lista = []
for index, wiersz in tabela_sen.iterrows():
    maska = (df_tetno['PelnyCzas'] >= wiersz['start_pelny']) & (df_tetno['PelnyCzas'] <= wiersz['koniec_pelny'])
    tetno_w_czasie_snu = df_tetno[maska].copy()

    if not tetno_w_czasie_snu.empty:
        tetno_w_czasie_snu['Data'] = wiersz['Data']  # Kopiujemy tekstową datę do tętna
        dane_nocne_lista.append(tetno_w_czasie_snu)

if dane_nocne_lista:
    dane_nocne = pd.concat(dane_nocne_lista, ignore_index=True)
    dzienne_rhr = dane_nocne.groupby('Data')['Tetno'].median().reset_index()
    dzienne_rhr.rename(columns={'Tetno': 'Nocne tętno (bpm)'}, inplace=True)

    # Tworzenie kolumn do algorytmu Stanfordu
    dzienne_rhr['Baseline'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).mean()
    dzienne_rhr['Odchylenie'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).std()
    dzienne_rhr['Z_score'] = (dzienne_rhr['Nocne tętno (bpm)'] - dzienne_rhr['Baseline']) / dzienne_rhr['Odchylenie']
    dzienne_rhr['Anomalia'] = (dzienne_rhr['Z_score'] > 2.0).astype(int)
    dzienne_rhr['Prawie_anomalia'] = ((dzienne_rhr['Z_score'] > 1.5) & (dzienne_rhr['Z_score'] <= 2.0)).astype(int)
else:
    dzienne_rhr = pd.DataFrame(
        columns=['Data', 'Nocne tętno (bpm)', 'Baseline', 'Odchylenie', 'Z_score', 'Anomalia', 'Prawie_anomalia'])

# 5. ŁĄCZENIE (Twój stary styl, dodane tylko łączenie z dzienne_rhr)
tabela_danych = pd.merge(tabela_aktywnosc, tabela_sen, on='Data', how='outer')
tabela_danych = pd.merge(tabela_danych, dzienne_rhr, on='Data',
                         how='outer')  # Doklejamy tętno na podstawie tekstu z Data

tabela_danych['Czas snu (min)'] = tabela_danych['czas_snu'] // 60
tabela_danych['Punkty kardio'] = tabela_danych['Punkty kardio'].fillna(0)
tabela_danych['Minuty intensywnego treningu'] = tabela_danych['Minuty intensywnego treningu'].fillna(0)

# Dopiero po wszystkich merge'ach zamieniamy tekst w dacie na datetime (tak jak było u Ciebie)
tabela_danych['Data'] = pd.to_datetime(tabela_danych['Data'])
tabela_danych = tabela_danych.sort_values(by='Data').reset_index(drop=True)
tabela_danych['Średnia waga (kg)'] = tabela_danych['Średnia waga (kg)'].interpolate(method='linear')

sensowne_kolumny = [
    'Data', 'Liczba kroków', 'Kalorie (kcal)', 'Odległość (m)', 'Punkty kardio',
    'Minuty intensywnego treningu', 'Średnie tętno (bpm)', 'Nocne tętno (bpm)',  # Nowa kolumna
    'Baseline', 'Odchylenie', 'Z_score', 'Anomalia', 'Prawie_anomalia',  # Nowe kolumny z algorytmu
    'Najwyższe tętno (bpm)', 'Średnia waga (kg)', 'Liczba minut ruchu',
    'Średnie wysycenie tlenem (%)', 'Czas snu (min)'
]


dostepne_kolumny = [kol for kol in sensowne_kolumny if kol in tabela_danych.columns]
tabela_danych = tabela_danych[dostepne_kolumny]

def rysuj_wykres_rhr(dane, data_od, data_do):
    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)

    czyste_dane = dane[(dane['Data'] >= data_od) & (dane['Data'] <= data_do)].dropna(
        subset=['Nocne tętno (bpm)', 'Baseline']).sort_values('Data')

    if czyste_dane.empty:
        print("Brak danych w wybranym zakresie.")
        return None

    czyste_dane['Data_tekst'] = czyste_dane['Data'].dt.strftime('%Y-%m-%d')
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Nocne tętno (bpm)'], label='Nocne tętno (bpm)', marker='o',
            color='tab:blue', zorder=3, alpha=0.6)
    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Baseline'], label='Linia bazowa (28 dni)', color='green', zorder=2,
            linewidth=2)

    aberracje = czyste_dane[czyste_dane['Anomalia'] == 1]
    if not aberracje.empty:
        ax.scatter(aberracje['Data_tekst'], aberracje['Nocne tętno (bpm)'], color='red', s=100, zorder=5,
                   label='Anomalia (>2 odchylenia)')

    ostrzezenia = czyste_dane[czyste_dane['Prawie_anomalia'] == 1]
    if not ostrzezenia.empty:
        ax.scatter(ostrzezenia['Data_tekst'], ostrzezenia['Nocne tętno (bpm)'], color='orange', s=80, zorder=4,
                   label='Ostrzeżenie (1.5-2.0 odchylenia)')

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Nocne tętno (bpm)')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    ax.legend()
    plt.title('Wykrywanie fizjologicznych anomalii (wzór RHR-Diff)')
    plt.tight_layout()
    plt.show()
    return fig


def szereg_czasowy_kroki_tetno(dane, data_od, data_do):
    df = dane.copy()
    df['Data'] = pd.to_datetime(df['Data'])
    df = df[(df['Data'] >= data_od) & (df['Data'] <= data_do)]
    df = df.dropna(subset=['Liczba kroków', 'Nocne tętno (bpm)'])

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(df['Data'], df['Liczba kroków'], color='gray', alpha=0.3, label='Kroki')
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Liczba kroków', color='gray')
    ax1.tick_params(axis='y', labelcolor='gray')

    ax2 = ax1.twinx()
    ax2.plot(df['Data'], df['Nocne tętno (bpm)'], color='tab:red', linewidth=2, label='Tętno nocne')
    ax2.set_ylabel('Nocne tętno (bpm)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    fig.autofmt_xdate()
    plt.title('Szereg czasowy: Aktywność dzienna vs Regeneracja nocna')
    fig.tight_layout()
    plt.show()


# TESTY
parametry_do_badania = [
    'Liczba kroków', 'Kalorie (kcal)', 'Odległość (m)', 'Punkty kardio',
    'Minuty intensywnego treningu', 'Nocne tętno (bpm)',  # Zaktualizowana lista o nocne tętno
    'Średnia waga (kg)', 'Czas snu (min)'
]


rysuj_wykres_rhr(tabela_danych, data_od='2026-01-01', data_do='2026-08-30')
szereg_czasowy_kroki_tetno(tabela_danych, data_od='2026-01-01', data_do='2026-08-30')

from csv import DictReader
from os import listdir
from json import load
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# wczytanie dzennego wskaznika aktywnosci
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

# wczytanie snu
katalog = '.'
wyniki_snu = []
for nazwa_pliku in listdir(katalog):
    # Dodany warunek "derived not in...", żeby pętla ignorowała duży plik z tętnem
    if nazwa_pliku.endswith(".json") and "derived" not in nazwa_pliku:
        with open(nazwa_pliku, 'r', encoding='utf-8') as plik:
            dane = load(plik)
            if dane.get("fitnessActivity") == "sleep":
                if "startTime" in dane and "endTime" in dane and "duration" in dane:
                    czas_snu_tekst = dane["duration"]
                    sekundy_snu = int(czas_snu_tekst[:-1])
                    if sekundy_snu < 7200:
                        continue

                    pelna_data_konca = dane["endTime"]
                    data_dla_snu = pelna_data_konca.split('T')[0]

                    wpis = {
                        "Data": pd.to_datetime(data_dla_snu),
                        "start_pelny": pd.to_datetime(dane["startTime"][:-1]),
                        "koniec_pelny": pd.to_datetime(pelna_data_konca[:-1]),
                        "czas_snu": sekundy_snu
                    }
                    wyniki_snu.append(wpis)

tabela_aktywnosc = pd.DataFrame(lista_DWA)
tabela_sen = pd.DataFrame(wyniki_snu)
tabela_aktywnosc['Data'] = pd.to_datetime(tabela_aktywnosc['Data'])
tabela_sen['Data'] = pd.to_datetime(tabela_sen['Data'])

# wczytanie tetna
nazwa_pliku_fit = 'derived_com.google.heart_rate.bpm_com.google.android.gms_merge_heart_rate_bpm.json'
with open(nazwa_pliku_fit, 'r', encoding='utf-8') as plik:
    dane_json = load(plik)

lista_tetna = []
for punkt in dane_json.get("Data Points", []):
    try:
        wartosc_bpm = punkt["fitValue"][0]["value"]["fpVal"]
        czas_sekundy = int(punkt["startTimeNanos"]) / 1_000_000_000
        lista_tetna.append({
            "PelnyCzas": pd.to_datetime(czas_sekundy, unit='s'),
            "Tetno": float(wartosc_bpm)
        })
    except (KeyError, IndexError, ValueError):
        continue

df_tetno = pd.DataFrame(lista_tetna)
df_tetno['PelnyCzas'] = df_tetno['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert('Europe/Warsaw').dt.tz_localize(None)

# obliczenia
dane_nocne_lista = []
for index, wiersz in tabela_sen.iterrows():
    maska = (df_tetno['PelnyCzas'] >= wiersz['start_pelny']) & (df_tetno['PelnyCzas'] <= wiersz['koniec_pelny'])
    tetno_w_czasie_snu = df_tetno[maska].copy()

    if not tetno_w_czasie_snu.empty:
        tetno_w_czasie_snu['Data'] = wiersz['Data']  # Kopiujemy tekstową datę do tętna
        dane_nocne_lista.append(tetno_w_czasie_snu)

if dane_nocne_lista:
    dane_nocne = pd.concat(dane_nocne_lista, ignore_index=True)
    dzienne_rhr = dane_nocne.groupby('Data')['Tetno'].median().reset_index()
    dzienne_rhr.rename(columns={'Tetno': 'Nocne tętno (bpm)'}, inplace=True)

    # Tworzenie kolumn do algorytmu Stanfordu
    dzienne_rhr['Baseline'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).mean()
    dzienne_rhr['Odchylenie'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).std()
    dzienne_rhr['Z_score'] = (dzienne_rhr['Nocne tętno (bpm)'] - dzienne_rhr['Baseline']) / dzienne_rhr['Odchylenie']
    dzienne_rhr['Anomalia'] = (dzienne_rhr['Z_score'] > 2.0).astype(int)
    dzienne_rhr['Prawie_anomalia'] = ((dzienne_rhr['Z_score'] > 1.5) & (dzienne_rhr['Z_score'] <= 2.0)).astype(int)
else:
    dzienne_rhr = pd.DataFrame(
        columns=['Data', 'Nocne tętno (bpm)', 'Baseline', 'Odchylenie', 'Z_score', 'Anomalia', 'Prawie_anomalia'])

# 5. ŁĄCZENIE (Twój stary styl, dodane tylko łączenie z dzienne_rhr)
tabela_danych = pd.merge(tabela_aktywnosc, tabela_sen, on='Data', how='outer')
tabela_danych = pd.merge(tabela_danych, dzienne_rhr, on='Data',
                         how='outer')  # Doklejamy tętno na podstawie tekstu z Data

tabela_danych['Czas snu (min)'] = tabela_danych['czas_snu'] // 60
tabela_danych['Punkty kardio'] = tabela_danych['Punkty kardio'].fillna(0)
tabela_danych['Minuty intensywnego treningu'] = tabela_danych['Minuty intensywnego treningu'].fillna(0)

# Dopiero po wszystkich merge'ach zamieniamy tekst w dacie na datetime (tak jak było u Ciebie)
tabela_danych['Data'] = pd.to_datetime(tabela_danych['Data'])
tabela_danych = tabela_danych.sort_values(by='Data').reset_index(drop=True)
tabela_danych['Średnia waga (kg)'] = tabela_danych['Średnia waga (kg)'].interpolate(method='linear')

sensowne_kolumny = [
    'Data', 'Liczba kroków', 'Kalorie (kcal)', 'Odległość (m)', 'Punkty kardio',
    'Minuty intensywnego treningu', 'Średnie tętno (bpm)', 'Nocne tętno (bpm)',  # Nowa kolumna
    'Baseline', 'Odchylenie', 'Z_score', 'Anomalia', 'Prawie_anomalia',  # Nowe kolumny z algorytmu
    'Najwyższe tętno (bpm)', 'Średnia waga (kg)', 'Liczba minut ruchu',
    'Średnie wysycenie tlenem (%)', 'Czas snu (min)'
]


dostepne_kolumny = [kol for kol in sensowne_kolumny if kol in tabela_danych.columns]
tabela_danych = tabela_danych[dostepne_kolumny]

def rysuj_wykres_rhr(dane, data_od, data_do):
    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    data_od = pd.to_datetime(data_od)
    data_do = pd.to_datetime(data_do)

    czyste_dane = dane[(dane['Data'] >= data_od) & (dane['Data'] <= data_do)].dropna(
        subset=['Nocne tętno (bpm)', 'Baseline']).sort_values('Data')

    if czyste_dane.empty:
        print("Brak danych w wybranym zakresie.")
        return None

    czyste_dane['Data_tekst'] = czyste_dane['Data'].dt.strftime('%Y-%m-%d')
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Nocne tętno (bpm)'], label='Nocne tętno (bpm)', marker='o',
            color='tab:blue', zorder=3, alpha=0.6)
    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Baseline'], label='Linia bazowa (28 dni)', color='green', zorder=2,
            linewidth=2)

    aberracje = czyste_dane[czyste_dane['Anomalia'] == 1]
    if not aberracje.empty:
        ax.scatter(aberracje['Data_tekst'], aberracje['Nocne tętno (bpm)'], color='red', s=100, zorder=5,
                   label='Anomalia (>2 odchylenia)')

    ostrzezenia = czyste_dane[czyste_dane['Prawie_anomalia'] == 1]
    if not ostrzezenia.empty:
        ax.scatter(ostrzezenia['Data_tekst'], ostrzezenia['Nocne tętno (bpm)'], color='orange', s=80, zorder=4,
                   label='Ostrzeżenie (1.5-2.0 odchylenia)')

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Nocne tętno (bpm)')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    ax.legend()
    plt.title('Wykrywanie fizjologicznych anomalii (wzór RHR-Diff)')
    plt.tight_layout()
    plt.show()
    return fig


def szereg_czasowy_kroki_tetno(dane, data_od, data_do):
    df = dane.copy()
    df['Data'] = pd.to_datetime(df['Data'])
    df = df[(df['Data'] >= data_od) & (df['Data'] <= data_do)]
    df = df.dropna(subset=['Liczba kroków', 'Nocne tętno (bpm)'])

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(df['Data'], df['Liczba kroków'], color='gray', alpha=0.3, label='Kroki')
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Liczba kroków', color='gray')
    ax1.tick_params(axis='y', labelcolor='gray')

    ax2 = ax1.twinx()
    ax2.plot(df['Data'], df['Nocne tętno (bpm)'], color='tab:red', linewidth=2, label='Tętno nocne')
    ax2.set_ylabel('Nocne tętno (bpm)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    fig.autofmt_xdate()
    plt.title('Szereg czasowy: Aktywność dzienna vs Regeneracja nocna')
    fig.tight_layout()
    plt.show()


# TESTY
parametry_do_badania = [
    'Liczba kroków', 'Kalorie (kcal)', 'Odległość (m)', 'Punkty kardio',
    'Minuty intensywnego treningu', 'Nocne tętno (bpm)',  # Zaktualizowana lista o nocne tętno
    'Średnia waga (kg)', 'Czas snu (min)'
]


rysuj_wykres_rhr(tabela_danych, data_od='2026-01-01', data_do='2026-08-30')
szereg_czasowy_kroki_tetno(tabela_danych, data_od='2026-01-01', data_do='2026-08-30')

# weryfikacja
print("\n=== WYKRYTE ANOMALIE (> 2 odchylenia standardowe) ===")
tabela_anomalii = tabela_danych[tabela_danych['Anomalia'] == 1]

for index, wiersz in tabela_anomalii.iterrows():
    print(f"Data: {wiersz['Data'].strftime('%Y-%m-%d')} | Tętno: {wiersz['Nocne tętno (bpm)']:.1f} bpm | Norma: {wiersz['Baseline']:.1f} bpm | Skok o {wiersz['Z_score']:.2f} std")

print("\n=== STANY OSTRZEGAWCZE (1.5 - 2.0 odchylenia standardowe) ===")
tabela_ostrzezen = tabela_danych[tabela_danych['Prawie_anomalia'] == 1]

for index, wiersz in tabela_ostrzezen.iterrows():
    print(f"Data: {wiersz['Data'].strftime('%Y-%m-%d')} | Tętno: {wiersz['Nocne tętno (bpm)']:.1f} bpm | Norma: {wiersz['Baseline']:.1f} bpm | Skok o {wiersz['Z_score']:.2f} std")

def weryfikuj_infekcje(dane, dni_wstecz=14, dni_w_przod=7):
    dane = dane.copy()
    dane['Data'] = pd.to_datetime(dane['Data'])
    anomalie = dane[dane['Anomalia'] == 1]

    print(f"\n=== WERYFIKACJA OBJAWOWA ({dni_w_przod} dni po skoku tętna) ===")

    if anomalie.empty:
        print("Brak anomalii do weryfikacji.")
        return

    for index, wiersz in anomalie.iterrows():
        data_anomalii = wiersz['Data']

        maska_przed = (dane['Data'] >= data_anomalii - pd.Timedelta(days=dni_wstecz)) & (dane['Data'] < data_anomalii)
        okno_przed = dane[maska_przed]

        maska_po = (dane['Data'] >= data_anomalii) & (dane['Data'] <= data_anomalii + pd.Timedelta(days=dni_w_przod))
        okno_po = dane[maska_po]

        if okno_przed.empty or okno_po.empty:
            continue

        kroki_przed = okno_przed['Liczba kroków'].mean()
        kroki_po = okno_po['Liczba kroków'].mean()
        sen_przed = okno_przed['Czas snu (min)'].mean()
        sen_po = okno_po['Czas snu (min)'].mean()

        if pd.isna(kroki_przed) or pd.isna(kroki_po):
            continue

        zmiana_krokow_proc = ((kroki_po - kroki_przed) / kroki_przed) * 100 if kroki_przed > 0 else 0
        zmiana_snu_min = (sen_po - sen_przed) if not pd.isna(sen_przed) and not pd.isna(sen_po) else 0

        is_choroba = (zmiana_krokow_proc <= -25) or (zmiana_snu_min >= 45)
        werdykt = "POTWIERDZONA CHOROBA" if is_choroba else "FAŁSZYWY ALARM"

        print(f"Data: {data_anomalii.strftime('%Y-%m-%d')} | Skok tętna o {wiersz['Z_score']:.2f} std")
        print(f"  -> Kroki: norma {kroki_przed:.0f} -> w trakcie {kroki_po:.0f} ({zmiana_krokow_proc:+.1f}%)")
        if not pd.isna(sen_przed) and not pd.isna(sen_po):
            print(f"  -> Sen: norma {sen_przed:.0f} min -> w trakcie {sen_po:.0f} min ({zmiana_snu_min:+.0f} min)")
        print(f"  -> {werdykt}\n")

# Wywołanie funkcji (tylko raz!)
weryfikuj_infekcje(tabela_danych)