# Contributing to DubSync

Thank you for your interest in contributing to the DubSync project! 🎬

## 🐛 Bug Reports

If you found a bug, please open an Issue and include:

1. **Bug description** - What happened?
2. **Expected behavior** - What should have happened?
3. **Reproduction steps** - How can the bug be reproduced?
4. **Environment** - Windows version, Python version
5. **Screenshot** - If relevant

## 💡 Feature Requests

If you'd like a new feature, open an Issue and describe:

1. **Feature description** - What would it do?
2. **Why is it useful?** - Who would use it and when?
3. **Examples** - How would it look in practice?

## 🔧 Creating a Pull Request

### Prerequisites

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/dubsync.git`
3. Create a branch: `git checkout -b feature/new-feature`

### Code Style

- Follow PEP 8
- Use type annotations where possible
- Write docstrings for all public methods
- Keep user-facing messages clear and descriptive

### Tests

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_models.py -v
```

### Commit Messages

```
feat: New feature description
fix: Bug fix description
docs: Documentation changes
refactor: Code refactoring
test: Test additions/modifications
```

### Submitting PR

1. Push your changes: `git push origin feature/new-feature`
2. Open a Pull Request
3. Describe your changes in detail
4. Wait for review

## 📋 Development Guide

### Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Project Structure

```
src/dubsync/
├── models/      # Data models (Project, Cue, Comment)
├── services/    # Business logic (ProjectManager, PDFExporter)
├── ui/          # Qt widgets and dialogs
├── plugins/     # Plugin system
└── utils/       # Utility functions
```

### Plugin Development

See: [docs/PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md)

## 📜 License

Your contributions will be published under the MIT license.
