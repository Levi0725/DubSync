# Plugin Fejlesztési Útmutató

Ez a dokumentum bemutatja, hogyan készíthetsz saját plugin-eket a DubSync alkalmazáshoz.

## Áttekintés

A DubSync plugin rendszere hat fő plugin típust támogat:

1. **Export Plugin-ek**: Új export formátumok hozzáadása
2. **QA Plugin-ek**: Minőségellenőrzési szabályok
3. **UI Plugin-ek**: Új ablakok, panelek, menük hozzáadása
4. **Service Plugin-ek**: Háttérszolgáltatások (API-k, fordítók)
5. **Translation Plugin-ek**: Fordító szolgáltatások
6. **Import Plugin-ek**: Egyedi formátumok importálása

## Fontos tudnivalók

- **A pluginok alapból le vannak tiltva** - A felhasználónak kézzel kell engedélyezni
- **Újraindítás szükséges** - A plugin változások csak újraindítás után lépnek érvénybe
- **README.md kötelező** - Minden pluginnak legyen részletes leírása

## Alap követelmények

### Plugin fájl struktúra

```
my_plugin/
├── __init__.py       # Plugin osztály és export
├── README.md         # Részletes dokumentáció (kötelező)
└── requirements.txt  # Függőségek (opcionális)
```

### Minimális plugin

```python
# my_plugin/__init__.py

from dubsync.plugins.base import PluginInterface, PluginInfo, PluginType

class MyPlugin(PluginInterface):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="my_plugin",
            name="My Plugin",
            version="1.0.0",
            author="A neved",
            description="Plugin rövid leírása",
            plugin_type=PluginType.TOOL,
            icon="🔧",
            readme_path="README.md"
        )

# Plugin export (kötelező!)
Plugin = MyPlugin
```

---

## PluginInfo dataclass

Minden pluginnak kötelező megadni az `info` property-t:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class PluginDependency:
    """Plugin függőség leírása."""
    package: str          # pip csomag neve
    version: str = ""     # Verzió specifikáció
    optional: bool = False

@dataclass
class PluginInfo:
    id: str                                    # Egyedi azonosító
    name: str                                  # Megjelenített név
    version: str                               # Verzió (SemVer)
    author: str                                # Szerző neve
    description: str                           # Rövid leírás
    plugin_type: PluginType                    # Plugin típus
    dependencies: List[PluginDependency] = field(default_factory=list)
    homepage: str = ""                         # Projekt URL
    readme_path: str = ""                      # README.md relatív út
    icon: str = ""                             # Emoji vagy ikon
```

---

## Plugin típusok

### 1. Export Plugin

Új export formátumok hozzáadása.

```python
from dubsync.plugins.base import ExportPlugin, PluginInfo, PluginType

class JSONExportPlugin(ExportPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="json_export",
            name="JSON Export",
            version="1.0.0",
            author="Developer",
            description="Export cues to JSON format",
            plugin_type=PluginType.EXPORT,
            icon="📄"
        )
    
    @property
    def file_extension(self) -> str:
        return ".json"
    
    def export(self, cues: list, output_path: Path, **options) -> bool:
        import json
        data = [{"index": c.cue_index, "text": c.translated_text} for c in cues]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

Plugin = JSONExportPlugin
```

### 2. QA Plugin

Minőségellenőrzési szabályok.

```python
from dubsync.plugins.base import QAPlugin, PluginInfo, PluginType

class LengthCheckPlugin(QAPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="length_check",
            name="Length Check",
            version="1.0.0",
            author="Developer",
            description="Check text length limits",
            plugin_type=PluginType.QA,
            icon="📏"
        )
    
    def check_cue(self, cue) -> list[dict]:
        issues = []
        if len(cue.translated_text) > 84:
            issues.append({
                "severity": "warning",
                "code": "TOO_LONG",
                "message": f"Text too long ({len(cue.translated_text)} chars)",
                "cue_id": cue.id,
                "cue_index": cue.cue_index
            })
        return issues

Plugin = LengthCheckPlugin
```

### 3. UI Plugin ⭐ ÚJ

Saját ablakok, panelek, menük hozzáadása.

```python
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QAction
from dubsync.plugins.base import UIPlugin, PluginInfo, PluginType

class MyDockPlugin(UIPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="my_dock_plugin",
            name="My Dock Panel",
            version="1.0.0",
            author="Developer",
            description="Example dock widget plugin",
            plugin_type=PluginType.UI,
            icon="🎨"
        )
    
    def create_dock_widget(self) -> QDockWidget:
        """Létrehoz egy új dokkolható panelt."""
        dock = QDockWidget("My Panel")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello from plugin!"))
        dock.setWidget(widget)
        return dock
    
    def create_menu_items(self) -> list[QAction]:
        """Menü elemek hozzáadása."""
        action = QAction("My Action", self._main_window)
        action.triggered.connect(self._on_action)
        return [action]
    
    def _on_action(self):
        print("Menu action triggered!")
    
    def on_cue_selected(self, cue) -> None:
        """Meghívódik amikor cue-t választanak ki."""
        print(f"Selected cue: {cue.cue_index}")
    
    def on_project_opened(self, project) -> None:
        """Meghívódik projekt megnyitásakor."""
        print(f"Project opened: {project.title}")
    
    def on_project_closed(self) -> None:
        """Meghívódik projekt bezárásakor."""
        print("Project closed")

Plugin = MyDockPlugin
```

#### UIPlugin interfész

| Metódus | Leírás |
|---------|--------|
| `create_dock_widget()` | Dokkolható panel létrehozása |
| `create_menu_items()` | QAction lista menühöz |
| `create_toolbar_items()` | QAction lista eszköztárhoz |
| `on_cue_selected(cue)` | Cue kiválasztás esemény |
| `on_project_opened(project)` | Projekt megnyitás esemény |
| `on_project_closed()` | Projekt bezárás esemény |

### 4. Service Plugin ⭐ ÚJ

Háttérszolgáltatások (API-k, processzorok).

```python
from dubsync.plugins.base import ServicePlugin, PluginInfo, PluginType

class SpellCheckService(ServicePlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="spell_check",
            name="Spell Checker",
            version="1.0.0",
            author="Developer",
            description="Background spell checking service",
            plugin_type=PluginType.SERVICE,
            icon="✍️"
        )
    
    def start(self) -> None:
        """Szolgáltatás indítása."""
        print("Spell check service started")
    
    def stop(self) -> None:
        """Szolgáltatás leállítása."""
        print("Spell check service stopped")
    
    def check_spelling(self, text: str) -> list[str]:
        """Egyedi metódus a spell check-hez."""
        # Implementáció...
        return []

Plugin = SpellCheckService
```

### 5. Translation Plugin ⭐ ÚJ

Fordító szolgáltatások implementálása.

```python
from dubsync.plugins.base import TranslationPlugin, PluginInfo, PluginType, PluginDependency

class DeepLTranslatorPlugin(TranslationPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="deepl_translator",
            name="DeepL Translator",
            version="1.0.0",
            author="Developer",
            description="Translation via DeepL API",
            plugin_type=PluginType.SERVICE,
            dependencies=[
                PluginDependency("deepl", ">=1.0.0")
            ],
            icon="🌐"
        )
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Szöveg lefordítása."""
        import deepl
        translator = deepl.Translator("YOUR_API_KEY")
        result = translator.translate_text(text, target_lang=target_lang)
        return result.text
    
    def get_supported_languages(self) -> list[tuple]:
        """Támogatott nyelvek listája."""
        return [
            ("en", "English"),
            ("hu", "Hungarian"),
            ("de", "German"),
            ("fr", "French"),
        ]

Plugin = DeepLTranslatorPlugin
```

---

## Teljes példa: Argos Translator Plugin

Ez a plugin bemutatja az UIPlugin és TranslationPlugin kombinálását:

```python
# translator/__init__.py

from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QComboBox, QLabel
)
from PySide6.QtGui import QAction

from dubsync.plugins.base import (
    UIPlugin, TranslationPlugin, PluginInfo, 
    PluginType, PluginDependency
)


class TranslatorWorker(QThread):
    """Háttérszál a fordításhoz."""
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, plugin, text, src, tgt):
        super().__init__()
        self.plugin = plugin
        self.text = text
        self.src = src
        self.tgt = tgt
    
    def run(self):
        try:
            result = self.plugin.translate(self.text, self.src, self.tgt)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class TranslatorWidget(QWidget):
    """Fordító panel UI."""
    insert_translation = Signal(str)
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Nyelv választók
        lang_layout = QHBoxLayout()
        self.src_combo = QComboBox()
        self.tgt_combo = QComboBox()
        
        for code, name in self.plugin.get_supported_languages():
            self.src_combo.addItem(name, code)
            self.tgt_combo.addItem(name, code)
        
        lang_layout.addWidget(QLabel("Forrás:"))
        lang_layout.addWidget(self.src_combo)
        lang_layout.addWidget(QLabel("Cél:"))
        lang_layout.addWidget(self.tgt_combo)
        layout.addLayout(lang_layout)
        
        # Szöveg mezők
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("Forrás szöveg...")
        layout.addWidget(self.source_text)
        
        self.target_text = QTextEdit()
        self.target_text.setPlaceholderText("Lefordított szöveg...")
        self.target_text.setReadOnly(True)
        layout.addWidget(self.target_text)
        
        # Gombok
        btn_layout = QHBoxLayout()
        self.translate_btn = QPushButton("Fordítás")
        self.translate_btn.clicked.connect(self._translate)
        self.insert_btn = QPushButton("Beszúrás")
        self.insert_btn.clicked.connect(self._insert)
        btn_layout.addWidget(self.translate_btn)
        btn_layout.addWidget(self.insert_btn)
        layout.addLayout(btn_layout)
    
    def _translate(self):
        text = self.source_text.toPlainText()
        if not text:
            return
        
        src = self.src_combo.currentData()
        tgt = self.tgt_combo.currentData()
        
        self.worker = TranslatorWorker(self.plugin, text, src, tgt)
        self.worker.finished.connect(self._on_translated)
        self.worker.start()
    
    def _on_translated(self, result):
        self.target_text.setPlainText(result)
    
    def _insert(self):
        text = self.target_text.toPlainText()
        if text:
            self.insert_translation.emit(text)


class ArgosTranslatorPlugin(UIPlugin, TranslationPlugin):
    """Argos Translate plugin UI-val és fordítással."""
    
    def __init__(self):
        super().__init__()
        self._widget: Optional[TranslatorWidget] = None
        self._installed_languages = set()
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="argos_translator",
            name="Argos Fordító",
            version="1.0.0",
            author="Levente Kulacsy - Argos Translate Team",
            description="Offline fordítás Argos Translate-tel",
            plugin_type=PluginType.UI,
            dependencies=[
                PluginDependency("argostranslate", ">=1.9.0")
            ],
            homepage="https://github.com/argosopentech/argos-translate",
            readme_path="README.md",
            icon="🌐"
        )
    
    def create_dock_widget(self) -> QDockWidget:
        dock = QDockWidget("🌐 Fordító")
        self._widget = TranslatorWidget(self)
        dock.setWidget(self._widget)
        return dock
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        import argostranslate.translate
        return argostranslate.translate.translate(text, source_lang, target_lang)
    
    def get_supported_languages(self) -> List[tuple]:
        return [("en", "English"), ("hu", "Hungarian")]
    
    def on_cue_selected(self, cue) -> None:
        if self._widget and cue.source_text:
            self._widget.source_text.setPlainText(cue.source_text)


Plugin = ArgosTranslatorPlugin
```

---

## Plugin beállítások

A pluginok saját beállításokat tárolhatnak a SettingsManager-en keresztül:

```python
from dubsync.services.settings_manager import SettingsManager

class MyConfigurablePlugin(UIPlugin):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
    
    def get_settings(self) -> dict:
        """Plugin beállítások lekérése."""
        return self.settings.get_plugin_settings(self.info.id)
    
    def save_settings(self, settings: dict):
        """Plugin beállítások mentése."""
        self.settings.set_plugin_settings(self.info.id, settings)
    
    @property
    def api_key(self) -> str:
        return self.get_settings().get("api_key", "")
```

### Beállítások megjelenítése

A pluginok definiálhatnak egyedi beállításokat:

```python
def get_settings_schema(self) -> dict:
    """JSON Schema a beállítások UI-hoz."""
    return {
        "type": "object",
        "properties": {
            "api_key": {
                "type": "string",
                "title": "API Key",
                "description": "DeepL API kulcs"
            },
            "max_chars": {
                "type": "integer",
                "title": "Maximum karakterek",
                "default": 5000
            }
        }
    }
```

---

## Plugin regisztráció

### Automatikus betöltés

Helyezd a plugint a következő helyre:

**Windows:** `src\dubsync\plugins\`  

```
plugins/
└── my_plugin/
    ├── __init__.py    # Plugin = MyPlugin
    └── README.md      # Kötelező!
```

### Programatikus regisztráció

```python
from dubsync.plugins.registry import PluginRegistry
from my_plugin import MyPlugin

registry = PluginRegistry()
plugin = MyPlugin()
registry.register(plugin)
```

---

## Issue severity szintek

| Severity | Jelentés | UI megjelenés |
|----------|----------|---------------|
| `error` | Kritikus hiba | 🔴 Piros |
| `warning` | Figyelmeztetés | 🟡 Sárga |
| `info` | Információ | 🔵 Kék |

---

## README.md követelmények

Minden pluginnak **kötelező** tartalmaznia egy `README.md` fájlt:

```markdown
# Plugin Neve

Rövid leírás a pluginról.

## Telepítés

Szükséges függőségek telepítése:
\`\`\`bash
pip install package_name
\`\`\`

## Használat

A plugin használatának leírása.

## Beállítások

| Beállítás | Típus | Leírás |
|-----------|-------|--------|
| api_key | string | API kulcs |

## Changelog

### 1.0.0
- Első kiadás
```

---

## Tesztelés

```python
import pytest
from my_plugin import MyPlugin

class TestMyPlugin:
    @pytest.fixture
    def plugin(self):
        return MyPlugin()
    
    def test_info(self, plugin):
        assert plugin.info.id == "my_plugin"
        assert plugin.info.version == "1.0.0"
    
    def test_functionality(self, plugin):
        # Plugin specifikus tesztek
        pass
```

---

## Best Practices

1. **Egyedi ID**: Használj egyedi, leíró plugin ID-t
2. **Verziókezelés**: SemVer formátum (1.0.0)
3. **Függőségek**: Deklaráld a PluginDependency-ben
4. **README.md**: Részletes dokumentáció
5. **Hibakezelés**: Megfelelő exception kezelés
6. **Aszinkron műveletek**: QThread használata hosszú műveletekhez
7. **Lokalizáció**: Magyar nyelvű üzenetek

---

## Beépített plugin példák

| Plugin | Típus | Leírás |
|--------|-------|--------|
| [csv_export](../src/dubsync/plugins/builtin/csv_export.py) | Export | CSV exportálás |
| [basic_qa](../src/dubsync/plugins/builtin/basic_qa.py) | QA | Alapvető ellenőrzések |
| [translator](../src/dubsync/plugins/builtin/translator/) | UI + Service | Argos fordító |

---

## Segítség

- **Dokumentáció**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: GitHub Issues
- **Példák**: `src/dubsync/plugins/builtin/`
