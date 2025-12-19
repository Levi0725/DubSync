# DubSync - Professional Dubbing Translation Editor

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010+-lightgrey.svg)]()

> 🇭🇺 [Magyar verzió / Hungarian version](docs/README_HU.md)

DubSync is a professional Windows desktop application for dubbing translators and directors. The application enables efficient creation of dubbed translations with frame-accurate lip-sync.

## 🎬 Key Features

### Project Management
- **Custom .dubsync format**: Portable SQLite-based project files
- **Auto-save**: Never lose your work
- **Recent projects**: Quick access to previous work

### SRT Import/Export
- **Multiple encodings**: UTF-8, UTF-8 BOM, CP1250, ISO-8859-2
- **Smart cleanup**: Automatic removal of HTML and ASS tags
- **Bidirectional**: Both import and export supported

### Video Playback
- **Embedded player**: No external software required
- **Segment playback**: Play only the current cue
- **Speed control**: 0.5x - 2.0x speed
- **Frame-accurate navigation**: Step forward/backward by frames

### Lip-Sync Estimation
- **Real-time analysis**: Results update while typing
- **Optimized for Hungarian**: 13 characters/second default
- **Source language consideration**: Time frame calculated based on English speech rate
- **Bracket content ignored**: Director instructions don't count
- **Visual feedback**: Color-coded status (green/yellow/red)

### Review Comments
- **Cue-level comments**: Separate notes for each text
- **Resolution tracking**: Resolved/unresolved status
- **Team collaboration**: Multiple reviewers can work together

### PDF Export
- **Classic dubbing script format**: Industry standard
- **Full Unicode support**: Including accented characters
- **Bilingual option**: Source and target language side by side

### Plugin System
- **Extensible architecture**: Write your own plugins
- **Plugin types**: Export, QA, UI extensions, services
- **Built-in plugins**:
  - 🌍 Argos Translator: Offline English-Hungarian translator
  - CSV Export: Spreadsheet export
  - Basic QA: Basic quality assurance checks

### Settings
- **Themes**: Dark, light, custom colors
- **General settings**: Save location, user data
- **Plugin management**: Enable/disable plugins, configure settings

## 📋 System Requirements

- **Operating System**: Windows 10 or later
- **Python**: 3.10+
- **RAM**: minimum 4 GB
- **Storage**: ~100 MB (+ project sizes)
- **Video codecs**: Windows Media Foundation supported formats

## 🚀 Installation

### Quick Start (recommended)

```bash
# Clone the repository
git clone https://github.com/Levi0725/DubSync.git
cd dubsync

# Launch (automatically sets up the environment)
.\run.ps1   # PowerShell
# or
run.bat     # Command Prompt
```

### Manual Installation

#### 1. Clone the repository

```bash
git clone https://github.com/Levi0725/DubSync.git
cd dubsync
```

#### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Launch the application

```bash
python -m dubsync
```

Or in development mode:

```bash
pip install -e .
dubsync
```

## 📖 Usage

### Create a New Project

1. `File > New Project` (Ctrl+N)
2. Choose the save location and name
3. Set the source and target languages

### SRT Import

1. `File > Import SRT` (Ctrl+I)
2. Select the SRT file
3. Cues are loaded automatically

### Attach Video

1. `File > Attach Video`
2. Select the video file (MP4, AVI, MKV, etc.)
3. Video appears in the player

### Translation

1. Click on a cue in the list
2. Enter the translation in the editor
3. The lip-sync indicator updates in real-time
4. `Save` button → automatically jumps to the next line

### Settings

1. `File > Application Settings` (Ctrl+,)
2. Configure general options
3. Manage plugins (restart required)
4. Select a theme

### PDF Export

1. `File > PDF Export` (Ctrl+E)
2. Choose the format
3. Set the options
4. Save the PDF

## ⌨️ Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| Ctrl+N | New project |
| Ctrl+O | Open project |
| Ctrl+S | Save |
| Ctrl+I | Import SRT |
| Ctrl+E | PDF export |
| Space | Play/pause video |
| F5 | Segment playback |
| , | Previous frame |
| . | Next frame |
| Ctrl+↑ | Previous cue |
| Ctrl+↓ | Next cue |
| Ctrl+F | Search |
| F11 | Fullscreen |

## 🔌 Plugin Development

### Export Plugin Example

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

### QA Plugin Example

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
                "message": "Text too long"
            })
        return issues
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Coverage measurement
pytest --cov=dubsync --cov-report=html
```

## 📁 Project Structure

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

MIT License - see the [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- Qt/PySide6 - GUI framework
- ReportLab - PDF generation
- SQLite - Database engine

## 📞 Contact

Bug reports and feature requests: [GitHub Issues](https://github.com/Levi0725/DubSync/issues)
