# Alapvető QA Plugin

Minőségellenőrzési plugin a DubSync alkalmazáshoz.

## Funkciók

A plugin automatikusan ellenőrzi a következő problémákat:

| Probléma | Súlyosság | Leírás |
|----------|-----------|--------|
| Hiányzó fordítás | ⚠️ Figyelmeztetés | A cue-nak nincs fordított szövege |
| Túl hosszú lip-sync | 🔴 Hiba | A szöveg túl hosszú az időzítéshez képest |
| Dupla szóközök | ℹ️ Info | Felesleges dupla szóközök a szövegben |
| Hiányzó karakter név | ℹ️ Info | Nincs megadva a beszélő neve |
| Felesleges whitespace | ℹ️ Info | Szóközök a szöveg elején/végén |

## Használat

1. **Panel megnyitása**: Nézet → QA Panel
2. **Ellenőrzés futtatása**: Kattints a "▶️ Ellenőrzés futtatása" gombra vagy nyomd meg az **F7** billentyűt
3. **Hibára ugrás**: Dupla kattintás egy sorra a listában

## Gyorsbillentyűk

| Billentyű | Funkció |
|-----------|---------|
| F7 | QA ellenőrzés futtatása |

## Severity szintek

- 🔴 **Hiba (error)**: Kritikus probléma, javítás szükséges
- 🟡 **Figyelmeztetés (warning)**: Valószínűleg javítandó
- 🔵 **Info**: Javasolt javítás, de nem kötelező

## Verzió

- **1.1.0**: UI panel hozzáadása, Nézet menü integráció
- **1.0.0**: Alapvető QA ellenőrzések
