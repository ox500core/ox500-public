# BLISK — wydajność stron i automatyzacja przetwarzania obrazów

**Projekt:** własny system budowy stron z wykorzystaniem agentów AI, wdrożony m.in. na [blisk.pl](https://blisk.pl).

## Cel i moje zadania

Ustalałem wymagania szybkości, responsywności, kontroli jakości i kosztów publikacji. Akceptowałem kierunki zmian oraz wymagałem porównania wyników z testami. Kod budowniczego stron, automatyzacji obrazów i cache był implementowany z pomocą agentów AI.

## Zweryfikowana wydajność

W udokumentowanym pomiarze laboratoryjnym Lighthouse 13.4.0 z 13 lipca 2026 r.:

| Miernik | Mobile | Desktop |
|---|---:|---:|
| Performance | **100/100** | **100/100** |
| LCP | 0,9 s | 0,4 s |
| TBT | 0 ms | 0 ms |
| CLS | 0 | 0 |

Accessibility i Best Practices również otrzymały 100 punktów w tym audycie. Wynik SEO był wtedy ograniczony świadomym ustawieniem `noindex`; nie należy więc twierdzić, że wszystkie kategorie zawsze osiągały 100.

## Automatyzacja mediów

System generuje responsywne warianty **WebP/AVIF** podczas budowania witryny. Warianty są buforowane według identyfikatora zawartości i parametrów kodowania.

W udokumentowanej próbie cache:

- zapisano **214 unikalnych wariantów**;
- przy kolejnym buildzie bez zmian obrazów zapisano **0 z 80 wariantów** na nowo;
- mechanizm został rozszerzony o eliminację podwójnego cache i limit **256 MiB** wraz z testami regresji.

**Granice dowodu:** są to wyniki konkretnych audytów i testów, a nie gwarancja obecnej wydajności strony ani stałego wyniku 100.

**Wewnętrzne źródła weryfikacji:** wewnętrzne repozytorium systemu stron, PR **#25** (Lighthouse), **#95** (AVIF/WebP cache), **#111** (usunięcie duplikacji cache), **#112** (ograniczenie cache). Wszystkie cztery były scalone przy przygotowaniu opisu.
