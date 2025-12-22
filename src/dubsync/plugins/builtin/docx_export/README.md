# DOCX Export Plugin

Word dokumentum export plugin a DubSync alkalmazáshoz.

## Funkciók

- Export Word (.docx) formátumba
- Két stílus: táblázatos és forgatókönyv
- Testreszabható tartalom (időkódok, forrásnyelv, megjegyzések, stb.)
- Professzionális formázás
- Státusz színekkel jelölve

## Használat

1. Nyiss meg egy projektet
2. Menü: Plugins → DOCX Export
3. Válaszd ki az export beállításokat
4. Kattints az "Export DOCX-ba" gombra
5. Add meg a mentési helyet

## Stílusok

### Táblázatos elrendezés
- Minden cue egy sorban
- Oszlopok: #, Idő, Karakter, Forrás, Fordítás, Megjegyzések, Státusz
- Színezett fejléc és státusz cellák

### Forgatókönyv formátum
- Karakternév középen, nagybetűvel
- Időkód és forrásszöveg szürkével
- Fordítás behúzással
- Megjegyzések dőlt betűvel

## Követelmények

```
python-docx>=0.8.0
```

## Telepítés

A plugin automatikusan települ a DubSync-kel. A python-docx könyvtár szükséges:

```bash
pip install python-docx
```
