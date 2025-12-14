# DubSync Architektúra Dokumentáció

## Áttekintés

A DubSync egy többrétegű architektúrát használ, amely elválasztja az adatkezelést, az üzleti logikát és a felhasználói felületet. Ez a dokumentum részletezi az alkalmazás belső felépítését.

## Architekturális rétegek

```
┌─────────────────────────────────────────────────────┐
│                    UI Réteg                         │
│   (PySide6/Qt Widgets, Dialógusok, Események)       │
├─────────────────────────────────────────────────────┤
│                Service Réteg                        │
│   (Üzleti logika, Feldolgozás, Export/Import)       │
├─────────────────────────────────────────────────────┤
│                 Model Réteg                         │
│   (Adatstruktúrák, ORM-szerű CRUD műveletek)        │
├─────────────────────────────────────────────────────┤
│              Adatbázis Réteg                        │
│   (SQLite, Séma kezelés, Tranzakciók)               │
└─────────────────────────────────────────────────────┘
```

## Komponensek

### 1. Adatbázis réteg (`models/database.py`)

A `DatabaseManager` osztály felelős az SQLite adatbázis kezeléséért.

```python
class DatabaseManager:
    """SQLite adatbázis wrapper."""
    
    def __init__(self, db_path: Path | str = ":memory:")
    def execute(self, query: str, params: tuple = ()) -> list
    def execute_many(self, query: str, data: list) -> None
    def begin_transaction(self) -> None
    def commit(self) -> None
    def rollback(self) -> None
```

**Séma felépítés:**

```sql
-- Projekt metaadatok
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Projekt információk
CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    source_language TEXT DEFAULT 'EN',
    target_language TEXT DEFAULT 'HU',
    video_path TEXT,
    frame_rate REAL DEFAULT 25.0,
    created_at TIMESTAMP,
    modified_at TIMESTAMP
);

-- Szinkron cue-k
CREATE TABLE cue (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    cue_index INTEGER NOT NULL,
    time_in_ms INTEGER NOT NULL,
    time_out_ms INTEGER NOT NULL,
    source_text TEXT DEFAULT '',
    translated_text TEXT DEFAULT '',
    character_name TEXT DEFAULT '',
    status TEXT DEFAULT 'new',
    lip_sync_ratio REAL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

-- Lektori megjegyzések
CREATE TABLE comment (
    id INTEGER PRIMARY KEY,
    cue_id INTEGER NOT NULL,
    author TEXT DEFAULT '',
    text TEXT NOT NULL,
    created_at TIMESTAMP,
    resolved INTEGER DEFAULT 0,
    FOREIGN KEY (cue_id) REFERENCES cue(id) ON DELETE CASCADE
);
```

### 2. Model réteg

#### Project (`models/project.py`)

```python
@dataclass
class Project:
    id: int | None = None
    title: str = ""
    source_language: str = "EN"
    target_language: str = "HU"
    video_path: str | None = None
    frame_rate: float = 25.0
    
    def save(self, db: DatabaseManager) -> None
    def delete(self, db: DatabaseManager) -> None
    
    @classmethod
    def load(cls, db: DatabaseManager, project_id: int) -> Project | None
    
    @classmethod
    def get_primary(cls, db: DatabaseManager) -> Project | None
```

#### Cue (`models/cue.py`)

```python
@dataclass
class Cue:
    id: int | None = None
    project_id: int | None = None
    cue_index: int = 0
    time_in_ms: int = 0
    time_out_ms: int = 0
    source_text: str = ""
    translated_text: str = ""
    character_name: str = ""
    status: str = CueStatus.NEW
    lip_sync_ratio: float = 0.0
    
    @property
    def duration_ms(self) -> int
    
    @property
    def time_in_tc(self) -> str  # Timecode formátum
    
    @property
    def time_out_tc(self) -> str
```

#### Comment (`models/comment.py`)

```python
@dataclass
class Comment:
    id: int | None = None
    cue_id: int = 0
    author: str = ""
    text: str = ""
    created_at: datetime | None = None
    resolved: bool = False
    
    def resolve(self) -> None
```

### 3. Service réteg

#### SRTParser (`services/srt_parser.py`)

Az SRT fájlok beolvasásáért és feldolgozásáért felelős.

```python
class SRTParser:
    def parse_file(self, file_path: Path) -> list[SRTEntry]
    def parse_content(self, content: str) -> list[SRTEntry]
    def get_cues(self, project_id: int) -> list[Cue]
    def has_errors(self) -> bool
    def get_errors(self) -> list[str]
```

**Támogatott kódolások:**
- UTF-8 (BOM-mal és anélkül)
- CP1250 (Windows Central European)
- ISO-8859-2 (Latin-2)

**Tisztítási műveletek:**
- HTML tagek eltávolítása (`<i>`, `<b>`, `<font>`, stb.)
- ASS stílus kódok eltávolítása (`{\an8}`, `{\pos()}`, stb.)
- Whitespace normalizálás

#### LipSyncEstimator (`services/lip_sync.py`)

Magyar beszédsebesség alapján becsüli a lip-sync megfelelőséget.

```python
class LipSyncEstimator:
    def __init__(self, chars_per_second: float = 13.0)
    
    def estimate(self, text: str, duration_ms: int) -> LipSyncResult
    def estimate_cue(self, cue: Cue) -> LipSyncResult
    def update_cue_ratio(self, cue: Cue) -> float
    def calculate_max_chars(self, duration_ms: int) -> int

@dataclass
class LipSyncResult:
    text_length: int
    available_time_ms: int
    estimated_time_ms: int
    ratio: float
    status: LipSyncStatus  # GOOD, WARNING, TOO_LONG
```

**Státusz határok:**
- `GOOD`: ratio ≤ 0.95 (Zöld)
- `WARNING`: 0.95 < ratio ≤ 1.0 (Sárga)
- `TOO_LONG`: ratio > 1.0 (Piros)

#### PDFExporter (`services/pdf_export.py`)

Klasszikus magyar szinkronkönyv formátumú PDF generálás.

```python
class PDFExporter:
    def export(
        self,
        project: Project,
        cues: list[Cue],
        output_path: Path,
        config: PDFExportConfig | None = None
    ) -> bool

@dataclass
class PDFExportConfig:
    page_size: str = "A4"
    font_size: int = 10
    include_source: bool = True
    include_translated: bool = True
    include_timecodes: bool = True
    layout: str = "standard"  # vagy "bilingual_columns"
```

#### ProjectManager (`services/project_manager.py`)

Magas szintű projektkezelési műveletek.

```python
class ProjectManager:
    def create_project(self, path: Path, title: str, **kwargs) -> Project
    def open_project(self, path: Path) -> Project
    def close_project(self) -> None
    def save_project(self) -> None
    
    def import_srt(self, srt_path: Path, replace_existing: bool = True) -> tuple[list[Cue], list[str]]
    def export_srt(self, output_path: Path, use_translated: bool = True) -> None
    
    def get_all_cues(self) -> list[Cue]
    def update_cue(self, cue: Cue) -> None
    def link_video(self, video_path: Path) -> None
```

### 4. UI réteg

#### MainWindow (`ui/main_window.py`)

A főablak felépítése:

```
┌─────────────────────────────────────────────────────────┐
│ Menü: Fájl | Szerkesztés | Nézet | Eszközök | Súgó      │
├─────────────────────────────────────────────────────────┤
│ Eszköztár: [Új][Megnyitás][Mentés] | [Import][Export]   │
├────────────────────┬────────────────────────────────────┤
│                    │                                    │
│    Cue Lista       │       Videó Lejátszó              │
│    (QTableView)    │       (QVideoWidget)              │
│                    │                                    │
│                    ├────────────────────────────────────┤
│                    │                                    │
│                    │       Cue Szerkesztő              │
│                    │       - Forrás szöveg             │
│                    │       - Fordítás                  │
│                    │       - Lip-sync mutató           │
│                    │                                    │
├────────────────────┴────────────────────────────────────┤
│ [Dokkolható] Megjegyzések Panel                         │
├─────────────────────────────────────────────────────────┤
│ Státusz: Projekt neve | Cue: 15/120 | Lip-sync: OK      │
└─────────────────────────────────────────────────────────┘
```

#### Komponensek:

- **CueListWidget** (`ui/cue_list.py`): QTableView + custom model
- **CueEditorWidget** (`ui/cue_editor.py`): Szövegszerkesztő lip-sync mutatóval
- **VideoPlayerWidget** (`ui/video_player.py`): QMediaPlayer wrapper
- **CommentsPanelWidget** (`ui/comments_panel.py`): Dokkolható megjegyzések
- **SettingsDialog** (`ui/settings_dialog.py`): Beállítások ablak

#### Főablak menüstruktúra

```
Fájl
├── Új projekt (Ctrl+N)
├── Megnyitás (Ctrl+O)
├── Mentés (Ctrl+S)
├── ─────────────
├── Alkalmazás beállítások (Ctrl+,)
└── Kilépés (Ctrl+Q)

Szerkesztés
├── Visszavonás (Ctrl+Z)
├── Újra (Ctrl+Y)
├── ─────────────
├── Keresés (Ctrl+F)
└── Csere (Ctrl+H)

Nézet
├── Teljes képernyő (F11)
├── ─────────────
├── Megjegyzések panel
└── [Plugin panelek...]

Eszközök
├── Import SRT
├── Export...
├── ─────────────
└── [Plugin menük...]
```

### 5. Plugin rendszer

A DubSync plugin rendszere hat fő plugin típust támogat:

```python
from enum import Enum

class PluginType(Enum):
    EXPORT = "export"      # Export formátumok
    QA = "qa"              # Minőségellenőrzés
    IMPORT = "import"      # Import formátumok
    TOOL = "tool"          # Általános eszközök
    UI = "ui"              # UI elemek (panelek, menük)
    SERVICE = "service"    # Háttérszolgáltatások
```

#### Plugin alap osztályok

```python
# Alap interfész (minden plugin)
class PluginInterface(ABC):
    @property
    @abstractmethod
    def info(self) -> PluginInfo: ...
    
    def activate(self) -> None: ...
    def deactivate(self) -> None: ...

# Export plugin
class ExportPlugin(PluginInterface):
    @property
    @abstractmethod
    def file_extension(self) -> str: ...
    
    @abstractmethod
    def export(self, cues: list[Cue], output_path: Path, **options) -> bool: ...

# QA plugin
class QAPlugin(PluginInterface):
    @abstractmethod
    def check_cue(self, cue: Cue) -> list[dict]: ...

# UI plugin (ÚJ)
class UIPlugin(PluginInterface):
    def create_dock_widget(self) -> Optional[QDockWidget]: ...
    def create_menu_items(self) -> List[QAction]: ...
    def on_cue_selected(self, cue: Cue) -> None: ...
    def on_project_opened(self, project: Project) -> None: ...
    def on_project_closed(self) -> None: ...

# Service plugin (ÚJ)
class ServicePlugin(PluginInterface):
    def start(self) -> None: ...
    def stop(self) -> None: ...

# Translation plugin (ÚJ)
class TranslationPlugin(ServicePlugin):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...
    def get_supported_languages(self) -> List[tuple]: ...
```

#### Plugin Manager

```python
class PluginManager:
    export_plugins: List[ExportPlugin]
    qa_plugins: List[QAPlugin]
    ui_plugins: List[UIPlugin]
    service_plugins: List[ServicePlugin]
    translation_plugins: List[TranslationPlugin]
    
    def register(self, plugin: PluginInterface) -> None
    def unregister(self, plugin_id: str) -> None
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]
    def enable_plugin(self, plugin_id: str) -> None
    def disable_plugin(self, plugin_id: str) -> None
```

#### Plugin regisztráció

```python
from dubsync.plugins.registry import PluginRegistry

registry = PluginRegistry()
registry.discover_builtin()  # Beépített plugin-ek
registry.load_from_directory(plugins_dir)  # Külső plugin-ek
```

### 6. Settings rendszer (ÚJ)

A `SettingsManager` kezeli az alkalmazás beállításait.

```python
@dataclass
class AppSettings:
    # Általános
    default_project_dir: str
    default_author: str
    autosave_enabled: bool
    autosave_interval: int
    
    # Lip-sync
    lip_sync_chars_per_second: float
    lip_sync_source_language: str
    lip_sync_ignore_brackets: bool
    
    # UI
    theme: str
    custom_colors: Dict[str, str]
    
    # Pluginok
    enabled_plugins: List[str]
    plugin_settings: Dict[str, Dict]

class SettingsManager:
    _instance: Optional["SettingsManager"] = None
    
    @classmethod
    def instance(cls) -> "SettingsManager": ...
    
    def load(self) -> AppSettings: ...
    def save(self, settings: AppSettings) -> None: ...
    def get_plugin_settings(self, plugin_id: str) -> dict: ...
    def set_plugin_settings(self, plugin_id: str, settings: dict) -> None: ...
    
    @property
    def config_dir(self) -> Path: ...  # Platform-specifikus
    
    @property
    def plugins_dir(self) -> Path: ...
```

**Konfiguráció tárolás:**

- **Windows**: `%APPDATA%\dubsync\settings.json`
- **macOS**: `~/Library/Application Support/dubsync/settings.json`
- **Linux**: `~/.config/dubsync/settings.json`

## Adatfolyam

### SRT Import folyamat

```
SRT Fájl
    │
    ▼
SRTParser.parse_file()
    │
    ├─► Kódolás detektálás
    ├─► HTML/ASS tag tisztítás
    ├─► Időkód parse
    │
    ▼
list[SRTEntry]
    │
    ▼
SRTParser.get_cues(project_id)
    │
    ▼
list[Cue]
    │
    ▼
ProjectManager.import_srt()
    │
    ├─► Meglévő cue-k törlése (opcionális)
    ├─► Új cue-k mentése DB-be
    │
    ▼
UI frissítés
```

### Lip-sync számítás

```
Cue szerkesztése
    │
    ▼
CueEditor.on_text_changed()
    │
    ▼
LipSyncEstimator.estimate_cue()
    │
    ├─► Szöveg normalizálás
    ├─► Karakterszám / idő számítás
    ├─► Ratio meghatározás
    ├─► Státusz beállítás
    │
    ▼
LipSyncResult
    │
    ▼
UI lip-sync mutató frissítés
```

## Konfiguráció

### Konstansok (`utils/constants.py`)

```python
# Alapértelmezett értékek
DEFAULT_FRAME_RATE = 25.0
CHARS_PER_SECOND_NORMAL = 13.0

# Lip-sync küszöbök
LIPSYNC_WARNING_THRESHOLD = 0.95
LIPSYNC_ERROR_THRESHOLD = 1.0

# Színek
COLOR_LIPSYNC_GOOD = "#4CAF50"      # Zöld
COLOR_LIPSYNC_WARNING = "#FFC107"   # Sárga
COLOR_LIPSYNC_TOO_LONG = "#F44336"  # Piros

# Cue státuszok
class CueStatus:
    NEW = "new"
    TRANSLATED = "translated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
```

## Tesztelési stratégia

### Unit tesztek

Minden modul saját teszt fájllal rendelkezik:

- `test_time_utils.py` - Időkezelő függvények
- `test_srt_parser.py` - SRT beolvasás
- `test_lip_sync.py` - Lip-sync becslés
- `test_database.py` - Adatbázis műveletek
- `test_models.py` - Model CRUD
- `test_project_manager.py` - Projektkezelés
- `test_pdf_export.py` - PDF generálás
- `test_plugins.py` - Plugin rendszer

### Fixture-ök (`conftest.py`)

```python
@pytest.fixture
def temp_dir():
    """Ideiglenes könyvtár tesztekhez."""

@pytest.fixture
def memory_db():
    """Memória adatbázis."""

@pytest.fixture
def sample_project(memory_db):
    """Minta projekt adatokkal."""

@pytest.fixture
def sample_cues():
    """Minta cue lista."""
```

## Bővítési lehetőségek

1. **Új export formátumok**: ExportPlugin implementálása
2. **QA szabályok**: QAPlugin implementálása
3. **UI elemek**: UIPlugin dokkolható panelekkel
4. **Fordító szolgáltatások**: TranslationPlugin implementálása
5. **Videó formátumok**: Codec plugin-ek
6. **Felhő szinkron**: Cloud service integráció
7. **Együttműködés**: WebSocket alapú valós idejű szinkron

## Fájl struktúra

```
dubsync/
├── docs/
│   ├── ARCHITECTURE.md     # Ez a dokumentum
│   └── PLUGIN_DEVELOPMENT.md
├── src/
│   └── dubsync/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py          # Alkalmazás entry point
│       ├── main.py
│       ├── models/         # Adatmodell réteg
│       │   ├── database.py
│       │   ├── project.py
│       │   ├── cue.py
│       │   └── comment.py
│       ├── services/       # Üzleti logika réteg
│       │   ├── srt_parser.py
│       │   ├── lip_sync.py
│       │   ├── pdf_export.py
│       │   ├── project_manager.py
│       │   └── settings_manager.py  # ÚJ
│       ├── plugins/        # Plugin rendszer
│       │   ├── base.py
│       │   ├── registry.py
│       │   └── builtin/
│       │       ├── basic_qa.py
│       │       ├── csv_export.py
│       │       └── translator/  # ÚJ
│       ├── ui/             # Felhasználói felület
│       │   ├── main_window.py
│       │   ├── cue_list.py
│       │   ├── cue_editor.py
│       │   ├── video_player.py
│       │   ├── comments_panel.py
│       │   ├── settings_dialog.py  # ÚJ
│       │   ├── dialogs.py
│       │   └── theme.py
│       └── utils/
│           ├── constants.py
│           └── time_utils.py
├── tests/
├── run.bat                 # Windows indító script
├── run.ps1                 # PowerShell indító script
├── requirements.txt
└── README.md
```
