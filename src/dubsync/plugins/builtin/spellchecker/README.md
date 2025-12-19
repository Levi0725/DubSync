# Helyesírás-ellenőrző Plugin

Magyar helyesírás-ellenőrző plugin a DubSync alkalmazáshoz.

## Funkciók

### Helyesírás-ellenőrzés
- **Magyar nyelv**: Hunspell alapú magyar szótár
- **Automatikus ellenőrzés**: Cue kiválasztásakor automatikusan ellenőrzi a szöveget
- **Javaslatok**: Hibás szavakhoz javítási javaslatok

### Kivételek kezelése
- **Figyelmen kívül hagyás**: Szavak amit nem kell ellenőrizni (nevek, rövidítések)
- **Egyéni szótár**: Szavak hozzáadása a szótárhoz
- **Import/Export**: Kivételek mentése és betöltése

## Telepítés

A plugin a `spylls` Python csomagot használja, ami egy pure Python Hunspell implementáció:

```bash
pip install spylls
```

### Magyar szótár

A plugin automatikusan keresi a rendszerre telepített magyar Hunspell szótárat.
Ha nem találja, le kell tölteni a magyar szótárt:

1. Töltsd le a magyar szótárat: https://github.com/LibreOffice/dictionaries/tree/master/hu_HU
2. Másold a `hu_HU.dic` és `hu_HU.aff` fájlokat a plugin `dictionaries` mappájába

## Használat

1. Nyisd meg a Helyesírás panelt (Nézet → Helyesírás panel)
2. Válassz ki egy cue-t a listából
3. A hibás szavak megjelennek a panelen
4. Jobb kattintással:
   - Választhatsz a javaslatokból
   - Hozzáadhatod a kivételekhez
   - Hozzáadhatod az egyéni szótárhoz

## Kivételek fájlformátum

```json
{
  "ignored": ["szó1", "szó2"],
  "custom": ["egyéni1", "egyéni2"]
}
```

## Billentyűparancsok

- **Jobb kattintás**: Kontextus menü javaslatokkal

## Verzió

- 1.0.0 - Kezdeti verzió
