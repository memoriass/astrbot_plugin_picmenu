"""
数据模型定义
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PageType(Enum):
    """页面类型"""
    MAIN = "main"
    PLUGIN_DETAIL = "plugin_detail"


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
        """获取命令数量（不包含隐藏命令）"""
        return len([cmd for cmd in self.commands if not cmd.hidden])

    def get_command_count(self, show_hidden: bool = False, is_admin: bool = False) -> int:
        """获取可见命令数量"""
        return len(self.get_visible_commands(show_hidden, is_admin))
    
    def get_visible_commands(self, show_hidden: bool = False, is_admin: bool = False) -> List[CommandInfo]:
        """获取可见的命令列表"""
        commands = self.commands if show_hidden else [cmd for cmd in self.commands if not cmd.hidden]
        # 根据管理员权限过滤
        if not is_admin:
            commands = [cmd for cmd in commands if not cmd.admin_only]
        return commands


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
    background_color: str
    text_color: str
    card_background: str
    border_color: str
    primary_color: str
    secondary_color: str

    @classmethod
    def light_theme(cls) -> 'ThemeConfig':
        """浅色主题"""
        return cls(
            background_color="#f5f5f5",
            text_color="#333333",
            card_background="#ffffff",
            border_color="#e0e0e0",
            primary_color="#007acc",
            secondary_color="#666666"
        )

    @classmethod
    def dark_theme(cls) -> 'ThemeConfig':
        """深色主题"""
        return cls(
            background_color="#2b2b2b",
            text_color="#ffffff",
            card_background="#3c3c3c",
            border_color="#555555",
            primary_color="#4a9eff",
            secondary_color="#cccccc"
        )


@dataclass
class RenderConfig:
    """渲染配置"""
    width: int = 800
    font_size: int = 16
    padding: int = 20
    card_spacing: int = 15
    border_radius: int = 8
    title_font_size: int = 24
    subtitle_font_size: int = 14
    theme: ThemeConfig = None
    max_plugins_per_page: int = 10
    col_count: int = 2
    col_width: int = 300


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
