"""
DubSync Icon Manager

SVG icon loading and management for the application.
"""

from pathlib import Path
from typing import Optional, Dict
from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

from dubsync.services.logger import get_logger

logger = get_logger(__name__)

# Icon directory path
ICONS_DIR = Path(__file__).parent / "icons"


class IconManager:
    """
    Manages SVG icon loading with theme color support.
    
    Icons are loaded from the resources/icons directory and can be
    colorized to match the current theme.
    """
    
    _instance: Optional['IconManager'] = None
    _cache: Dict[str, QIcon] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._icon_color: QColor = QColor("#ffffff")
        self._icon_size: QSize = QSize(24, 24)
        logger.debug(f"IconManager initialized, icons dir: {ICONS_DIR}")
    
    def set_icon_color(self, color: QColor):
        """
        Set the default icon color for theming.
        
        Args:
            color: QColor to use for icons
        """
        self._icon_color = color
        # Clear cache when color changes
        self._cache.clear()
        logger.debug(f"Icon color set to {color.name()}")
    
    def set_default_size(self, size: QSize):
        """
        Set the default icon size.
        
        Args:
            size: QSize for icons
        """
        self._icon_size = size
    
    def get_icon(
        self, 
        name: str, 
        color: Optional[QColor] = None,
        size: Optional[QSize] = None
    ) -> QIcon:
        """
        Get an icon by name.
        
        Args:
            name: Icon name (without .svg extension)
            color: Optional color override
            size: Optional size override
            
        Returns:
            QIcon instance (empty if icon not found)
        """
        # Build cache key
        actual_color = color or self._icon_color
        actual_size = size or self._icon_size
        cache_key = f"{name}_{actual_color.name()}_{actual_size.width()}x{actual_size.height()}"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Load icon
        icon = self._load_icon(name, actual_color, actual_size)
        self._cache[cache_key] = icon
        return icon
    
    def _load_icon(
        self, 
        name: str, 
        color: QColor, 
        size: QSize
    ) -> QIcon:
        """
        Load and colorize an SVG icon.
        
        Args:
            name: Icon name (without .svg extension)
            color: Color to apply
            size: Size for the icon
            
        Returns:
            QIcon instance
        """
        icon_path = ICONS_DIR / f"{name}.svg"
        
        if not icon_path.exists():
            logger.warning(f"Icon not found: {icon_path}")
            return QIcon()
        
        try:
            # Read SVG content
            svg_content = icon_path.read_text(encoding="utf-8")
            
            # Replace currentColor with actual color
            svg_content = svg_content.replace("currentColor", color.name())
            
            # Also handle common color patterns
            svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color.name()}"')
            svg_content = svg_content.replace('stroke="#000"', f'stroke="{color.name()}"')
            svg_content = svg_content.replace('fill="#000000"', f'fill="{color.name()}"')
            svg_content = svg_content.replace('fill="#000"', f'fill="{color.name()}"')
            
            # Add fill color to path elements that don't have fill specified
            # This handles FontAwesome icons which don't have fill attributes
            import re
            # Add fill to <path without fill attribute
            svg_content = re.sub(
                r'<path(?![^>]*fill=)',
                f'<path fill="{color.name()}"',
                svg_content
            )
            # Also handle <circle, <rect, etc without fill
            svg_content = re.sub(
                r'<(circle|rect|polygon|ellipse)(?![^>]*fill=)',
                f'<\\1 fill="{color.name()}"',
                svg_content
            )
            
            # Render SVG to pixmap
            renderer = QSvgRenderer(svg_content.encode("utf-8"))
            
            if not renderer.isValid():
                logger.error(f"Invalid SVG: {icon_path}")
                return QIcon()
            
            # Create pixmap
            pixmap = QPixmap(size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            logger.error(f"Error loading icon {name}: {e}")
            return QIcon()
    
    def get_pixmap(
        self, 
        name: str, 
        color: Optional[QColor] = None,
        size: Optional[QSize] = None
    ) -> QPixmap:
        """
        Get a pixmap by icon name.
        
        Args:
            name: Icon name (without .svg extension)
            color: Optional color override
            size: Optional size override
            
        Returns:
            QPixmap instance (null if icon not found)
        """
        actual_size = size or self._icon_size
        icon = self.get_icon(name, color, actual_size)
        return icon.pixmap(actual_size)
    
    def clear_cache(self):
        """Clear the icon cache."""
        self._cache.clear()
        logger.debug("Icon cache cleared")
    
    def has_icon(self, name: str) -> bool:
        """
        Check if an icon exists.
        
        Args:
            name: Icon name (without .svg extension)
            
        Returns:
            True if icon file exists
        """
        return (ICONS_DIR / f"{name}.svg").exists()
    
    def list_available_icons(self) -> list[str]:
        """
        List all available icon names.
        
        Returns:
            List of icon names (without .svg extension)
        """
        if not ICONS_DIR.exists():
            return []
        return [p.stem for p in ICONS_DIR.glob("*.svg")]


# Global instance
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """Get the global IconManager instance."""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager


def get_icon(
    name: str, 
    color: Optional[QColor] = None,
    size: Optional[QSize] = None
) -> QIcon:
    """
    Convenience function to get an icon.
    
    Args:
        name: Icon name (without .svg extension)
        color: Optional color override
        size: Optional size override
        
    Returns:
        QIcon instance
    """
    return get_icon_manager().get_icon(name, color, size)


def get_pixmap(
    name: str, 
    color: Optional[QColor] = None,
    size: Optional[QSize] = None
) -> QPixmap:
    """
    Convenience function to get a pixmap.
    
    Args:
        name: Icon name (without .svg extension)
        color: Optional color override
        size: Optional size override
        
    Returns:
        QPixmap instance
    """
    return get_icon_manager().get_pixmap(name, color, size)
