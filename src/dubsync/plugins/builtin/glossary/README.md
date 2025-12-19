# Szótár Plugin

Egyéni fordító szótár plugin a DubSync alkalmazáshoz.

## Funkciók

### Bejegyzések kezelése
- **Hozzáadás**: Új szó/kifejezés párok felvétele angol → magyar fordítással
- **Szerkesztés**: Meglévő bejegyzések módosítása dupla kattintással vagy a szerkesztés gombbal
- **Törlés**: Nem kívánt bejegyzések eltávolítása
- **Keresés**: Gyors keresés a forrás, fordítás és megjegyzés mezőkben

### Import/Export
- **Fájlformátum**: `.glossync` (JSON alapú)
- **Szelektív import**: Választható, mely bejegyzéseket importáljuk
- **Szelektív export**: Választható, mely bejegyzéseket exportáljuk
- **Duplikátum kezelés**: Import során frissíti a meglévő bejegyzéseket

## Használat

1. Nyisd meg a Szótár panelt (Nézet → Szótár panel)
2. Adj hozzá bejegyzéseket a ➕ gombbal
3. Válassz ki egy bejegyzést és kattints a 📥 gombra a fordítás beillesztéséhez
4. Exportáld a szótárat a 💾 Export gombbal

## .glossync fájlformátum

```json
{
  "name": "Szótár neve",
  "source_lang": "en",
  "target_lang": "hu",
  "entries": [
    {
      "source": "Hello",
      "target": "Szia",
      "notes": "Köszönés"
    }
  ]
}
```

## Billentyűparancsok

- **Dupla kattintás**: Bejegyzés szerkesztése
- **Jobb kattintás**: Kontextus menü

## Verzió

- 1.0.0 - Kezdeti verzió
