from os import listdir
from json import load
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages


# 1. FUNKCJE (Wykresy, Weryfikacja i Raporty)


def wykres_rhr(dane):
    czyste_dane = dane.dropna(subset=['Nocne tętno (bpm)', 'Baseline_RHR']).sort_values('Data')
    if czyste_dane.empty:
        return None

    czyste_dane['Data_tekst'] = czyste_dane['Data'].dt.strftime('%Y-%m-%d')
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Nocne tętno (bpm)'], label='Nocne tętno (bpm)', marker='o',
            color='tab:blue', zorder=3, alpha=0.6)
    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Baseline_RHR'], label='Średnia krocząca (28 dni)', color='green', zorder=2,
            linewidth=2)

    infekcje_rhr = czyste_dane[czyste_dane['Infekcja_RHR'] == 1]
    ax.scatter(infekcje_rhr['Data_tekst'], infekcje_rhr['Nocne tętno (bpm)'], color='red', s=80, zorder=5,
               label='Infekcja (>2 std)')

    ostrzezenia_rhr = czyste_dane[czyste_dane['Ostrzezenie_RHR'] == 1]
    ax.scatter(ostrzezenia_rhr['Data_tekst'], ostrzezenia_rhr['Nocne tętno (bpm)'], color='orange', s=60, zorder=4,
               label='Ostrzeżenie (1.5-2.0 std)')

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Nocne tętno (bpm)')

    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.xticks(rotation=45)
    ax.legend()
    plt.title('Detekcja infekcji na podstawie nocnego tętna spoczynkowego (RHR)')
    plt.tight_layout()

    return fig


def wykres_hros(dane):
    czyste_dane = dane.dropna(subset=['Z_score_HROS']).sort_values('Data')
    if czyste_dane.empty:
        return None

    czyste_dane['Data_tekst'] = czyste_dane['Data'].dt.strftime('%Y-%m-%d')
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Z_score_HROS'], label='Z-score (HROS)', marker='o',
            color='tab:purple', zorder=3, alpha=0.6)

    ax.axhline(y=1.5, color='orange', linestyle='--', zorder=2, label='Ostrzeżenie (1.5 -2.0 std)')
    ax.axhline(y=2.0, color='red', linestyle='--', zorder=2, label='Infekcja (2.0 std)')

    infekcje_hros = czyste_dane[czyste_dane['Infekcja_HROS'] == 1]
    ax.scatter(infekcje_hros['Data_tekst'], infekcje_hros['Z_score_HROS'], color='red', s=100, zorder=5)

    ostrzezenia_hros = czyste_dane[czyste_dane['Ostrzezenie_HROS'] == 1]
    ax.scatter(ostrzezenia_hros['Data_tekst'], ostrzezenia_hros['Z_score_HROS'], color='orange', s=80, zorder=4)

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Odchylenie (Z-score)')

    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.xticks(rotation=45)
    ax.legend()
    plt.title('Detekcja infekcji metodą HROS (Heart Rate Over Steps)')
    plt.tight_layout()

    return fig


def weryfikuj_objawy(dane, kol_infekcji, kol_ostrzezenia, kol_zscore, nazwa_metody, dni_wstecz=14, dni_w_przod=7):
    zdarzenia = dane[(dane[kol_infekcji] == 1) | (dane[kol_ostrzezenia] == 1)]
    raport = f"=== WERYFIKACJA: {nazwa_metody} ===\n"

    if zdarzenia.empty:
        raport += f"Brak zdarzeń do weryfikacji.\n\n"
        return raport

    for index, wiersz in zdarzenia.iterrows():
        data_zd = wiersz['Data']
        typ_skoku = "INFEKCJA" if wiersz[kol_infekcji] == 1 else "OSTRZEŻENIE"
        z_score_val = wiersz[kol_zscore]

        okno_przed = dane[(dane['Data'] >= data_zd - pd.Timedelta(days=dni_wstecz)) & (dane['Data'] < data_zd)]
        okno_po = dane[(dane['Data'] >= data_zd) & (dane['Data'] <= data_zd + pd.Timedelta(days=dni_w_przod))]

        if okno_przed.empty or okno_po.empty:
            continue

        kroki_przed, kroki_po = okno_przed['Liczba kroków'].mean(), okno_po['Liczba kroków'].mean()
        sen_przed, sen_po = okno_przed['Czas snu (min)'].mean(), okno_po['Czas snu (min)'].mean()

        if pd.isna(kroki_przed) or pd.isna(kroki_po):
            continue

        zmiana_krokow_proc = ((kroki_po - kroki_przed) / kroki_przed) * 100 if kroki_przed > 0 else 0
        zmiana_snu_min = (sen_po - sen_przed) if not pd.isna(sen_przed) and not pd.isna(sen_po) else 0

        is_choroba = (zmiana_krokow_proc <= -20)
        werdykt = "POTWIERDZONA INFEKCJA" if is_choroba else "FAŁSZYWY ALARM"

        raport += f"Data: {data_zd.strftime('%Y-%m-%d')} [{typ_skoku}] | Skok o {z_score_val:.2f} std\n"
        raport += f"  -> Kroki: norma {kroki_przed:.0f} -> w trakcie {kroki_po:.0f} ({zmiana_krokow_proc:+.1f}%)\n"
        if not pd.isna(sen_przed) and not pd.isna(sen_po):
            raport += f"  -> Sen (informacyjnie): norma {sen_przed:.0f} min -> w trakcie {sen_po:.0f} min ({zmiana_snu_min:+.0f} min)\n"
        raport += f"  -> {werdykt}\n\n"

    return raport

def zapisz_raporty(dane, nazwa_csv="Wyniki_Analizy.csv", nazwa_pdf="Raport_Wykresy.pdf"):
    dane.to_csv(nazwa_csv, index=False, encoding='utf-8')

    raport_rhr = weryfikuj_objawy(dane, 'Infekcja_RHR', 'Ostrzezenie_RHR', 'Z_score_RHR', "RHR (Nocne)")
    raport_hros = weryfikuj_objawy(dane, 'Infekcja_HROS', 'Ostrzezenie_HROS', 'Z_score_HROS', "HROS (Kroki)")
    pelny_raport = raport_rhr + raport_hros

    pelny_raport += "=== POTWIERDZONE OBIEMA METODAMI ===\n"
    filtr_RHR = (dane['Infekcja_RHR'] == 1) | (dane['Ostrzezenie_RHR'] == 1)
    filtr_HROS = (dane['Infekcja_HROS'] == 1) | (dane['Ostrzezenie_HROS'] == 1)

    wspolne_infekcje = dane[filtr_RHR & filtr_HROS]
    if wspolne_infekcje.empty:
        pelny_raport += "Brak wspólnych dni.\n"
    else:
        for index, wiersz in wspolne_infekcje.iterrows():
            pelny_raport += f"Data: {wiersz['Data'].strftime('%Y-%m-%d')} - Niepokojący skok w obu algorytmach!\n"

    print(pelny_raport)

    with PdfPages(nazwa_pdf) as pdf:
        fig1 = wykres_rhr(dane)
        if fig1:
            pdf.savefig(fig1)

        fig2 = wykres_hros(dane)
        if fig2:
            pdf.savefig(fig2)

        fig_text = plt.figure(figsize=(10, 8))
        fig_text.clf()
        fig_text.text(0.05, 0.95, pelny_raport, transform=fig_text.transFigure, size=10, family='monospace', va='top')
        pdf.savefig(fig_text)
        plt.close(fig_text)

    print(f"\n[SUKCES] Zapisano dane do: {nazwa_csv}")
    print(f"[SUKCES] Zapisano raport (wykresy + diagnozy) do: {nazwa_pdf}")
    plt.show()

# 2. GŁÓWNA LOGIKA PROGRAMU

#Wczytanie snu
wyniki_snu = []
for nazwa_pliku in listdir('.'):
    if nazwa_pliku.endswith(".json") and "derived" not in nazwa_pliku:
        with open(nazwa_pliku, 'r', encoding='utf-8') as plik:
            dane = load(plik)
            if dane.get("fitnessActivity") == "sleep" and "startTime" in dane and "endTime" in dane and "duration" in dane:
                sekundy_snu = int(dane["duration"][:-1])
                if sekundy_snu >= 7200:
                    wyniki_snu.append({
                        "Data": pd.to_datetime(dane["endTime"].split('T')[0]),
                        "start_pelny": pd.to_datetime(dane["startTime"][:-1]),
                        "koniec_pelny": pd.to_datetime(dane["endTime"][:-1]),
                        "czas_snu": sekundy_snu
                    })
tabela_sen = pd.DataFrame(wyniki_snu)

#Wczytanie tętna
with open('derived_com.google.heart_rate.bpm_com.google.android.gms_merge_heart_rate_bpm.json', 'r', encoding='utf-8') as plik:
    dane_json = load(plik)

lista_tetna = []
for punkt in dane_json.get("Data Points", []):
    try:
        lista_tetna.append({
            "PelnyCzas": pd.to_datetime(int(punkt["startTimeNanos"]) / 1_000_000_000, unit='s'),
            "Tetno": float(punkt["fitValue"][0]["value"]["fpVal"])
        })
    except (KeyError, IndexError, ValueError):
        continue

tabela_tetno = pd.DataFrame(lista_tetna)
tabela_tetno['PelnyCzas'] = tabela_tetno['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert('Europe/Warsaw').dt.tz_localize(None)

#Wczytanie kroków
with open('derived_com.google.step_count.delta_com.google.android.gms_estimated_steps.json', 'r', encoding='utf-8') as plik:
    dane_kroki = load(plik)

lista_krokow = []
for punkt in dane_kroki.get("Data Points", []):
    try:
        lista_krokow.append({
            "PelnyCzas": pd.to_datetime(int(punkt["startTimeNanos"]) / 1_000_000_000, unit='s'),
            "Kroki": punkt["fitValue"][0]["value"]["intVal"]
        })
    except (KeyError, IndexError, ValueError):
        continue

tabela_kroki = pd.DataFrame(lista_krokow)
tabela_kroki['PelnyCzas'] = tabela_kroki['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert('Europe/Warsaw').dt.tz_localize(None)

#Obliczenia: Tętno nocne (RHR)
dane_nocne_lista = []
for index, wiersz in tabela_sen.iterrows():
    maska = (tabela_tetno['PelnyCzas'] >= wiersz['start_pelny']) & (tabela_tetno['PelnyCzas'] <= wiersz['koniec_pelny'])
    tetno_snu = tabela_tetno[maska].copy()
    if not tetno_snu.empty:
        tetno_snu['Data'] = wiersz['Data']
        dane_nocne_lista.append(tetno_snu)

if dane_nocne_lista:
    dzienne_rhr = pd.concat(dane_nocne_lista, ignore_index=True).groupby('Data')['Tetno'].median().reset_index()
    dzienne_rhr.rename(columns={'Tetno': 'Nocne tętno (bpm)'}, inplace=True)

    dzienne_rhr['Baseline_RHR'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).mean()
    dzienne_rhr['Odchylenie_RHR'] = dzienne_rhr['Nocne tętno (bpm)'].rolling(window=28, min_periods=7).std()
    dzienne_rhr['Z_score_RHR'] = (dzienne_rhr['Nocne tętno (bpm)'] - dzienne_rhr['Baseline_RHR']) / dzienne_rhr['Odchylenie_RHR']
    dzienne_rhr['Infekcja_RHR'] = (dzienne_rhr['Z_score_RHR'] > 2.0).astype(int)
    dzienne_rhr['Ostrzezenie_RHR'] = ((dzienne_rhr['Z_score_RHR'] > 1.5) & (dzienne_rhr['Z_score_RHR'] <= 2.0)).astype(int)
else:
    dzienne_rhr = pd.DataFrame(
        columns=['Data', 'Nocne tętno (bpm)', 'Baseline_RHR', 'Odchylenie_RHR', 'Z_score_RHR', 'Infekcja_RHR', 'Ostrzezenie_RHR'])

#Obliczenia: Kroki
tabela_kroki['Data'] = tabela_kroki['PelnyCzas'].dt.normalize()
dzienne_kroki = tabela_kroki.groupby('Data')['Kroki'].sum().reset_index()
dzienne_kroki.rename(columns={'Kroki': 'Liczba kroków'}, inplace=True)

#Obliczenia: Algorytm HROS
kroki_15m = tabela_kroki.set_index('PelnyCzas')[['Kroki']].resample('15min').sum()
tetno_15m = tabela_tetno.set_index('PelnyCzas')[['Tetno']].resample('15min').mean()
tabela_hros = pd.merge(kroki_15m, tetno_15m, left_index=True, right_index=True, how='inner')
tabela_hros = tabela_hros[tabela_hros['Kroki'] > 10].copy()

przedzialy = [10, 100, 300, 500, 1000, np.inf]
etykiety = ['Bardzo lekki', 'Lekki', 'Umiarkowany', 'Intensywny', 'Bardzo intensywny']
tabela_hros['Koszyk'] = pd.cut(tabela_hros['Kroki'], bins=przedzialy, labels=etykiety)
tabela_hros = tabela_hros.sort_index()

def licz_normy_koszyka(grupa):
    grupa['Baseline_HR'] = grupa['Tetno'].rolling('28D', min_periods=7).mean()
    grupa['Std_HR'] = grupa['Tetno'].rolling('28D', min_periods=7).std()
    return grupa

tabela_hros = tabela_hros.groupby('Koszyk', observed=True, group_keys=False).apply(licz_normy_koszyka)
tabela_hros['Z_score_15m'] = (tabela_hros['Tetno'] - tabela_hros['Baseline_HR']) / tabela_hros['Std_HR']
tabela_hros['Data'] = tabela_hros.index.normalize()

dzienne_hros = tabela_hros.groupby('Data')['Z_score_15m'].mean().reset_index()
dzienne_hros.rename(columns={'Z_score_15m': 'Z_score_HROS'}, inplace=True)

#Łączenie w ostateczną bazę
baza_danych = pd.merge(tabela_sen, dzienne_rhr, on='Data', how='outer')
baza_danych = pd.merge(baza_danych, dzienne_hros, on='Data', how='outer')
baza_danych = pd.merge(baza_danych, dzienne_kroki, on='Data', how='outer')

baza_danych['Czas snu (min)'] = baza_danych['czas_snu'] // 60
baza_danych['Data'] = pd.to_datetime(baza_danych['Data'])
baza_danych = baza_danych.sort_values(by='Data').reset_index(drop=True)

baza_danych['Infekcja_HROS'] = (baza_danych['Z_score_HROS'] > 2.0).astype(int)
baza_danych['Ostrzezenie_HROS'] = ((baza_danych['Z_score_HROS'] > 1.5) & (baza_danych['Z_score_HROS'] <= 2.0)).astype(int)

# Oczyszczanie kolumn
sensowne_kolumny = [
    'Data', 'Liczba kroków', 'Czas snu (min)', 'Nocne tętno (bpm)',
    'Baseline_RHR', 'Odchylenie_RHR', 'Z_score_RHR', 'Infekcja_RHR', 'Ostrzezenie_RHR',
    'Z_score_HROS', 'Infekcja_HROS', 'Ostrzezenie_HROS'
]
baza_danych = baza_danych[[kol for kol in sensowne_kolumny if kol in baza_danych.columns]]

#FILTROWANIE PO DACIE

data_od = '2025-01-01'
data_do = '2026-12-31'

baza_do_raportu = baza_danych.copy()

if data_od:
    baza_do_raportu = baza_do_raportu[baza_do_raportu['Data'] >= pd.to_datetime(data_od)]
if data_do:
    baza_do_raportu = baza_do_raportu[baza_do_raportu['Data'] <= pd.to_datetime(data_do)]

#Zabezpieczenie przed pustym wynikiem
if baza_do_raportu.empty:
    print("Brak danych w wybranym przedziale czasowym!")
else:
    #Uruchomienie eksportu na przefiltrowanych danych
    zapisz_raporty(baza_do_raportu)