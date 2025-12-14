# Contributing to DubSync

Köszönjük, hogy hozzá szeretnél járulni a DubSync projekthez! 🎬

## 🐛 Hibajelentés

Ha hibát találtál, kérjük nyiss egy Issue-t és add meg:

1. **A hiba leírása** - Mi történt?
2. **Elvárt viselkedés** - Mi kellett volna történjen?
3. **Reprodukálási lépések** - Hogyan lehet megismételni a hibát?
4. **Környezet** - Windows verzió, Python verzió
5. **Képernyőkép** - Ha releváns

## 💡 Funkció javaslat

Ha új funkciót szeretnél, nyiss egy Issue-t és írd le:

1. **A funkció leírása** - Mit csinálna?
2. **Miért hasznos?** - Ki használná és mikor?
3. **Példák** - Hogyan nézne ki a gyakorlatban?

## 🔧 Pull Request készítése

### Előkészületek

1. Fork-old a repository-t
2. Klónozd a fork-ot: `git clone https://github.com/TE-USERNAME/dubsync.git`
3. Hozz létre egy branch-et: `git checkout -b feature/uj-funkcio`

### Kód stílus

- PEP 8 követése
- Típus annotációk használata ahol lehetséges
- Docstringek írása minden publikus metódushoz
- Magyar nyelv a felhasználói üzenetekben

### Tesztek

```bash
# Tesztek futtatása
pytest tests/ -v

# Csak specifikus teszt
pytest tests/test_models.py -v
```

### Commit üzenetek

```
feat: Új funkció leírása
fix: Hibajavítás leírása
docs: Dokumentáció módosítás
refactor: Kód átszervezés
test: Teszt hozzáadás/módosítás
```

### PR benyújtása

1. Push-old a változásokat: `git push origin feature/uj-funkcio`
2. Nyiss egy Pull Request-et
3. Írd le a változásokat részletesen
4. Várd meg a review-t

## 📋 Fejlesztési útmutató

### Virtuális környezet

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Fejlesztői függőségek
```

### Projekt struktúra

```
src/dubsync/
├── models/      # Adatmodellek (Project, Cue, Comment)
├── services/    # Üzleti logika (ProjectManager, PDFExporter)
├── ui/          # Qt widgetek és dialógusok
├── plugins/     # Plugin rendszer
└── utils/       # Segédfüggvények
```

### Plugin fejlesztés

Lásd: [docs/PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md)

## 📜 Licensz

A hozzájárulásodat MIT licensz alatt teszed közzé.
