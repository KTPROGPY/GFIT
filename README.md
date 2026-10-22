# Analizator Zdrowia (Detekcja Infekcji RHR & HROS)

## Opis projektu
Aplikacja okienkowa (GUI) służąca do analizy danych zdrowotnych i aktywności fizycznej wyeksportowanych z usługi Google Fit (Google Takeout). Program przetwarza pliki JSON dotyczące snu, tętna i liczby kroków, aby wykrywać anomalie i potencjalne infekcje. Wykorzystuje do tego analizę nocnego tętna spoczynkowego (RHR) oraz metodę HROS (analiza tętna podczas bardzo lekkiej aktywności/spoczynku w ciągu dnia).

## Lista głównych funkcji
- **Automatyczne przetwarzanie  plików JSON:** Wczytywanie surowych danych z Google Takeout 
- **Analiza RHR:** Wyliczanie nocnego tętna z okresów snu i śledzenie odchyleń (Z-score) względem średniej z 28 dni.
- **Analiza HROS:** Śledzenie anomalii tętna w ciągu dnia przy minimalnym wysiłku fizycznym.
- **Weryfikacja krzyżowa:** Automatyczne odrzucanie "fałszywych alarmów" poprzez sprawdzanie, czy po anomaliach tętna nastąpił spadek aktywności (kroków) o minimum 20%.
- **Generowanie raportów:** Eksport wyników do plików CSV oraz PDF wraz z wygenerowanymi wykresami.
- **Interfejs graficzny z ciemnym motywem:** Prosty w obsłudze interfejs z podglądem danych w formie tabel, wykresów oraz heatmapy.

## Instrukcja instalacji i uruchomienia
1. Upewnij się, że masz zainstalowanego Pythona (zalecana wersja 3.9 lub nowsza).
2. Pobierz pliki projektu do jednego folderu.
3. Otwórz terminal (wiersz poleceń) w tym folderze i zainstaluj wymagane biblioteki:
   `pip install -r requirements.txt`
4. Uruchom aplikację klikając dwukrotnie plik programu (jeśli zmieniłeś rozszerzenie na `.pyw`) lub wpisując w terminalu:
   `python analizator.py`

## Informacja o wykorzystaniu AI
Projekt został zrealizowany przy wsparciu asystenta sztucznej inteligencji (Gemini). AI pomagało głównie w:
- Zaprojektowaniu i wdrożeniu interfejsu graficznego za pomocą `customtkinter`.
- Debugowaniu kodu oraz optymalizacji funkcji generujących wykresy `matplotlib`.
- Formatowaniu tekstu, wykresów oraz poprawkach UX/UI.
- Doborze własciwych metod analitycznych, oraz testowaniu różnych rozwiązań powstałych problemów.
