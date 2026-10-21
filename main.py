import os
from json import load
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_pdf import PdfPages
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkcalendar import DateEntry
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.ttk as ttk

# Ustawienia wyglądu GUI
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ==========================================
# 1. FUNKCJE POMOCNICZE (Wykresy i Raporty)
# ==========================================

def przygotuj_dane_do_wykresu(dane, kolumny_subset):
    czyste_dane = dane.dropna(subset=kolumny_subset).sort_values('Data').copy()
    if czyste_dane.empty:
        return czyste_dane

    nowe_wiersze = []
    for i in range(len(czyste_dane)):
        wiersz = czyste_dane.iloc[i]
        if i > 0:
            poprzedni_wiersz = czyste_dane.iloc[i - 1]
            roznica_dni = (wiersz['Data'] - poprzedni_wiersz['Data']).days
            if roznica_dni > 3:
                wiersz_nan = wiersz.copy()
                wiersz_nan['Data'] = poprzedni_wiersz['Data'] + pd.Timedelta(days=1)
                for kol in kolumny_subset:
                    if kol in wiersz_nan:
                        wiersz_nan[kol] = np.nan
                for kol_flaga in ['Infekcja_RHR', 'Ostrzezenie_RHR', 'Infekcja_HROS', 'Ostrzezenie_HROS']:
                    if kol_flaga in wiersz_nan:
                        wiersz_nan[kol_flaga] = 0
                nowe_wiersze.append(wiersz_nan)
        nowe_wiersze.append(wiersz)

    wynik = pd.DataFrame(nowe_wiersze).sort_values('Data')
    wynik['Data_tekst'] = wynik['Data'].dt.strftime('%Y-%m-%d')
    return wynik


def wykres_rhr(dane):
    czyste_dane = przygotuj_dane_do_wykresu(dane, ['Nocne tętno (bpm)', 'Baseline_RHR'])
    if czyste_dane.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Nocne tętno (bpm)'], label='Nocne tętno (bpm)', marker='o',
            color='tab:blue', zorder=3, alpha=0.6)
    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Baseline_RHR'], label='Średnia krocząca (28 dni)', color='green',
            zorder=2, linewidth=2)

    infekcje_rhr = czyste_dane[czyste_dane['Infekcja_RHR'] == 1]
    ax.scatter(infekcje_rhr['Data_tekst'], infekcje_rhr['Nocne tętno (bpm)'], color='red', s=20, zorder=5,
               label='Infekcja (>2 std)')

    ostrzezenia_rhr = czyste_dane[czyste_dane['Ostrzezenie_RHR'] == 1]
    ax.scatter(ostrzezenia_rhr['Data_tekst'], ostrzezenia_rhr['Nocne tętno (bpm)'], color='orange', s=20, zorder=4,
               label='Ostrzeżenie (1.5-2.0 std)')

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Nocne tętno (bpm)', labelpad=2)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.xticks(rotation=45)
    ax.legend(fontsize='small')
    plt.title('Detekcja infekcji na podstawie nocnego tętna spoczynkowego (RHR)')

    plt.tight_layout(pad=2.0)
    return fig


def wykres_hros(dane):
    czyste_dane = przygotuj_dane_do_wykresu(dane, ['Z_score_HROS'])
    if czyste_dane.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(czyste_dane['Data_tekst'], czyste_dane['Z_score_HROS'], label='Wskaźnik anomalii HROS', marker='o',
            color='tab:purple', zorder=3, alpha=0.6)

    ax.axhline(y=1.5, color='orange', linestyle='--', zorder=2, label='Ostrzeżenie (1.5-2.0 std)')
    ax.axhline(y=2.0, color='red', linestyle='--', zorder=2, label='Infekcja (>2 std)')

    infekcje_hros = czyste_dane[czyste_dane['Infekcja_HROS'] == 1]
    ax.scatter(infekcje_hros['Data_tekst'], infekcje_hros['Z_score_HROS'], color='red', s=20, zorder=5)

    ostrzezenia_hros = czyste_dane[czyste_dane['Ostrzezenie_HROS'] == 1]
    ax.scatter(ostrzezenia_hros['Data_tekst'], ostrzezenia_hros['Z_score_HROS'], color='orange', s=20, zorder=4)

    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    ax.set_xlabel('Data')
    ax.set_ylabel('Poziom anomalii', labelpad=2)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=15))
    plt.xticks(rotation=45)
    ax.legend()
    plt.title('Detekcja infekcji metodą HROS (Tylko w spoczynku)')

    plt.tight_layout(pad=2.0)
    return fig


def wykres_heatmap(dane):
    if dane.empty:
        return None

    d = dane.copy()

    d['Tydzien'] = d['Data'].dt.to_period('W').apply(lambda r: r.start_time)
    agregacja = d.groupby('Tydzien').agg({
        'Gestosc_HR': 'sum',
        'Gestosc_Kroki': 'sum',
        'Czas snu (min)': 'sum'
    }).reset_index()

    daty = agregacja['Tydzien'].dt.strftime('%Y-%m-%d').tolist()

    hr = agregacja['Gestosc_HR'].fillna(0).values
    kroki = agregacja['Gestosc_Kroki'].fillna(0).values
    sen = agregacja['Czas snu (min)'].fillna(0).values

    hr_norm = hr / hr.max() if hr.max() > 0 else hr
    kroki_norm = kroki / kroki.max() if kroki.max() > 0 else kroki
    sen_norm = sen / sen.max() if sen.max() > 0 else sen

    matrix = np.vstack((hr_norm, kroki_norm, sen_norm))

    fig, ax = plt.subplots(figsize=(10, 4))

    kolory_mapy = LinearSegmentedColormap.from_list('dostepnosc', ['#111111', '#e8cc17', '#28a821'])
    cax = ax.imshow(matrix, aspect='auto', cmap=kolory_mapy, interpolation='nearest', vmin=0, vmax=1)

    cbar = fig.colorbar(cax, ticks=[0, 0.5, 1], orientation='vertical')
    cbar.ax.set_yticklabels(['Brak danych', 'Częściowa', 'Pełna'])

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['Tętno (pom.)', 'Kroki (pom.)', 'Sen (czas)'])

    num_dates = len(daty)
    step = max(1, num_dates // 15)
    ax.set_xticks(np.arange(0, num_dates, step))
    ax.set_xticklabels([daty[i] for i in range(0, num_dates, step)], rotation=45, ha='right')

    plt.title('Heatmapa dostępności danych')
    plt.tight_layout()
    return fig


def weryfikuj_objawy(dane, kol_infekcji, kol_ostrzezenia, kol_zscore, nazwa_metody, dni_wstecz=14, dni_w_przod=7,
                     pomin_falszywe=False):
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

        if pomin_falszywe and not is_choroba:
            continue

        raport += f"Data: {data_zd.strftime('%Y-%m-%d')} [{typ_skoku}] | Wskaźnik: {z_score_val:.2f}\n"
        raport += f"  -> Kroki: norma {kroki_przed:.0f} -> w trakcie {kroki_po:.0f} ({zmiana_krokow_proc:+.1f}%)\n"
        if not pd.isna(sen_przed) and not pd.isna(sen_po):
            raport += f"  -> Sen (informacyjnie): norma {sen_przed:.0f} min -> w trakcie {sen_po:.0f} min ({zmiana_snu_min:+.0f} min)\n"
        raport += f"  -> {werdykt}\n\n"

    return raport


# ==========================================
# 2. GŁÓWNA LOGIKA
# ==========================================

def generuj_tekst_raportu(dane, pomin_falszywe=False):
    raport_rhr = weryfikuj_objawy(dane, 'Infekcja_RHR', 'Ostrzezenie_RHR', 'Z_score_RHR', "RHR (Nocne)",
                                  pomin_falszywe=pomin_falszywe)
    raport_hros = weryfikuj_objawy(dane, 'Infekcja_HROS', 'Ostrzezenie_HROS', 'Z_score_HROS', "HROS (Kroki)",
                                   pomin_falszywe=pomin_falszywe)
    pelny_raport = raport_rhr + raport_hros

    pelny_raport += "=== POTWIERDZONE OBIEMA METODAMI ===\n"

    filtr_RHR = (dane['Infekcja_RHR'] == 1) | (dane['Ostrzezenie_RHR'] == 1)
    filtr_HROS = (dane['Infekcja_HROS'] == 1) | (dane['Ostrzezenie_HROS'] == 1)
    wspolne_infekcje = dane[filtr_RHR & filtr_HROS]

    if wspolne_infekcje.empty:
        pelny_raport += "Brak wspólnych dni.\n"
    else:
        for index, wiersz in wspolne_infekcje.iterrows():
            data_zd = wiersz['Data']
            okno_przed = dane[(dane['Data'] >= data_zd - pd.Timedelta(days=14)) & (dane['Data'] < data_zd)]
            okno_po = dane[(dane['Data'] >= data_zd) & (dane['Data'] <= data_zd + pd.Timedelta(days=7))]

            is_choroba = False
            if not okno_przed.empty and not okno_po.empty:
                kroki_przed = okno_przed['Liczba kroków'].mean()
                kroki_po = okno_po['Liczba kroków'].mean()
                if pd.notna(kroki_przed) and pd.notna(kroki_po) and kroki_przed > 0:
                    spadek_proc = ((kroki_po - kroki_przed) / kroki_przed) * 100
                    if spadek_proc <= -20:
                        is_choroba = True

            if pomin_falszywe and not is_choroba:
                continue

            werdykt = "POTWIERDZONA INFEKCJA" if is_choroba else "FAŁSZYWY ALARM (brak spadku aktywności)"
            pelny_raport += f"Data: {data_zd.strftime('%Y-%m-%d')} | Zgodność obu wskaźników\n  -> {werdykt}\n\n"

    return pelny_raport


def wczytaj_surowe_dane(folder_fit):
    folder_sen = None
    folder_aktywnosc = None

    mozliwe_katalogi_sen = ["Wszystkie sesje", "All Sessions"]
    mozliwe_katalogi_akt = ["Wszystkie dane", "All Data"]

    for nazwa in mozliwe_katalogi_sen:
        sciezka = os.path.join(folder_fit, nazwa)
        if os.path.isdir(sciezka):
            folder_sen = sciezka
            break

    for nazwa in mozliwe_katalogi_akt:
        sciezka = os.path.join(folder_fit, nazwa)
        if os.path.isdir(sciezka):
            folder_aktywnosc = sciezka
            break

    if not folder_sen or not folder_aktywnosc:
        raise FileNotFoundError(
            "Nie odnaleziono wymaganej struktury w folderze 'Fit'.\n"
            "Upewnij się, że wskazałeś główny folder 'Fit' pobrany z Google Takeout, "
            "który zawiera podfoldery 'Wszystkie sesje'/'All Sessions' oraz 'Wszystkie dane'/'All Data'."
        )

    wyniki_snu = []
    for nazwa_pliku in os.listdir(folder_sen):
        if nazwa_pliku.endswith(".json") and "derived" not in nazwa_pliku:
            with open(os.path.join(folder_sen, nazwa_pliku), 'r', encoding='utf-8') as plik:
                dane = load(plik)
                if dane.get(
                        "fitnessActivity") == "sleep" and "startTime" in dane and "endTime" in dane and "duration" in dane:
                    sekundy_snu = int(dane["duration"][:-1])
                    if sekundy_snu >= 7200:
                        wyniki_snu.append({
                            "Data": pd.to_datetime(dane["endTime"].split('T')[0]),
                            "start_pelny": pd.to_datetime(dane["startTime"][:-1]),
                            "koniec_pelny": pd.to_datetime(dane["endTime"][:-1]),
                            "czas_snu": sekundy_snu
                        })
    tabela_sen = pd.DataFrame(wyniki_snu)
    if not tabela_sen.empty:
        tabela_sen = tabela_sen.drop_duplicates().reset_index(drop=True)

    sciezka_tetno = os.path.join(folder_aktywnosc,
                                 'derived_com.google.heart_rate.bpm_com.google.android.gms_merge_heart_rate_bpm.json')
    if not os.path.exists(sciezka_tetno):
        raise FileNotFoundError(f"Brak pliku tętna w {folder_aktywnosc}")

    with open(sciezka_tetno, 'r', encoding='utf-8') as plik:
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
    tabela_tetno['PelnyCzas'] = tabela_tetno['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert(
        'Europe/Warsaw').dt.tz_localize(None)
    tabela_tetno = tabela_tetno.drop_duplicates(subset=['PelnyCzas']).reset_index(drop=True)
    tabela_tetno['Data'] = tabela_tetno['PelnyCzas'].dt.normalize()

    sciezka_kroki = os.path.join(folder_aktywnosc,
                                 'derived_com.google.step_count.delta_com.google.android.gms_estimated_steps.json')
    if not os.path.exists(sciezka_kroki):
        raise FileNotFoundError(f"Brak pliku kroków w {folder_aktywnosc}")

    with open(sciezka_kroki, 'r', encoding='utf-8') as plik:
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
    tabela_kroki['PelnyCzas'] = tabela_kroki['PelnyCzas'].dt.tz_localize('UTC').dt.tz_convert(
        'Europe/Warsaw').dt.tz_localize(None)
    tabela_kroki = tabela_kroki.drop_duplicates(subset=['PelnyCzas']).reset_index(drop=True)
    tabela_kroki['Data'] = tabela_kroki['PelnyCzas'].dt.normalize()

    return tabela_sen, tabela_tetno, tabela_kroki


def uruchom_analize_z_cache(tabela_sen, tabela_tetno, tabela_kroki, data_od, data_do, pomin_falszywe=False):
    liczba_hr = tabela_tetno.groupby('Data').size().reset_index(name='Gestosc_HR')
    dzienne_hr = tabela_tetno.groupby('Data')['Tetno'].mean().reset_index(name='Srednie_dzienne_HR')
    liczba_kroki = tabela_kroki.groupby('Data').size().reset_index(name='Gestosc_Kroki')

    dane_nocne_lista = []
    for index, wiersz in tabela_sen.iterrows():
        maska = (tabela_tetno['PelnyCzas'] >= wiersz['start_pelny']) & (
                    tabela_tetno['PelnyCzas'] <= wiersz['koniec_pelny'])
        tetno_snu = tabela_tetno[maska].copy()

        if len(tetno_snu) > 60:
            dolny_prog = tetno_snu['Tetno'].quantile(0.05)
            gorny_prog = tetno_snu['Tetno'].quantile(0.95)
            czyste_tetno = tetno_snu[(tetno_snu['Tetno'] >= dolny_prog) & (tetno_snu['Tetno'] <= gorny_prog)].copy()
            czyste_tetno['Data'] = wiersz['Data']
            dane_nocne_lista.append(czyste_tetno)

    if dane_nocne_lista:
        dzienne_rhr = pd.concat(dane_nocne_lista, ignore_index=True).groupby('Data')['Tetno'].median().reset_index()
        dzienne_rhr.rename(columns={'Tetno': 'Nocne tętno (bpm)'}, inplace=True)
        dzienne_rhr.set_index('Data', inplace=True)

        base_temp = dzienne_rhr['Nocne tętno (bpm)'].rolling('28D', min_periods=14).mean()
        std_temp = dzienne_rhr['Nocne tętno (bpm)'].rolling('28D', min_periods=14).std().clip(lower=1.0)

        z_temp = (dzienne_rhr['Nocne tętno (bpm)'] - base_temp) / std_temp
        czyste_tetno_rhr = dzienne_rhr['Nocne tętno (bpm)'].mask(z_temp > 2.0)

        dzienne_rhr['Baseline_RHR'] = czyste_tetno_rhr.rolling('28D', min_periods=14).mean()
        dzienne_rhr['Odchylenie_RHR'] = czyste_tetno_rhr.rolling('28D', min_periods=14).std().clip(lower=1.0)
        dzienne_rhr.reset_index(inplace=True)

        dzienne_rhr['Z_score_RHR'] = (dzienne_rhr['Nocne tętno (bpm)'] - dzienne_rhr['Baseline_RHR']) / dzienne_rhr[
            'Odchylenie_RHR']
        dzienne_rhr['Infekcja_RHR'] = (dzienne_rhr['Z_score_RHR'] > 2.0).astype(int)
        dzienne_rhr['Ostrzezenie_RHR'] = (
                    (dzienne_rhr['Z_score_RHR'] > 1.5) & (dzienne_rhr['Z_score_RHR'] <= 2.0)).astype(int)
    else:
        dzienne_rhr = pd.DataFrame(
            columns=['Data', 'Nocne tętno (bpm)', 'Baseline_RHR', 'Odchylenie_RHR', 'Z_score_RHR', 'Infekcja_RHR',
                     'Ostrzezenie_RHR'])

    dzienne_kroki = tabela_kroki.groupby('Data')['Kroki'].sum().reset_index()
    dzienne_kroki.rename(columns={'Kroki': 'Liczba kroków'}, inplace=True)

    kroki_15m = tabela_kroki.set_index('PelnyCzas')[['Kroki']].resample('15min').sum()
    tetno_15m = tabela_tetno.set_index('PelnyCzas')[['Tetno']].resample('15min').mean()
    tabela_hros = pd.merge(kroki_15m, tetno_15m, left_index=True, right_index=True, how='inner')
    tabela_hros = tabela_hros[tabela_hros['Kroki'] > 10].copy()

    przedzialy = [10, 100, 300, 500, 1000, np.inf]
    etykiety = ['Bardzo lekki', 'Lekki', 'Umiarkowany', 'Intensywny', 'Bardzo intensywny']
    tabela_hros['Koszyk'] = pd.cut(tabela_hros['Kroki'], bins=przedzialy, labels=etykiety)
    tabela_hros = tabela_hros.sort_index()

    tabela_hros_spoczynek = tabela_hros[tabela_hros['Koszyk'] == 'Bardzo lekki'].copy()

    def licz_normy_koszyka(grupa):
        b_temp = grupa['Tetno'].rolling('28D', min_periods=14).mean()
        s_temp = grupa['Tetno'].rolling('28D', min_periods=14).std().clip(lower=1.0)
        z_temp = (grupa['Tetno'] - b_temp) / s_temp

        czyste_hr = grupa['Tetno'].mask(z_temp > 2.0)
        grupa['Baseline_HR'] = czyste_hr.rolling('28D', min_periods=14).mean()
        grupa['Std_HR'] = czyste_hr.rolling('28D', min_periods=14).std().clip(lower=1.0)
        return grupa

    if not tabela_hros_spoczynek.empty:
        tabela_hros_spoczynek = tabela_hros_spoczynek.groupby('Koszyk', observed=True, group_keys=False).apply(
            licz_normy_koszyka)
        tabela_hros_spoczynek['Z_score_15m'] = (tabela_hros_spoczynek['Tetno'] - tabela_hros_spoczynek['Baseline_HR']) / \
                                               tabela_hros_spoczynek['Std_HR']
        tabela_hros_spoczynek['Anomalia_15m'] = (tabela_hros_spoczynek['Z_score_15m'] > 2.0).astype(int)
        tabela_hros_spoczynek['Data'] = tabela_hros_spoczynek.index.normalize()

        dzienne_hros = tabela_hros_spoczynek.groupby('Data')['Anomalia_15m'].mean().reset_index()
        dzienne_hros.rename(columns={'Anomalia_15m': 'Procent_anomalii_HROS'}, inplace=True)
        dzienne_hros['Z_score_HROS'] = dzienne_hros['Procent_anomalii_HROS'] * 10
    else:
        dzienne_hros = pd.DataFrame(columns=['Data', 'Procent_anomalii_HROS', 'Z_score_HROS'])

    baza_danych = pd.merge(tabela_sen, dzienne_rhr, on='Data', how='outer')
    baza_danych = pd.merge(baza_danych, dzienne_hros, on='Data', how='outer')
    baza_danych = pd.merge(baza_danych, dzienne_kroki, on='Data', how='outer')
    baza_danych = pd.merge(baza_danych, dzienne_hr, on='Data', how='outer')
    baza_danych = pd.merge(baza_danych, liczba_hr, on='Data', how='outer')
    baza_danych = pd.merge(baza_danych, liczba_kroki, on='Data', how='outer')

    baza_danych['Czas snu (min)'] = baza_danych['czas_snu'] // 60
    baza_danych['Data'] = pd.to_datetime(baza_danych['Data'])
    baza_danych = baza_danych.sort_values(by='Data').reset_index(drop=True)

    baza_danych['Infekcja_HROS'] = (baza_danych['Z_score_HROS'] >= 2.0).astype(int)
    baza_danych['Ostrzezenie_HROS'] = (
                (baza_danych['Z_score_HROS'] >= 1.5) & (baza_danych['Z_score_HROS'] < 2.0)).astype(int)

    sensowne_kolumny = [
        'Data', 'Liczba kroków', 'Czas snu (min)', 'Nocne tętno (bpm)',
        'Baseline_RHR', 'Odchylenie_RHR', 'Srednie_dzienne_HR', 'Z_score_RHR', 'Infekcja_RHR', 'Ostrzezenie_RHR',
        'Z_score_HROS', 'Infekcja_HROS', 'Ostrzezenie_HROS', 'Gestosc_HR', 'Gestosc_Kroki'
    ]
    baza_danych = baza_danych[[kol for kol in sensowne_kolumny if kol in baza_danych.columns]]

    baza_pelna = baza_danych.copy()
    baza_do_raportu = baza_danych.copy()

    if data_od:
        baza_do_raportu = baza_do_raportu[baza_do_raportu['Data'] >= pd.to_datetime(data_od)]
    if data_do:
        baza_do_raportu = baza_do_raportu[baza_do_raportu['Data'] <= pd.to_datetime(data_do)]

    raport_tekstowy = generuj_tekst_raportu(baza_do_raportu, pomin_falszywe)

    return baza_pelna, baza_do_raportu, raport_tekstowy


def stylizuj_tabele():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                    background="#2b2b2b",
                    foreground="white",
                    fieldbackground="#2b2b2b",
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background="#1f1f1f",
                    foreground="white",
                    relief="flat",
                    font=("Arial", 10, "bold"))
    style.map("Treeview",
              background=[('selected', '#1f538d')],
              foreground=[('selected', 'white')])


# ==========================================
# 3. INTERFEJS GRAFICZNY (GUI)
# ==========================================

class Aplikacja(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wykrywanie infekcji na podstawie tętna (RHR & HROS)")
        self.geometry("1300x750")

        stylizuj_tabele()

        self.folder_fit_sciezka = ""

        self.cache_sen = None
        self.cache_tetno = None
        self.cache_kroki = None

        self.pelna_baza = None
        self.zapisana_baza = None

        self.zapisany_raport_tekst = ""
        self.fig_rhr = None
        self.fig_hros = None

        self.frame_folder = ctk.CTkFrame(self)
        self.frame_folder.pack(pady=10, padx=20, fill="x")

        self.btn_folder_fit = ctk.CTkButton(self.frame_folder, text="Wybierz folder Fit",
                                            command=self.wybierz_folder_fit)
        self.btn_folder_fit.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.label_folder_fit = ctk.CTkLabel(self.frame_folder, text="Brak wybranego folderu",
                                             text_color="gray")
        self.label_folder_fit.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.frame_daty = ctk.CTkFrame(self)
        self.frame_daty.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.frame_daty, text="Data od:").pack(side="left", padx=10, pady=10)
        self.kalendarz_od = DateEntry(self.frame_daty, width=12, background='black', foreground='white', borderwidth=2,
                                      date_pattern='y-mm-dd')
        self.kalendarz_od.pack(side="left", padx=5)

        ctk.CTkLabel(self.frame_daty, text="Data do:").pack(side="left", padx=10, pady=10)
        self.kalendarz_do = DateEntry(self.frame_daty, width=12, background='black', foreground='white', borderwidth=2,
                                      date_pattern='y-mm-dd')
        self.kalendarz_do.pack(side="left", padx=5)

        self.ukryj_falszywe_var = ctk.IntVar(value=1)

        self.check_falszywe = ctk.CTkCheckBox(self.frame_daty, text="Ukryj fałszywe alarmy",
                                              variable=self.ukryj_falszywe_var)
        self.check_falszywe.pack(side="left", padx=10, pady=10)

        self.btn_skanuj = ctk.CTkButton(self.frame_daty, text="Sprawdź dane", command=self.sprawdz_dane,
                                        fg_color="#d97706", hover_color="#b45309")
        self.btn_skanuj.pack(side="left", padx=10, pady=10)

        self.btn_analizuj = ctk.CTkButton(self.frame_daty, text="Uruchom analizę", command=self.start_analizy,
                                          fg_color="#7a0099", hover_color="#5c0073")
        self.btn_analizuj.pack(side="left", padx=10, pady=10)

        self.btn_zapisz = ctk.CTkButton(self.frame_daty, text="Generuj PDF/CSV", command=self.generuj_pliki,
                                        fg_color="green", state="disabled")
        self.btn_zapisz.pack(side="right", padx=10, pady=10)

        self.btn_heatmap = ctk.CTkButton(self.frame_daty, text="Pokaż dane źródłowe", command=self.pokaz_okno_danych,
                                         fg_color="#0055ff", state="disabled")
        self.btn_heatmap.pack(side="right", padx=10, pady=10)

        self.frame_dolny = ctk.CTkFrame(self)
        self.frame_dolny.pack(pady=10, padx=20, fill="both", expand=True)

        self.frame_tekst = ctk.CTkFrame(self.frame_dolny, fg_color="transparent")
        self.frame_tekst.pack(side="left", fill="y", padx=(0, 10))
        self.label_raport = ctk.CTkLabel(self.frame_tekst, text="Podsumowanie diagnostyczne:")
        self.label_raport.pack(pady=(0, 5), anchor="w")

        self.pole_tekstowe = ctk.CTkTextbox(self.frame_tekst, width=450, font=("Consolas", 12), wrap="word")
        self.pole_tekstowe.pack(fill="y", expand=True)

        instrukcja_powitalna = (
            "Instrukcja:\n"
            "1. Wskaż lokalizację folderu \"Fit\" (znajduje się w katalogu utworzonym po rozpakowaniu archiwum pobranego z Google Takeout).\n"
            "2. Kliknij 'Sprawdź dane', aby wczytać pliki, sprawdzić zakres dostępnych dat i uaktywnić podgląd danych źródłowych, lub od razu wybierz zakres dat w kalendarzu i kliknij 'Uruchom analizę', aby sprawdzić wyniki.\n"
            "3. Pamiętaj, że zaznaczenie lub odznaczenie opcji 'Ukryj fałszywe alarmy' musi nastąpić przed kliknięciem 'Uruchom analizę'."
        )
        self.pole_tekstowe.insert("1.0", instrukcja_powitalna)

        self.zakladki = ctk.CTkTabview(self.frame_dolny)
        self.zakladki.pack(side="right", fill="both", expand=True)

        self.tab_dane = self.zakladki.add("Dane")
        self.tab_rhr = self.zakladki.add("Wykres RHR")
        self.tab_hros = self.zakladki.add("Wykres HROS")

    def wybierz_folder_fit(self):
        folder = filedialog.askdirectory(title="Wybierz główny folder 'Fit' z Google Takeout")
        if folder:
            self.folder_fit_sciezka = folder
            self.label_folder_fit.configure(text=folder)
            self.cache_sen = None
            self.cache_tetno = None
            self.cache_kroki = None

    def sprawdz_dane(self):
        if not self.folder_fit_sciezka:
            messagebox.showwarning("Błąd", "Wybierz najpierw główny folder 'Fit' z danymi!")
            return

        try:
            self.pole_tekstowe.delete("1.0", ctk.END)
            self.pole_tekstowe.insert(ctk.END, "Skanowanie struktury folderów i wczytywanie danych...\n")
            self.update()

            self.cache_sen, self.cache_tetno, self.cache_kroki = wczytaj_surowe_dane(self.folder_fit_sciezka)

            if self.cache_sen.empty:
                messagebox.showwarning("Uwaga", "Nie znaleziono danych o śnie.")
                return

            wszystkie_daty = []
            if not self.cache_sen.empty:
                wszystkie_daty.append(self.cache_sen['Data'].min())
                wszystkie_daty.append(self.cache_sen['Data'].max())
            if not self.cache_tetno.empty:
                wszystkie_daty.append(self.cache_tetno['Data'].min())
                wszystkie_daty.append(self.cache_tetno['Data'].max())
            if not self.cache_kroki.empty:
                wszystkie_daty.append(self.cache_kroki['Data'].min())
                wszystkie_daty.append(self.cache_kroki['Data'].max())

            min_data = min(wszystkie_daty)
            max_data = max(wszystkie_daty)

            self.kalendarz_od.set_date(min_data)
            self.kalendarz_do.set_date(max_data)

            liczba_hr = self.cache_tetno.groupby('Data').size().reset_index(name='Gestosc_HR')
            liczba_kroki = self.cache_kroki.groupby('Data').size().reset_index(name='Gestosc_Kroki')
            dzienne_kroki = self.cache_kroki.groupby('Data')['Kroki'].sum().reset_index(name='Liczba kroków')

            self.pelna_baza = pd.merge(
                self.cache_sen[['Data', 'czas_snu']].rename(columns={'czas_snu': 'Czas snu (min)'}), liczba_hr,
                on='Data', how='outer')
            self.pelna_baza = pd.merge(self.pelna_baza, liczba_kroki, on='Data', how='outer')
            self.pelna_baza = pd.merge(self.pelna_baza, dzienne_kroki, on='Data', how='outer')
            self.pelna_baza['Czas snu (min)'] = self.pelna_baza['Czas snu (min)'] // 60
            self.pelna_baza['Data'] = pd.to_datetime(self.pelna_baza['Data'])
            self.pelna_baza = self.pelna_baza.sort_values(by='Data').reset_index(drop=True)

            self.btn_heatmap.configure(state="normal")

            self.pole_tekstowe.delete("1.0", ctk.END)
            self.pole_tekstowe.insert(ctk.END, f"Sprawdzanie zakończone pomyślnie!\n\n")
            self.pole_tekstowe.insert(ctk.END,
                                      f"Wykryto zakres od: {min_data.strftime('%Y-%m-%d')} do: {max_data.strftime('%Y-%m-%d')}\n\n")
            self.pole_tekstowe.insert(ctk.END,
                                      "Kalendarz został zaktualizowany. Możesz teraz wybrać 'Uruchom analizę' lub podejrzeć surowe dane klikając 'Pokaż dane źródłowe'.\n")

        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił problem podczas sprawdzania danych:\n{str(e)}")

    def rysuj_wykres_w_zakladce(self, fig, zakladka):
        for widget in zakladka.winfo_children():
            widget.destroy()

        if fig:
            canvas = FigureCanvasTkAgg(fig, master=zakladka)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

    def wypelnij_tabele_danych(self, dane, zakladka):
        for widget in zakladka.winfo_children():
            widget.destroy()

        kolumny = ("Data", "Kroki", "Sen (min)", "Średnie tętno", "RHR", "Norma RHR (28d)", "Odchylenie RHR",
                   "Wskaźnik HROS")

        tabela = ttk.Treeview(zakladka, columns=kolumny, show="headings", height=15)

        for kol in kolumny:
            tabela.heading(kol, text=kol)
            tabela.column(kol, width=120, anchor="center")

        tabela.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        pasek = ttk.Scrollbar(zakladka, orient="vertical", command=tabela.yview)
        tabela.configure(yscroll=pasek.set)
        pasek.pack(side="right", fill="y", padx=(0, 10), pady=10)

        if dane is not None and not dane.empty:
            for idx, wiersz in dane.iterrows():
                dt = wiersz['Data'].strftime('%Y-%m-%d') if pd.notna(wiersz['Data']) else "-"
                kroki = f"{wiersz['Liczba kroków']:.0f}" if pd.notna(wiersz.get('Liczba kroków')) else "-"
                sen = f"{wiersz['Czas snu (min)']:.0f}" if pd.notna(wiersz.get('Czas snu (min)')) else "-"
                sr_dzienne = f"{wiersz['Srednie_dzienne_HR']:.1f}" if pd.notna(
                    wiersz.get('Srednie_dzienne_HR')) else "-"
                rhr = f"{wiersz['Nocne tętno (bpm)']:.1f}" if pd.notna(wiersz.get('Nocne tętno (bpm)')) else "-"
                norma = f"{wiersz['Baseline_RHR']:.1f}" if pd.notna(wiersz.get('Baseline_RHR')) else "-"
                odchyl_rhr = f"{wiersz['Odchylenie_RHR']:.2f}" if pd.notna(wiersz.get('Odchylenie_RHR')) else "-"
                hros = f"{wiersz['Z_score_HROS']:.2f}" if pd.notna(wiersz.get('Z_score_HROS')) else "-"

                tabela.insert("", "end", values=(dt, kroki, sen, sr_dzienne, rhr, norma, odchyl_rhr, hros))

    def pokaz_okno_danych(self):
        if self.pelna_baza is None or self.pelna_baza.empty:
            return

        okno = ctk.CTkToplevel(self)
        okno.title("Podgląd Wczytanych Danych i Wizualizacja")
        okno.geometry("1250x800")
        okno.attributes("-topmost", True)

        zakladki_okna = ctk.CTkTabview(okno)
        zakladki_okna.pack(fill="both", expand=True, padx=10, pady=10)

        tab_heatmap = zakladki_okna.add("Heatmapa dostępności danych")
        tab_tetno = zakladki_okna.add("Tętno")
        tab_kroki = zakladki_okna.add("Kroki")
        tab_sen = zakladki_okna.add("Sen")

        # 1. Zakładka z Heatmapą
        fig = wykres_heatmap(self.pelna_baza)
        if fig:
            canvas = FigureCanvasTkAgg(fig, master=tab_heatmap)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # 2. Zakładka z tętnem
        frame_tetno = ctk.CTkFrame(tab_tetno)
        frame_tetno.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame_tetno, text="Punkty pomiarowe tętna z pliku JSON:", font=("Arial", 13, "bold")).pack(
            anchor="w", padx=10, pady=(5, 5))

        tabela_t = ttk.Treeview(frame_tetno, columns=("Czas", "Wartość (BPM)"), show="headings", height=25)
        tabela_t.heading("Czas", text="Data i godzina pomiaru")
        tabela_t.heading("Wartość (BPM)", text="Tętno (BPM)")
        tabela_t.column("Czas", width=300, anchor="center")
        tabela_t.column("Wartość (BPM)", width=200, anchor="center")
        tabela_t.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        pasek_t = ttk.Scrollbar(frame_tetno, orient="vertical", command=tabela_t.yview)
        tabela_t.configure(yscroll=pasek_t.set)
        pasek_t.pack(side="right", fill="y", padx=(0, 10), pady=10)

        if self.cache_tetno is not None and not self.cache_tetno.empty:
            for idx, wiersz in self.cache_tetno.head(5000).iterrows():
                tabela_t.insert("", "end",
                                values=(wiersz['PelnyCzas'].strftime('%Y-%m-%d %H:%M:%S'), f"{wiersz['Tetno']:.1f}"))

        # 3. Zakładka z krokami
        frame_kroki = ctk.CTkFrame(tab_kroki)
        frame_kroki.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame_kroki, text="Wpisy kroków z pliku JSON:", font=("Arial", 13, "bold")).pack(anchor="w",
                                                                                                      padx=10,
                                                                                                      pady=(5, 5))

        tabela_k = ttk.Treeview(frame_kroki, columns=("Czas", "Kroki"), show="headings", height=25)
        tabela_k.heading("Czas", text="Data i godzina pomiaru")
        tabela_k.heading("Kroki", text="Liczba kroków")
        tabela_k.column("Czas", width=300, anchor="center")
        tabela_k.column("Kroki", width=200, anchor="center")
        tabela_k.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        pasek_k = ttk.Scrollbar(frame_kroki, orient="vertical", command=tabela_k.yview)
        tabela_k.configure(yscroll=pasek_k.set)
        pasek_k.pack(side="right", fill="y", padx=(0, 10), pady=10)

        if self.cache_kroki is not None and not self.cache_kroki.empty:
            for idx, wiersz in self.cache_kroki.head(5000).iterrows():
                tabela_k.insert("", "end",
                                values=(wiersz['PelnyCzas'].strftime('%Y-%m-%d %H:%M:%S'), f"{wiersz['Kroki']}"))

        # 4. Zakładka ze snem
        frame_sen = ctk.CTkFrame(tab_sen)
        frame_sen.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame_sen, text="Sesje snu z plików JSON:", font=("Arial", 13, "bold")).pack(anchor="w", padx=10,
                                                                                                  pady=(5, 5))

        tabela_s = ttk.Treeview(frame_sen, columns=("Start", "Koniec", "Czas trwania (min)"), show="headings",
                                height=25)
        tabela_s.heading("Start", text="Początek snu")
        tabela_s.heading("Koniec", text="Koniec snu")
        tabela_s.heading("Czas trwania (min)", text="Czas trwania (min)")
        tabela_s.column("Start", width=250, anchor="center")
        tabela_s.column("Koniec", width=250, anchor="center")
        tabela_s.column("Czas trwania (min)", width=200, anchor="center")
        tabela_s.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        pasek_s = ttk.Scrollbar(frame_sen, orient="vertical", command=tabela_s.yview)
        tabela_s.configure(yscroll=pasek_s.set)
        pasek_s.pack(side="right", fill="y", padx=(0, 10), pady=10)

        if self.cache_sen is not None and not self.cache_sen.empty:
            for idx, wiersz in self.cache_sen.iterrows():
                start_str = wiersz['start_pelny'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(
                    wiersz.get('start_pelny')) else "-"
                koniec_str = wiersz['koniec_pelny'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(
                    wiersz.get('koniec_pelny')) else "-"
                min_str = f"{wiersz['czas_snu'] // 60}" if pd.notna(wiersz.get('czas_snu')) else "-"
                tabela_s.insert("", "end", values=(start_str, koniec_str, min_str))

    def start_analizy(self):
        if not self.folder_fit_sciezka:
            messagebox.showwarning("Błąd", "Wybierz najpierw główny folder 'Fit' z danymi!")
            return

        data_od_dt = self.kalendarz_od.get_date()
        data_do_dt = self.kalendarz_do.get_date()
        pomin_falszywe_stan = bool(self.ukryj_falszywe_var.get())

        self.pole_tekstowe.delete("1.0", ctk.END)
        self.pole_tekstowe.insert(ctk.END, "Trwa obliczanie wskaźników diagnostycznych...\n")
        self.btn_zapisz.configure(state="disabled")
        self.update()

        try:
            if self.cache_sen is None or self.cache_tetno is None or self.cache_kroki is None:
                self.cache_sen, self.cache_tetno, self.cache_kroki = wczytaj_surowe_dane(self.folder_fit_sciezka)

            self.pelna_baza, self.zapisana_baza, self.zapisany_raport_tekst = uruchom_analize_z_cache(
                self.cache_sen, self.cache_tetno, self.cache_kroki, data_od_dt, data_do_dt, pomin_falszywe_stan
            )

            if self.pelna_baza is not None and not self.pelna_baza.empty:
                self.btn_heatmap.configure(state="normal")

            if self.zapisana_baza.empty:
                self.pole_tekstowe.insert(ctk.END, "\nBrak danych w wybranym przedziale czasowym!")
                self.wypelnij_tabele_danych(None, self.tab_dane)
                self.rysuj_wykres_w_zakladce(None, self.tab_rhr)
                self.rysuj_wykres_w_zakladce(None, self.tab_hros)
            else:
                self.pole_tekstowe.delete("1.0", ctk.END)
                self.pole_tekstowe.insert(ctk.END, self.zapisany_raport_tekst)

                baza_do_wykresow = self.zapisana_baza.copy()

                if pomin_falszywe_stan:
                    for prefiks in ['RHR', 'HROS']:
                        kol_inf = f'Infekcja_{prefiks}'
                        kol_ostrz = f'Ostrzezenie_{prefiks}'

                        for idx, wiersz in baza_do_wykresow[
                            (baza_do_wykresow[kol_inf] == 1) | (baza_do_wykresow[kol_ostrz] == 1)].iterrows():
                            data_zd = wiersz['Data']
                            okno_przed = self.zapisana_baza[
                                (self.zapisana_baza['Data'] >= data_zd - pd.Timedelta(days=14)) & (
                                            self.zapisana_baza['Data'] < data_zd)]
                            okno_po = self.zapisana_baza[(self.zapisana_baza['Data'] >= data_zd) & (
                                        self.zapisana_baza['Data'] <= data_zd + pd.Timedelta(days=7))]

                            kroki_przed = okno_przed['Liczba kroków'].mean()
                            kroki_po = okno_po['Liczba kroków'].mean()

                            if pd.notna(kroki_przed) and pd.notna(kroki_po) and kroki_przed > 0:
                                spadek_proc = ((kroki_po - kroki_przed) / kroki_przed) * 100

                                if spadek_proc > -20:
                                    baza_do_wykresow.at[idx, kol_inf] = 0
                                    baza_do_wykresow.at[idx, kol_ostrz] = 0

                self.fig_rhr = wykres_rhr(baza_do_wykresow)
                self.fig_hros = wykres_hros(baza_do_wykresow)

                self.rysuj_wykres_w_zakladce(self.fig_rhr, self.tab_rhr)
                self.rysuj_wykres_w_zakladce(self.fig_hros, self.tab_hros)

                self.wypelnij_tabele_danych(self.zapisana_baza, self.tab_dane)
                self.btn_zapisz.configure(state="normal")

                self.zakladki.set("Dane")

        except FileNotFoundError as fnf_error:
            self.pole_tekstowe.insert(ctk.END, f"\nWystąpił problem:\n{str(fnf_error)}\n")
        except Exception as e:
            self.pole_tekstowe.insert(ctk.END, f"\nWystąpił błąd:\n{str(e)}\n")

    def generuj_pliki(self):
        if self.zapisana_baza is None or self.zapisana_baza.empty:
            return

        nazwa_csv = "Wyniki_Analizy.csv"
        nazwa_pdf = "Raport_Wykresy.pdf"

        self.zapisana_baza.to_csv(nazwa_csv, index=False, encoding='utf-8')

        with PdfPages(nazwa_pdf) as pdf:
            if self.fig_rhr:
                pdf.savefig(self.fig_rhr)
            if self.fig_hros:
                pdf.savefig(self.fig_hros)

            linie_raportu = self.zapisany_raport_tekst.split('\n')
            max_linii = 45

            for i in range(0, len(linie_raportu), max_linii):
                fragment_tekstu = '\n'.join(linie_raportu[i:i + max_linii])
                fig_text = plt.figure(figsize=(10, 8))
                fig_text.clf()
                fig_text.text(0.05, 0.95, fragment_tekstu, transform=fig_text.transFigure, size=10, family='monospace',
                              va='top')
                pdf.savefig(fig_text)
                plt.close(fig_text)

        messagebox.showinfo("Sukces", f"Zapisano pomyślnie pliki do folderu głównego:\n{nazwa_csv}\n{nazwa_pdf}")


if __name__ == "__main__":
    app = Aplikacja()
    app.mainloop()