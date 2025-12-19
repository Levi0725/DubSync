# DubSync - Professzionális Szinkronfordító Szerkesztő

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010+-lightgrey.svg)]()

A DubSync egy professzionális, Windows-alapú asztali alkalmazás szinkronfordítók és szinkronrendezők számára. Az alkalmazás segítségével hatékonyan készíthetők magyar nyelvű szinkronszövegek, időkód-pontos ajkszinkronnal.

## 🎬 Főbb funkciók

### Projektkezelés
- **Egyedi .dubsync formátum**: Hordozható SQLite-alapú projektfájl
- **Automatikus mentés**: Soha ne veszítsd el a munkádat
- **Legutóbbi projektek**: Gyors hozzáférés korábbi munkákhoz

### SRT Import/Export
- **Többféle kódolás**: UTF-8, UTF-8 BOM, CP1250, ISO-8859-2
- **Intelligens tisztítás**: HTML és ASS tagek automatikus eltávolítása
- **Kétirányú**: Import és export is támogatott

### Videó lejátszás
- **Beágyazott lejátszó**: Nincs szükség külső programra
- **Szegmens lejátszás**: Csak az aktuális cue lejátszása
- **Sebességszabályzás**: 0.5x - 2.0x sebesség
- **Frame-pontos navigáció**: Előre/hátra léptetés képkockánként

### Lip-Sync Becslés
- **Valós idejű elemzés**: Gépelés közben frissülő eredmények
- **Magyar nyelvre optimalizálva**: 13 karakter/másodperc alapértelmezett
- **Forrásnyelv figyelembevétele**: Angol beszédsebesség alapján számított időkeret
- **Szögletes zárójelek figyelmen kívül hagyása**: Rendezői utasítások nem számítanak
- **Vizuális visszajelzés**: Színkódolt állapot (zöld/sárga/piros)

### Lektori megjegyzések
- **Cue-szintű kommentek**: Minden szöveghez külön megjegyzések
- **Feloldás követés**: Megoldott/megoldatlan státusz
- **Csapatmunka támogatás**: Több lektor közös munkája

### PDF Export
- **Klasszikus szinkronkönyv formátum**: Iparági standard
- **Magyar ékezetek**: Teljes Unicode támogatás
- **Kétnyelvű opció**: Forrás és célnyelv egymás mellett

### Plugin rendszer
- **Bővíthető architektúra**: Saját plugin-ek írhatók
- **Plugin típusok**: Export, QA, UI bővítés, szolgáltatások
- **Beépített plugin-ek**:
  - 🌍 Argos Fordító: Offline angol-magyar fordító
  - CSV Export: Táblázatos export
  - Basic QA: Alapvető minőségellenőrzés

### Beállítások
- **Témák**: Sötét, világos, egyedi színek
- **Általános beállítások**: Mentési hely, felhasználói adatok
- **Plugin kezelés**: Pluginok ki/bekapcsolása, beállítások

## 📋 Rendszerkövetelmények

- **Operációs rendszer**: Windows 10 vagy újabb
- **Python**: 3.10+
- **RAM**: minimum 4 GB
- **Tárhely**: ~100 MB (+ projektek mérete)
- **Videó codec-ek**: Windows Media Foundation támogatott formátumok

## 🚀 Telepítés

### Gyors indítás (ajánlott)

```bash
# Repository klónozása
git clone https://github.com/Levi0725/DubSync.git
cd dubsync

# Indítás (automatikusan beállítja a környezetet)
.\run.ps1   # PowerShell
# vagy
run.bat     # Command Prompt
```

### Manuális telepítés

#### 1. Repository klónozása

```bash
git clone https://github.com/Levi0725/DubSync.git
cd dubsync
```

#### 2. Virtuális környezet létrehozása

```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Függőségek telepítése

```bash
pip install -r requirements.txt
```

#### 4. Alkalmazás indítása

```bash
python -m dubsync
```

Vagy fejlesztői módban:

```bash
pip install -e .
dubsync
```

## 📖 Használat

### Új projekt létrehozása

1. `Fájl > Új projekt` (Ctrl+N)
2. Válaszd ki a mentési helyet és adj nevet
3. Állítsd be a forrás- és célnyelvet

### SRT importálás

1. `Fájl > SRT importálás` (Ctrl+I)
2. Válaszd ki az SRT fájlt
3. A cue-k automatikusan betöltődnek

### Videó csatolása

1. `Fájl > Videó csatolása`
2. Válaszd ki a videófájlt (MP4, AVI, MKV, stb.)
3. A videó megjelenik a lejátszóban

### Fordítás

1. Kattints egy cue-ra a listában
2. A szerkesztőben írd be a fordítást
3. A lip-sync mutató valós időben frissül
4. `Mentés` gomb → automatikus ugrás a következő sorra

### Beállítások

1. `Fájl > Alkalmazás beállítások` (Ctrl+,)
2. Állítsd be az általános opciókat
3. Kezeld a pluginokat (újraindítás szükséges)
4. Válaszd ki a témát

### PDF export

1. `Fájl > PDF export` (Ctrl+E)
2. Válaszd ki a formátumot
3. Állítsd be az opciókat
4. Mentsd a PDF-et

## ⌨️ Billentyűkombinációk

| Kombináció | Funkció |
|------------|---------|
| Ctrl+N | Új projekt |
| Ctrl+O | Projekt megnyitása |
| Ctrl+S | Mentés |
| Ctrl+I | SRT importálás |
| Ctrl+E | PDF export |
| Space | Videó lejátszás/megállítás |
| F5 | Szegmens lejátszás |
| , | Előző képkocka |
| . | Következő képkocka |
| Ctrl+↑ | Előző cue |
| Ctrl+↓ | Következő cue |
| Ctrl+F | Keresés |
| F11 | Teljes képernyő |

## 🔌 Plugin fejlesztés

### Export plugin példa

```python
from dubsync.plugins.base import ExportPlugin

class MyExportPlugin(ExportPlugin):
    @property
    def name(self) -> str:
        return "My Export"
    
    @property
    def file_extension(self) -> str:
        return ".txt"
    
    def export(self, cues, output_path, **options):
        with open(output_path, 'w', encoding='utf-8') as f:
            for cue in cues:
                f.write(f"{cue.translated_text}\n")
        return True
```

### QA plugin példa

```python
from dubsync.plugins.base import QAPlugin

class MyQAPlugin(QAPlugin):
    @property
    def name(self) -> str:
        return "My QA Check"
    
    def check_cue(self, cue):
        issues = []
        if len(cue.translated_text) > 100:
            issues.append({
                "severity": "warning",
                "message": "Túl hosszú szöveg"
            })
        return issues
```

## 🧪 Tesztelés

```bash
# Összes teszt futtatása
pytest

# Részletes kimenet
pytest -v

# Lefedettség mérés
pytest --cov=dubsync --cov-report=html
```

## 📁 Projekt struktúra

```
dubsync/
├── src/
│   └── dubsync/
│       ├── __init__.py
│       ├── main.py
│       ├── app.py
│       ├── models/
│       │   ├── database.py
│       │   ├── project.py
│       │   ├── cue.py
│       │   └── comment.py
│       ├── services/
│       │   ├── srt_parser.py
│       │   ├── lip_sync.py
│       │   ├── pdf_export.py
│       │   └── project_manager.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── cue_list.py
│       │   ├── cue_editor.py
│       │   ├── video_player.py
│       │   ├── comments_panel.py
│       │   └── dialogs.py
│       ├── plugins/
│       │   ├── base.py
│       │   ├── registry.py
│       │   └── builtin/
│       └── utils/
│           ├── constants.py
│           └── time_utils.py
├── tests/
├── requirements.txt
└── setup.py
```

## 🤝 Közreműködés

1. Fork-old a repository-t
2. Hozz létre egy feature branch-et (`git checkout -b feature/AmazingFeature`)
3. Commit-old a változtatásokat (`git commit -m 'Add some AmazingFeature'`)
4. Push-old a branch-et (`git push origin feature/AmazingFeature`)
5. Nyiss egy Pull Request-et

## 📄 Licenc

MIT License - lásd a [LICENSE](../LICENSE) fájlt.

## 🙏 Köszönetnyilvánítás

- Qt/PySide6 - GUI framework
- ReportLab - PDF generálás
- SQLite - Adatbázis motor

## 📞 Kapcsolat

Hibák jelentése és feature kérések: [GitHub Issues](https://github.com/Levi0725/DubSync/issues)
