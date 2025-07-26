"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class PageType(Enum):
    """页面类型"""
    MAIN = "main"
    PLUGIN_DETAIL = "plugin_detail"
    COMMAND_DETAIL = "command_detail"


@dataclass
class CommandInfo:
    """命令信息"""
    name: str
    description: Optional[str] = None
    usage: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    hidden: bool = False
    admin_only: bool = False
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.parameters is None:
            self.parameters = []
        if self.examples is None:
            self.examples = []


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    commands: List[CommandInfo] = field(default_factory=list)
    hidden: bool = False
    plugin_type: str = "application"
    homepage: Optional[str] = None
    usage: Optional[str] = None
    
    def __post_init__(self):
        if self.commands is None:
            self.commands = []
    
    @property
    def subtitle(self) -> str:
        """获取插件副标题"""
        parts = []
        if self.author:
            parts.append(f"By {self.author}")
        if self.version:
            parts.append(f"v{self.version}")
        return " | ".join(parts)
    
    @property
    def command_count(self) -> int:
        """获取命令数量"""
        return len([cmd for cmd in self.commands if not cmd.hidden])
    
    def get_visible_commands(self, show_hidden: bool = False) -> List[CommandInfo]:
        """获取可见的命令列表"""
        if show_hidden:
            return self.commands
        return [cmd for cmd in self.commands if not cmd.hidden]


@dataclass
class HelpPage:
    """帮助页面"""
    title: str
    plugins: List[PluginInfo]
    show_hidden: bool = False
    page_type: str = "main"
    current_page: int = 1
    total_pages: int = 1
    theme: str = "light"
    
    @property
    def visible_plugins(self) -> List[PluginInfo]:
        """获取可见的插件列表"""
        if self.show_hidden:
            return self.plugins
        return [plugin for plugin in self.plugins if not plugin.hidden]
    
    @property
    def plugin_count(self) -> int:
        """获取插件数量"""
        return len(self.visible_plugins)


@dataclass
class ThemeConfig:
    """主题配置"""
    name: str
    background_color: str
    text_color: str
    primary_color: str
    secondary_color: str
    border_color: str
    card_background: str
    header_background: str
    
    @classmethod
    def light_theme(cls) -> 'ThemeConfig':
        """浅色主题"""
        return cls(
            name="light",
            background_color="#FFFFFF",
            text_color="#333333",
            primary_color="#007ACC",
            secondary_color="#666666",
            border_color="#E0E0E0",
            card_background="#F8F9FA",
            header_background="#F0F0F0"
        )
    
    @classmethod
    def dark_theme(cls) -> 'ThemeConfig':
        """深色主题"""
        return cls(
            name="dark",
            background_color="#1E1E1E",
            text_color="#FFFFFF",
            primary_color="#4FC3F7",
            secondary_color="#CCCCCC",
            border_color="#404040",
            card_background="#2D2D2D",
            header_background="#252525"
        )


@dataclass
class RenderConfig:
    """渲染配置"""
    width: int = 800
    font_size: int = 16
    padding: int = 20
    card_spacing: int = 15
    border_radius: int = 8
    max_plugins_per_page: int = 12
    
    # 字体配置
    title_font_size: int = 24
    subtitle_font_size: int = 14
    command_font_size: int = 14
    
    # 颜色配置
    theme: ThemeConfig = field(default_factory=ThemeConfig.light_theme)
    
    def __post_init__(self):
        # 根据基础字体大小调整其他字体大小
        self.title_font_size = int(self.font_size * 1.5)
        self.subtitle_font_size = int(self.font_size * 0.875)
        self.command_font_size = int(self.font_size * 0.875)


@dataclass
class SearchResult:
    """搜索结果"""
    item: Any  # PluginInfo 或 CommandInfo
    score: int
    match_type: str  # "name", "description", "pinyin"
    
    def __lt__(self, other):
        return self.score < other.score


@dataclass
class CacheInfo:
    """缓存信息"""
    key: str
    data: bytes
    timestamp: float
    size: int
    
    @property
    def age_seconds(self) -> float:
        """获取缓存年龄（秒）"""
        import time
        return time.time() - self.timestamp
    
    @property
    def size_mb(self) -> float:
        """获取缓存大小（MB）"""
        return self.size / (1024 * 1024)
