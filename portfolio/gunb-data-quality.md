# TellAhead / GUNB — odzyskanie istotnych opisów inwestycji

**Projekt:** własny, rozwijany system analizy źródeł publicznych. **Data próby:** 14 października 2026 r.

## Problem

W dwóch polach urzędowych zawierających opis zamierzenia budowlanego dodatkowe reguły treściowe usuwały poprawne informacje: nazwy firm, lokalizacje inwestycji i opisy projektów.

## Moja rola

Zakwestionowałem zasadność filtrów nakładanych na te konkretne pola i zażądałem zachowania pełnego opisu dla rekordów już zakwalifikowanych jako inwestycje organizacji. Jednocześnie należało zachować odrębną kontrolę kwalifikacji inwestora i nie dopuszczać błędnych wartości technicznych.

Analizę kodu, implementację i testy wykonywały agenty AI; ja zdefiniowałem zakres korekty i kontrolowałem, czy wynik odpowiada rzeczywistemu celowi biznesowemu.

## Wynik

W próbie **50 spraw** po korekcie zapisano **50 opisów**, odzyskując **17**, które wcześniej były błędnie odrzucone.

Nie jest to twierdzenie o poprawie 34% w całym krajowym zasobie ani dowód, że gotowe sygnały zostały wysłane klientom.

**Wewnętrzne źródło weryfikacji:** `tellahead` PR **#217**; scenariusz kontrolny Lubuskie 50/50, zmiany opisów SOURCE-002.
