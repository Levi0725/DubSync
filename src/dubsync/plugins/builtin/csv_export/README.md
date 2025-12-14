# CSV Export Plugin

CSV formátumú export plugin a DubSync alkalmazáshoz.

## Funkciók

- Testreszabható export beállítások
- Többféle elválasztó karakter támogatása
- Választható mezők (forrás, időkódok, stb.)
- Excel kompatibilis UTF-8-BOM kódolás

## Használat

### Menüből
1. **Fájl → Export → CSV Export...** vagy
2. **Pluginok → 📊 CSV Export...** vagy
3. Gyorsbillentyű: **Ctrl+Shift+C**

### Export beállítások

| Beállítás | Leírás |
|-----------|--------|
| Elválasztó | Pontosvessző (;), vessző (,) vagy tabulátor |
| Forrás szöveg | Eredeti szöveg mezők exportálása |
| Időkódok | Kezdés és befejezés időpontok |
| Karakter nevek | Beszélők nevei |
| Megjegyzések | Belső jegyzetek |
| SFX jegyzetek | Hangeffektus megjegyzések |

## CSV formátum

A generált CSV a következő oszlopokat tartalmazhatja:

```
#;Kezdés;Vége;Karakter;Forrás;Fordítás;Megjegyzés;SFX
1;00:00:01,000;00:00:04,500;John;"Hello, world!";"Helló, világ!";Üdvözlés;
```

## Gyorsbillentyűk

| Billentyű | Funkció |
|-----------|---------|
| Ctrl+Shift+C | CSV Exportálás |

## Verzió

- **1.1.0**: UI beállítások panel, Pluginok menü integráció
- **1.0.0**: Alapvető CSV export
