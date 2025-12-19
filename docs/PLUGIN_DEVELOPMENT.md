# Plugin Development Guide

> 🇭🇺 [Magyar verzió / Hungarian version](PLUGIN_DEVELOPMENT_HU.md)

This document explains how to create custom plugins for the DubSync application.

## Overview

The DubSync plugin system supports seven main plugin types:

1. **Export Plugins**: Add new export formats
2. **QA Plugins**: Quality assurance rules
3. **UI Plugins**: Add new windows, panels, menus
4. **Service Plugins**: Background services (APIs, translators)
5. **Translation Plugins**: Translation services
6. **Import Plugins**: Import custom formats
7. **Language Plugins**: Add new interface languages

## Important Notes

- **Plugins are disabled by default** - Users must manually enable them
- **Restart required** - Plugin changes only take effect after restart
- **README.md required** - Every plugin must have detailed documentation

## Basic Requirements

### Plugin File Structure

```
my_plugin/
├── __init__.py       # Plugin class and export
├── README.md         # Detailed documentation (required)
└── requirements.txt  # Dependencies (optional)
```

### Minimal Plugin

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
            author="Your Name",
            description="Short plugin description",
            plugin_type=PluginType.TOOL,
            icon="🔧",
            readme_path="README.md"
        )

# Plugin export (required!)
Plugin = MyPlugin
```

---

## PluginInfo Dataclass

Every plugin must provide the `info` property:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class PluginDependency:
    """Plugin dependency description."""
    package: str          # pip package name
    version: str = ""     # Version specification
    optional: bool = False

@dataclass
class PluginInfo:
    id: str                                    # Unique identifier
    name: str                                  # Display name
    version: str                               # Version (SemVer)
    author: str                                # Author name
    description: str                           # Short description
    plugin_type: PluginType                    # Plugin type
    dependencies: List[PluginDependency] = field(default_factory=list)
    homepage: str = ""                         # Project URL
    readme_path: str = ""                      # README.md relative path
    icon: str = ""                             # Emoji or icon
```

---

## Plugin Types

### 1. Export Plugin

Add new export formats.

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

Quality assurance rules.

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

### 3. UI Plugin

Add custom windows, panels, menus.

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
        """Create a new dockable panel."""
        dock = QDockWidget("My Panel")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello from plugin!"))
        dock.setWidget(widget)
        return dock
    
    def create_menu_items(self) -> list[QAction]:
        """Add menu items."""
        action = QAction("My Action", self._main_window)
        action.triggered.connect(self._on_action)
        return [action]
    
    def _on_action(self):
        print("Menu action triggered!")
    
    def on_cue_selected(self, cue) -> None:
        """Called when a cue is selected."""
        print(f"Selected cue: {cue.cue_index}")
    
    def on_project_opened(self, project) -> None:
        """Called when project is opened."""
        print(f"Project opened: {project.title}")
    
    def on_project_closed(self) -> None:
        """Called when project is closed."""
        print("Project closed")

Plugin = MyDockPlugin
```

#### UIPlugin Interface

| Method | Description |
|--------|-------------|
| `create_dock_widget()` | Create dockable panel |
| `create_menu_items()` | QAction list for menu |
| `create_toolbar_items()` | QAction list for toolbar |
| `on_cue_selected(cue)` | Cue selection event |
| `on_project_opened(project)` | Project open event |
| `on_project_closed()` | Project close event |

### 4. Service Plugin

Background services (APIs, processors).

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
        """Start service."""
        print("Spell check service started")
    
    def stop(self) -> None:
        """Stop service."""
        print("Spell check service stopped")
    
    def check_spelling(self, text: str) -> list[str]:
        """Custom method for spell checking."""
        # Implementation...
        return []

Plugin = SpellCheckService
```

### 5. Translation Plugin

Implement translation services.

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
        """Translate text."""
        import deepl
        translator = deepl.Translator("YOUR_API_KEY")
        result = translator.translate_text(text, target_lang=target_lang)
        return result.text
    
    def get_supported_languages(self) -> list[tuple]:
        """List of supported languages."""
        return [
            ("en", "English"),
            ("hu", "Hungarian"),
            ("de", "German"),
            ("fr", "French"),
        ]

Plugin = DeepLTranslatorPlugin
```

---

## Internationalization (i18n)

DubSync provides a built-in internationalization system that plugins can use to support multiple languages. **Plugins must have their own `locales/` directory** - they cannot modify the core application's locale files.

### Plugin Locale File Structure

```
my_plugin/
├── __init__.py       # Plugin class
├── README.md         # Documentation
├── requirements.txt  # Dependencies (optional)
└── locales/          # Plugin translations (required for i18n)
    ├── en.json       # English translations (required - fallback)
    └── hu.json       # Hungarian translations
```

### Creating Locale Files

Create JSON files in your plugin's `locales/` directory:

**locales/en.json** (English - required as fallback):
```json
{
  "name": "My Plugin",
  "description": "Plugin description",
  "panel_title": "🔧 My Plugin Panel",
  "welcome_message": "Welcome to My Plugin!",
  "action_button": "Do Something",
  "action_tooltip": "Click to perform action",
  "status_ready": "✅ Ready",
  "status_error": "❌ Error: {error}",
  "menu_item": "🔧 My Plugin"
}
```

**locales/hu.json** (Hungarian):
```json
{
  "name": "Saját Plugin",
  "description": "Plugin leírása",
  "panel_title": "🔧 Saját Plugin Panel",
  "welcome_message": "Üdvözöl a Saját Plugin!",
  "action_button": "Művelet",
  "action_tooltip": "Kattints a művelet végrehajtásához",
  "status_ready": "✅ Kész",
  "status_error": "❌ Hiba: {error}",
  "menu_item": "🔧 Saját Plugin"
}
```

### Using the Translation Function

```python
from dubsync.i18n import t

class MyPlugin(UIPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="my_plugin",  # This ID is used in translation keys
            # ...
        )
    
    def create_dock_widget(self) -> QDockWidget:
        # Use t() with "plugins.{plugin_id}.{key}" pattern
        dock = QDockWidget(t("plugins.my_plugin.panel_title"))
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # All UI strings should use t()
        label = QLabel(t("plugins.my_plugin.welcome_message"))
        button = QPushButton(t("plugins.my_plugin.action_button"))
        button.setToolTip(t("plugins.my_plugin.action_tooltip"))
        
        layout.addWidget(label)
        layout.addWidget(button)
        dock.setWidget(widget)
        return dock
```

### Automatic Locale Loading

Plugin locales are **automatically loaded** when the plugin initializes. The base `PluginInterface.initialize()` method handles this. If you override `initialize()`, make sure to call `super().initialize()`:

```python
def initialize(self) -> bool:
    """Plugin initialization."""
    super().initialize()  # This loads locale files from locales/
    # Your custom initialization...
    return True
```

### Translation Key Naming Convention

| Key Pattern | Usage |
|-------------|-------|
| `plugins.{id}.name` | Plugin display name |
| `plugins.{id}.description` | Plugin description |
| `plugins.{id}.panel` | Dock panel title |
| `plugins.{id}.menu_*` | Menu item labels |
| `plugins.{id}.status_*` | Status messages |
| `plugins.{id}.*_btn` | Button labels |
| `plugins.{id}.*_tooltip` | Tooltip texts |
| `plugins.{id}.*_placeholder` | Input placeholders |

### Parameterized Translations

Use Python's `.format()` for dynamic values:

```python
# In locale file:
# "items_found": "Found {count} items"
# "error_message": "Error: {error}"

label.setText(t("plugins.my_plugin.items_found").format(count=5))
status.setText(t("plugins.my_plugin.error_message").format(error=str(e)))
```

### Supported Languages

Currently supported languages:
- **English (en)** - Default/fallback language
- **Hungarian (hu)**

---

## Plugin Settings

Plugins can store their own settings through the SettingsManager:

```python
from dubsync.services.settings_manager import SettingsManager

class MyConfigurablePlugin(UIPlugin):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
    
    def get_settings(self) -> dict:
        """Get plugin settings."""
        return self.settings.get_plugin_settings(self.info.id)
    
    def save_settings(self, settings: dict):
        """Save plugin settings."""
        self.settings.set_plugin_settings(self.info.id, settings)
    
    @property
    def api_key(self) -> str:
        return self.get_settings().get("api_key", "")
```

### Displaying Settings

Plugins can define custom settings:

```python
def get_settings_schema(self) -> dict:
    """JSON Schema for settings UI."""
    return {
        "type": "object",
        "properties": {
            "api_key": {
                "type": "string",
                "title": "API Key",
                "description": "Your API key"
            },
            "max_chars": {
                "type": "integer",
                "title": "Maximum characters",
                "default": 5000
            }
        }
    }
```

---

## Plugin Registration

### Automatic Loading

Place your plugin in the following location:

**Windows:** `src\dubsync\plugins\`  

```
plugins/
└── my_plugin/
    ├── __init__.py    # Plugin = MyPlugin
    └── README.md      # Required!
```

### Programmatic Registration

```python
from dubsync.plugins.registry import PluginRegistry
from my_plugin import MyPlugin

registry = PluginRegistry()
plugin = MyPlugin()
registry.register(plugin)
```

---

## Issue Severity Levels

| Severity | Meaning | UI Display |
|----------|---------|------------|
| `error` | Critical error | 🔴 Red |
| `warning` | Warning | 🟡 Yellow |
| `info` | Information | 🔵 Blue |

---

## README.md Requirements

Every plugin **must** contain a `README.md` file:

```markdown
# Plugin Name

Short description of the plugin.

## Installation

Install required dependencies:
\`\`\`bash
pip install package_name
\`\`\`

## Usage

Description of how to use the plugin.

## Settings

| Setting | Type | Description |
|---------|------|-------------|
| api_key | string | API key |

## Changelog

### 1.0.0
- Initial release
```

---

## Testing

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
        # Plugin-specific tests
        pass
```

---

## Best Practices

1. **Unique ID**: Use a unique, descriptive plugin ID
2. **Versioning**: Use SemVer format (1.0.0)
3. **Dependencies**: Declare in PluginDependency
4. **README.md**: Detailed documentation
5. **Error handling**: Proper exception handling
6. **Async operations**: Use QThread for long operations
7. **Internationalization**: Use `t()` function for all UI strings
8. **Locale keys**: Follow naming convention `plugins.{plugin_id}.{key}`
9. **Both languages**: Add translations to both `en.json` and `hu.json`

---

## Built-in Plugin Examples

| Plugin | Type | Description |
|--------|------|-------------|
| [csv_export](../src/dubsync/plugins/builtin/csv_export/) | Export | CSV export |
| [basic_qa](../src/dubsync/plugins/builtin/basic_qa/) | QA | Basic checks |
| [glossary](../src/dubsync/plugins/builtin/glossary/) | UI | Translation glossary |
| [translator](../src/dubsync/plugins/builtin/translator/) | UI + Service | Argos translator |
| [spellchecker](../src/dubsync/plugins/builtin/spellchecker/) | UI | Spell checker |

---

## Help

- **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: GitHub Issues
- **Examples**: `src/dubsync/plugins/builtin/`
