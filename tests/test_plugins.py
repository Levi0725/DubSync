"""
DubSync Plugin System Tests

Plugin rendszer tesztjei.
"""

import pytest
from pathlib import Path
from typing import Optional, List, Dict, Any

from dubsync.plugins.base import (
    PluginInterface, PluginInfo, PluginType, PluginDependency,
    ExportPlugin, QAPlugin, QAIssue, UIPlugin, ServicePlugin,
    TranslationPlugin, PluginManager
)
from dubsync.models.project import Project
from dubsync.models.cue import Cue


# Mock plugin implementations for testing

class MockExportPlugin(ExportPlugin):
    """Teszt export plugin."""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="mock_export",
            name="Mock Export",
            version="1.0.0",
            author="Test",
            description="Mock export plugin for testing",
            plugin_type=PluginType.EXPORT
        )
    
    @property
    def file_extension(self) -> str:
        return ".mock"
    
    @property
    def file_filter(self) -> str:
        return "Mock Files (*.mock)"
    
    def export(
        self,
        output_path: Path,
        project: Project,
        cues: List[Cue],
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        Path(output_path).write_text("mock export content")
        return True


class MockQAPlugin(QAPlugin):
    """Teszt QA plugin."""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="mock_qa",
            name="Mock QA",
            version="1.0.0",
            author="Test",
            description="Mock QA plugin for testing",
            plugin_type=PluginType.QA
        )
    
    def check(
        self,
        project: Project,
        cues: List[Cue]
    ) -> List[QAIssue]:
        issues = []
        for cue in cues:
            if not cue.translated_text:
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="warning",
                    message="Empty translation"
                ))
        return issues


class MockUIPlugin(UIPlugin):
    """Teszt UI plugin."""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="mock_ui",
            name="Mock UI",
            version="1.0.0",
            author="Test",
            description="Mock UI plugin for testing",
            plugin_type=PluginType.UI
        )


class MockServicePlugin(ServicePlugin):
    """Teszt service plugin."""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="mock_service",
            name="Mock Service",
            version="1.0.0",
            author="Test",
            description="Mock service plugin for testing",
            plugin_type=PluginType.SERVICE
        )
    
    def get_service_name(self) -> str:
        return "mock_service"


class MockTranslationPlugin(TranslationPlugin):
    """Teszt fordító plugin."""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="mock_translator",
            name="Mock Translator",
            version="1.0.0",
            author="Test",
            description="Mock translation plugin for testing",
            plugin_type=PluginType.SERVICE
        )
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        return f"[{target_lang}] {text}"


class TestPluginInfo:
    """PluginInfo tesztek."""
    
    def test_create_plugin_info(self):
        """PluginInfo létrehozása."""
        info = PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            author="Tester",
            description="Test description",
            plugin_type=PluginType.EXPORT
        )
        
        assert info.id == "test_plugin"
        assert info.name == "Test Plugin"
        assert info.version == "1.0.0"
        assert info.plugin_type == PluginType.EXPORT
    
    def test_plugin_info_with_dependencies(self):
        """PluginInfo függőségekkel."""
        deps = [
            PluginDependency(package_name="numpy", min_version="1.0"),
            PluginDependency(package_name="pandas", optional=True)
        ]
        
        info = PluginInfo(
            id="test",
            name="Test",
            version="1.0.0",
            author="Test",
            description="Test",
            plugin_type=PluginType.TOOL,
            dependencies=deps
        )
        
        assert len(info.dependencies) == 2
        assert info.dependencies[0].package_name == "numpy"
        assert info.dependencies[1].optional is True
    
    def test_plugin_info_str(self):
        """PluginInfo string reprezentáció."""
        info = PluginInfo(
            id="test",
            name="Test Plugin",
            version="2.0.0",
            author="Author",
            description="Desc",
            plugin_type=PluginType.QA
        )
        
        string = str(info)
        assert "Test Plugin" in string
        assert "2.0.0" in string
        assert "Author" in string


class TestPluginInterface:
    """PluginInterface tesztek."""
    
    def test_export_plugin_interface(self):
        """Export plugin interface."""
        plugin = MockExportPlugin()
        
        assert plugin.info.name == "Mock Export"
        assert plugin.info.version == "1.0.0"
        assert plugin.file_extension == ".mock"
    
    def test_qa_plugin_interface(self):
        """QA plugin interface."""
        plugin = MockQAPlugin()
        
        assert plugin.info.name == "Mock QA"
        assert plugin.info.plugin_type == PluginType.QA
    
    def test_ui_plugin_interface(self):
        """UI plugin interface."""
        plugin = MockUIPlugin()
        
        assert plugin.info.name == "Mock UI"
        assert plugin.info.plugin_type == PluginType.UI
    
    def test_service_plugin_interface(self):
        """Service plugin interface."""
        plugin = MockServicePlugin()
        
        assert plugin.get_service_name() == "mock_service"
        assert plugin.is_available() is True
        assert plugin.get_status() == "OK"
    
    def test_translation_plugin_interface(self):
        """Translation plugin interface."""
        plugin = MockTranslationPlugin()
        
        result = plugin.translate("Hello", "en", "hu")
        assert "[hu]" in result
        assert "Hello" in result
    
    def test_plugin_initialize(self):
        """Plugin inicializálás."""
        plugin = MockExportPlugin()
        assert plugin.initialize() is True
    
    def test_plugin_settings(self):
        """Plugin beállítások."""
        plugin = MockExportPlugin()
        
        # Alapértelmezett üres beállítások
        assert plugin.get_settings_widget() is None
        assert plugin.save_settings() == {}
        
        # Beállítások betöltése nem dob hibát
        plugin.load_settings({"key": "value"})


class TestPluginManager:
    """PluginManager tesztek."""
    
    @pytest.fixture
    def manager(self):
        """PluginManager fixture."""
        return PluginManager()
    
    def test_register_plugin(self, manager):
        """Plugin regisztrálása."""
        plugin = MockExportPlugin()
        
        result = manager.register(plugin, enabled=True)
        
        assert result is True
        assert manager.get_plugin("mock_export") is plugin
    
    def test_register_duplicate_plugin(self, manager):
        """Duplikált plugin regisztrálása."""
        plugin1 = MockExportPlugin()
        plugin2 = MockExportPlugin()
        
        manager.register(plugin1)
        result = manager.register(plugin2)
        
        assert result is False
    
    def test_register_multiple_plugin_types(self, manager):
        """Több típusú plugin regisztrálása."""
        export = MockExportPlugin()
        qa = MockQAPlugin()
        ui = MockUIPlugin()
        service = MockServicePlugin()
        
        manager.register(export, enabled=True)
        manager.register(qa, enabled=True)
        manager.register(ui, enabled=True)
        manager.register(service, enabled=True)
        
        assert len(manager.get_all_plugins()) == 4
        assert len(manager.get_export_plugins()) == 1
        assert len(manager.get_qa_plugins()) == 1
    
    def test_unregister_plugin(self, manager):
        """Plugin eltávolítása."""
        plugin = MockExportPlugin()
        manager.register(plugin)
        
        result = manager.unregister("mock_export")
        
        assert result is True
        assert manager.get_plugin("mock_export") is None
    
    def test_unregister_nonexistent_plugin(self, manager):
        """Nem létező plugin eltávolítása."""
        result = manager.unregister("nonexistent")
        assert result is False
    
    def test_enable_disable_plugin(self, manager):
        """Plugin engedélyezése/tiltása."""
        plugin = MockExportPlugin()
        manager.register(plugin, enabled=False)
        
        assert manager.is_enabled("mock_export") is False
        
        manager.enable_plugin("mock_export")
        assert manager.is_enabled("mock_export") is True
        
        manager.disable_plugin("mock_export")
        assert manager.is_enabled("mock_export") is False
    
    def test_get_export_plugins_enabled_only(self, manager):
        """Export pluginok lekérése csak engedélyezettek."""
        plugin1 = MockExportPlugin()
        
        # Create a second export plugin with different id
        class MockExportPlugin2(MockExportPlugin):
            @property
            def info(self):
                return PluginInfo(
                    id="mock_export_2",
                    name="Mock Export 2",
                    version="1.0.0",
                    author="Test",
                    description="Second mock export",
                    plugin_type=PluginType.EXPORT
                )
        
        plugin2 = MockExportPlugin2()
        
        manager.register(plugin1, enabled=True)
        manager.register(plugin2, enabled=False)
        
        enabled = manager.get_export_plugins(enabled_only=True)
        all_plugins = manager.get_export_plugins(enabled_only=False)
        
        assert len(enabled) == 1
        assert len(all_plugins) == 2
    
    def test_get_qa_plugins(self, manager):
        """QA pluginok lekérése."""
        qa = MockQAPlugin()
        export = MockExportPlugin()
        
        manager.register(qa, enabled=True)
        manager.register(export, enabled=True)
        
        qa_plugins = manager.get_qa_plugins()
        
        assert len(qa_plugins) == 1
        assert qa_plugins[0] is qa
    
    def test_get_enabled_plugins(self, manager):
        """Engedélyezett pluginok lekérése."""
        plugin1 = MockExportPlugin()
        plugin2 = MockQAPlugin()
        
        manager.register(plugin1, enabled=True)
        manager.register(plugin2, enabled=False)
        
        enabled = manager.get_enabled_plugins()
        
        assert "mock_export" in enabled
        assert "mock_qa" not in enabled
    
    def test_set_enabled_plugins(self, manager):
        """Engedélyezett pluginok beállítása."""
        plugin = MockExportPlugin()
        manager.register(plugin, enabled=False)
        
        manager.set_enabled_plugins({"mock_export"})
        
        assert manager.is_enabled("mock_export") is True


class TestExportPluginExecution:
    """Export plugin végrehajtás tesztek."""
    
    def test_export_creates_file(self, tmp_path):
        """Export létrehoz fájlt."""
        plugin = MockExportPlugin()
        output_file = tmp_path / "output.mock"
        
        project = Project(title="Test")
        cues = []
        
        result = plugin.export(output_file, project, cues)
        
        assert result is True
        assert output_file.exists()
        assert output_file.read_text() == "mock export content"


class TestQAPluginExecution:
    """QA plugin végrehajtás tesztek."""
    
    def test_check_finds_issues(self):
        """QA ellenőrzés talál problémákat."""
        plugin = MockQAPlugin()
        
        project = Project(title="Test")
        cues = [
            Cue(id=1, cue_index=0, source_text="Hello", translated_text=""),
            Cue(id=2, cue_index=1, source_text="World", translated_text="Világ")
        ]
        
        issues = plugin.check(project, cues)
        
        assert len(issues) == 1
        assert issues[0].cue_id == 1
        assert issues[0].severity == "warning"
    
    def test_check_no_issues(self):
        """QA ellenőrzés nem talál problémát."""
        plugin = MockQAPlugin()
        
        project = Project(title="Test")
        cues = [
            Cue(id=1, cue_index=0, source_text="Hello", translated_text="Helló"),
            Cue(id=2, cue_index=1, source_text="World", translated_text="Világ")
        ]
        
        issues = plugin.check(project, cues)
        
        assert len(issues) == 0


class TestTranslationPluginExecution:
    """Translation plugin végrehajtás tesztek."""
    
    def test_translate_text(self):
        """Szöveg fordítása."""
        plugin = MockTranslationPlugin()
        
        result = plugin.translate("Hello", "en", "hu")
        
        assert "[hu]" in result
        assert "Hello" in result
    
    def test_get_service_name(self):
        """Szolgáltatás név lekérése."""
        plugin = MockTranslationPlugin()
        
        name = plugin.get_service_name()
        
        assert "translator" in name
