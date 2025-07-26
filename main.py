import asyncio
import hashlib
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from fuzzywuzzy import fuzz, process
from pypinyin import Style, lazy_pinyin

from .collector import PluginInfoCollector
from .models import CommandInfo, HelpPage, PluginInfo
from .renderer import HelpImageRenderer


@register(
    "picmenu",
    "Assistant",
    "新一代的图片帮助插件",
    "1.0.0",
    "https://github.com/example/astrbot_plugin_picmenu",
)
class PicMenuPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 初始化组件
        self.collector = PluginInfoCollector(context)
        self.renderer = HelpImageRenderer(config)

        # 缓存系统
        self.cache: Dict[str, Tuple[bytes, float]] = {}
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_expire = config.get("cache_expire_minutes", 30) * 60

        # 管理员列表
        self.admin_users = self._parse_admin_users()

        # 搜索配置
        self.fuzzy_threshold = config.get("fuzzy_search_threshold", 60)
        self.enable_pinyin = config.get("enable_pinyin_search", True)

        logger.info("PicMenu 插件已加载")

    def _parse_admin_users(self) -> List[str]:
        """解析管理员用户列表"""
        admin_str = self.config.get("admin_users", "")
        if not admin_str:
            return []
        return [user.strip() for user in admin_str.split(",") if user.strip()]

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否为管理员"""
        return user_id in self.admin_users

    def can_see_hidden(self, user_id: str) -> bool:
        """检查用户是否可以查看隐藏内容"""
        if not self.config.get("admin_only_hidden", True):
            return True
        return self.is_admin(user_id)

    def get_cache_key(self, *args) -> str:
        """生成缓存键"""
        content = "|".join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached_image(self, cache_key: str) -> Optional[bytes]:
        """获取缓存的图片"""
        if not self.cache_enabled or cache_key not in self.cache:
            return None

        image_data, timestamp = self.cache[cache_key]
        if time.time() - timestamp > self.cache_expire:
            del self.cache[cache_key]
            return None

        return image_data

    def cache_image(self, cache_key: str, image_data: bytes):
        """缓存图片"""
        if self.cache_enabled:
            self.cache[cache_key] = (image_data, time.time())

    def clean_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.cache_expire
        ]
        for key in expired_keys:
            del self.cache[key]

    def get_pinyin_string(self, text: str) -> str:
        """获取文本的拼音字符串"""
        if not self.enable_pinyin:
            return ""
        return "".join(lazy_pinyin(text, style=Style.NORMAL))

    def fuzzy_search_plugins(
        self, query: str, plugins: List[PluginInfo]
    ) -> List[Tuple[PluginInfo, int]]:
        """模糊搜索插件"""
        if not query or not plugins:
            return []

        results = []
        query_lower = query.lower()
        query_pinyin = self.get_pinyin_string(query_lower)

        for plugin in plugins:
            # 计算名称匹配度
            name_score = fuzz.partial_ratio(query_lower, plugin.name.lower())

            # 计算拼音匹配度
            pinyin_score = 0
            if self.enable_pinyin and query_pinyin:
                plugin_pinyin = self.get_pinyin_string(plugin.name.lower())
                pinyin_score = fuzz.partial_ratio(query_pinyin, plugin_pinyin)

            # 计算描述匹配度
            desc_score = 0
            if plugin.description:
                desc_score = fuzz.partial_ratio(query_lower, plugin.description.lower())

            # 综合评分
            final_score = max(name_score, pinyin_score, desc_score * 0.7)

            if final_score >= self.fuzzy_threshold:
                results.append((plugin, int(final_score)))

        # 按评分排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def fuzzy_search_commands(
        self, query: str, commands: List[CommandInfo]
    ) -> List[Tuple[CommandInfo, int]]:
        """模糊搜索命令"""
        if not query or not commands:
            return []

        results = []
        query_lower = query.lower()

        for command in commands:
            # 计算命令名匹配度
            name_score = fuzz.partial_ratio(query_lower, command.name.lower())

            # 计算描述匹配度
            desc_score = 0
            if command.description:
                desc_score = fuzz.partial_ratio(
                    query_lower, command.description.lower()
                )

            # 综合评分
            final_score = max(name_score, desc_score * 0.8)

            if final_score >= self.fuzzy_threshold:
                results.append((command, int(final_score)))

        # 按评分排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def parse_help_query(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """解析帮助查询参数"""
        if not query:
            return None, None

        parts = query.strip().split(None, 1)
        plugin_query = parts[0] if parts else None
        command_query = parts[1] if len(parts) > 1 else None

        return plugin_query, command_query

    async def get_plugin_by_query(
        self, query: str, plugins: List[PluginInfo]
    ) -> Optional[PluginInfo]:
        """根据查询获取插件"""
        # 尝试数字索引
        if query.isdigit():
            index = int(query) - 1
            if 0 <= index < len(plugins):
                return plugins[index]

        # 尝试精确匹配
        for plugin in plugins:
            if plugin.name.lower() == query.lower():
                return plugin

        # 模糊搜索
        results = self.fuzzy_search_plugins(query, plugins)
        if results:
            return results[0][0]

        return None

    async def get_command_by_query(
        self, query: str, commands: List[CommandInfo]
    ) -> Optional[CommandInfo]:
        """根据查询获取命令"""
        # 尝试数字索引
        if query.isdigit():
            index = int(query) - 1
            if 0 <= index < len(commands):
                return commands[index]

        # 尝试精确匹配
        for command in commands:
            if command.name.lower() == query.lower():
                return command

        # 模糊搜索
        results = self.fuzzy_search_commands(query, commands)
        if results:
            return results[0][0]

        return None

    @filter.command("help")
    async def help_command(self, event: AstrMessageEvent, query: str = ""):
        """显示帮助信息"""
        try:
            user_id = event.get_sender_id()
            show_hidden = self.can_see_hidden(user_id)

            # 收集插件信息
            plugins = await self.collector.collect_plugins(show_hidden)

            # 解析查询参数
            plugin_query, command_query = self.parse_help_query(query)

            if not plugin_query:
                # 显示主页
                await self.show_main_page(event, plugins, show_hidden)
            elif not command_query:
                # 显示插件详情
                await self.show_plugin_detail(event, plugin_query, plugins, show_hidden)
            else:
                # 显示命令详情
                await self.show_command_detail(
                    event, plugin_query, command_query, plugins, show_hidden
                )

        except Exception as e:
            logger.error(f"处理帮助命令失败: {e}")
            yield event.plain_result("❌ 生成帮助信息时出现错误")

    async def show_main_page(
        self, event: AstrMessageEvent, plugins: List[PluginInfo], show_hidden: bool
    ):
        """显示主页"""
        try:
            # 生成缓存键
            cache_key = self.get_cache_key(
                "main", len(plugins), show_hidden, self.config.get("theme", "light")
            )

            # 尝试获取缓存
            cached_image = self.get_cached_image(cache_key)
            if cached_image:
                yield event.chain_result([Comp.Image.fromBytes(cached_image)])
                return

            # 生成帮助页面
            help_page = HelpPage(
                title="📚 插件帮助菜单",
                plugins=plugins,
                show_hidden=show_hidden,
                page_type="main",
            )

            # 渲染图片
            image_data = await self.renderer.render_main_page(help_page)

            # 缓存图片
            self.cache_image(cache_key, image_data)

            # 发送图片
            yield event.chain_result([Comp.Image.fromBytes(image_data)])

        except Exception as e:
            logger.error(f"显示主页失败: {e}")
            yield event.plain_result("❌ 生成主页时出现错误")

    async def show_plugin_detail(
        self,
        event: AstrMessageEvent,
        plugin_query: str,
        plugins: List[PluginInfo],
        show_hidden: bool,
    ):
        """显示插件详情"""
        try:
            plugin = await self.get_plugin_by_query(plugin_query, plugins)
            if not plugin:
                yield event.plain_result(f"❌ 未找到插件: {plugin_query}")
                return

            # 生成缓存键
            cache_key = self.get_cache_key(
                "plugin", plugin.name, show_hidden, self.config.get("theme", "light")
            )

            # 尝试获取缓存
            cached_image = self.get_cached_image(cache_key)
            if cached_image:
                yield event.chain_result([Comp.Image.fromBytes(cached_image)])
                return

            # 生成帮助页面
            help_page = HelpPage(
                title=f"🔧 {plugin.name}",
                plugins=[plugin],
                show_hidden=show_hidden,
                page_type="plugin_detail",
            )

            # 渲染图片
            image_data = await self.renderer.render_plugin_detail(help_page, plugin)

            # 缓存图片
            self.cache_image(cache_key, image_data)

            # 发送图片
            yield event.chain_result([Comp.Image.fromBytes(image_data)])

        except Exception as e:
            logger.error(f"显示插件详情失败: {e}")
            yield event.plain_result("❌ 生成插件详情时出现错误")

    async def show_command_detail(
        self,
        event: AstrMessageEvent,
        plugin_query: str,
        command_query: str,
        plugins: List[PluginInfo],
        show_hidden: bool,
    ):
        """显示命令详情"""
        try:
            plugin = await self.get_plugin_by_query(plugin_query, plugins)
            if not plugin:
                yield event.plain_result(f"❌ 未找到插件: {plugin_query}")
                return

            command = await self.get_command_by_query(command_query, plugin.commands)
            if not command:
                yield event.plain_result(
                    f"❌ 在插件 {plugin.name} 中未找到命令: {command_query}"
                )
                return

            # 生成缓存键
            cache_key = self.get_cache_key(
                "command",
                plugin.name,
                command.name,
                show_hidden,
                self.config.get("theme", "light"),
            )

            # 尝试获取缓存
            cached_image = self.get_cached_image(cache_key)
            if cached_image:
                yield event.chain_result([Comp.Image.fromBytes(cached_image)])
                return

            # 生成帮助页面
            help_page = HelpPage(
                title=f"⚡ {command.name}",
                plugins=[plugin],
                show_hidden=show_hidden,
                page_type="command_detail",
            )

            # 渲染图片
            image_data = await self.renderer.render_command_detail(
                help_page, plugin, command
            )

            # 缓存图片
            self.cache_image(cache_key, image_data)

            # 发送图片
            yield event.chain_result([Comp.Image.fromBytes(image_data)])

        except Exception as e:
            logger.error(f"显示命令详情失败: {e}")
            yield event.plain_result("❌ 生成命令详情时出现错误")

    @filter.command("帮助")
    async def help_alias(self, event: AstrMessageEvent, query: str = ""):
        """帮助命令的中文别名"""
        await self.help_command(event, query)

    @filter.command("菜单")
    async def menu_alias(self, event: AstrMessageEvent, query: str = ""):
        """菜单命令别名"""
        await self.help_command(event, query)

    @filter.command("picmenu_status")
    async def status_command(self, event: AstrMessageEvent):
        """查看插件状态"""
        try:
            plugins = await self.collector.collect_plugins(True)
            cache_count = len(self.cache)

            status_text = f"""📊 PicMenu 状态
🔌 已加载插件: {len(plugins)}
🎨 当前主题: {self.config.get('theme', 'light')}
💾 缓存图片数: {cache_count}
🔍 模糊搜索阈值: {self.fuzzy_threshold}
👥 管理员数量: {len(self.admin_users)}
🈯 拼音搜索: {'✅ 启用' if self.enable_pinyin else '❌ 禁用'}
⏰ 缓存过期时间: {self.cache_expire // 60}分钟"""

            yield event.plain_result(status_text)

        except Exception as e:
            logger.error(f"查询状态失败: {e}")
            yield event.plain_result("❌ 查询状态失败")

    @filter.command("picmenu_clear_cache")
    async def clear_cache_command(self, event: AstrMessageEvent):
        """清理缓存"""
        user_id = event.get_sender_id()
        if not self.is_admin(user_id):
            yield event.plain_result("❌ 权限不足，仅管理员可执行此操作")
            return

        cache_count = len(self.cache)
        self.cache.clear()
        yield event.plain_result(f"✅ 已清理 {cache_count} 个缓存图片")

    async def terminate(self):
        """插件卸载时的清理工作"""
        self.cache.clear()
        logger.info("PicMenu 插件已卸载")
