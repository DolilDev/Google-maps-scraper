# Google Maps Lead Scraper & Manager

Zaawansowane narzędzie do automatyzacji procesów pozyskiwania kontaktów (Lead Generation) bezpośrednio z Google Maps. Aplikacja została zaprojektowana, aby wspierać agencje marketingowe w identyfikacji firm, które nie posiadają własnej strony internetowej i wymagają wsparcia w budowaniu widoczności w sieci.

## 🚀 Kluczowe Funkcje
* **Automatyczna ekstrakcja danych:** Wykorzystanie silnika Playwright do emulacji zachowań użytkownika i masowego skanowania wyników wyszukiwania.
* **Inteligentne filtrowanie:** Skrypt automatycznie pomija firmy posiadające już witrynę WWW oraz filtruje branże o niskim potencjale sprzedażowym (np. urzędy, szkoły).
* **Zasięg ogólnopolski:** Predefiniowana baza 40 największych miast Polski z możliwością monitorowania postępu na żywo.
* **Lead Manager:** Osobny moduł do przeglądania, filtrowania i eksportu zebranych danych do formatu CSV przyjaznego dla systemów CRM.
* **Real-time Monitoring:** Dashboard wyświetlający statystyki na żywo: liczbę znalezionych firm, czas operacji oraz aktualnie skanowaną lokalizację.

## 📂 Struktura Projektu
```
Doliil-Maps-Scraper/
├── templates/              # Szablony HTML dla frameworka Flask
│   └── index.html          # Główny interfejs skrapera i dashboard live
├── app.py                  # Backend: serwer Flask i logika automatyzacji Playwright
├── lead_manager.html       # Narzędzie do zarządzania i eksportu pozyskanych baz danych
└── README.md               # Dokumentacja techniczna projektu

```

## 🛠️ Stos technologiczny

* **Backend:** Python (Flask, Playwright, Threading)
* **Frontend:** HTML5, CSS3 (Custom Properties), JavaScript (Vanilla JS, Server-Sent Events)
* **Zarządzanie danymi:** Formaty JSON oraz CSV (eksport danych)

## 📖 Instrukcja uruchomienia

1. Upewnij się, że masz zainstalowanego Pythona.
2. Zainstaluj wymagane biblioteki: `pip install flask playwright`.
3. Zainstaluj przeglądarki Playwright: `playwright install`.
4. Uruchom aplikację: `python app.py`.
5. Otwórz w przeglądarce adres: `http://localhost:5000`.
6. Aby zarządzać pobranymi danymi, otwórz plik `lead_manager.html` i załaduj wygenerowany plik CSV.

## 💡 Zastosowanie w SEO i Marketingu

Projekt demonstruje praktyczne wykorzystanie inżynierii oprogramowania w codziennej pracy specjalisty SEO:

1. **Audyt nasycenia rynku:** Szybka analiza lokalnej konkurencji w konkretnych regionach.
2. **Automatyzacja Outreachu:** Generowanie wysokiej jakości list kontaktowych do firm o niskiej widoczności cyfrowej.
3. **Efektywność pracy:** Zastąpienie czasochłonnych procesów ręcznych inteligentnym skryptem.

---

**Autor:** [DolilDev(https://github.com/DolilDev)]

