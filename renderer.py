"""
帮助图片渲染器
"""
import io
import math
from typing import List, Optional, Tuple, Union

from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont

from .models import CommandInfo, HelpPage, PluginInfo, RenderConfig, ThemeConfig


class HelpImageRenderer:
    """帮助图片渲染器"""

    def __init__(self, config):
        self.config = config
        self.render_config = self._create_render_config()
        self._font_cache = {}  # 字体缓存
        self._available_font_path = None  # 可用字体路径缓存
        
    def _create_render_config(self) -> RenderConfig:
        """创建渲染配置"""
        theme_name = self.config.get("theme", "light")
        theme = ThemeConfig.dark_theme() if theme_name == "dark" else ThemeConfig.light_theme()

        return RenderConfig(
            width=self.config.get("image_width", 800),
            font_size=self.config.get("font_size", 16),
            theme=theme,
            max_plugins_per_page=self.config.get("max_plugins_per_page", 10),
            col_count=self.config.get("col_count", 2),
            col_width=self.config.get("col_width", 300)
        )
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """获取字体"""
        import os
        import platform

        # 检查缓存
        cache_key = f"{size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # 如果已经找到可用字体路径，直接使用
        if self._available_font_path:
            try:
                font = ImageFont.truetype(self._available_font_path, size)
                self._font_cache[cache_key] = font
                return font
            except Exception as e:
                logger.warning(f"使用缓存字体路径失败: {e}")
                self._available_font_path = None

        system = platform.system()

        # 定义字体路径列表，按优先级排序
        font_paths = []

        if system == "Windows":
            # Windows 系统字体路径
            windows_fonts = [
                "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                "C:/Windows/Fonts/simhei.ttf",    # 黑体
                "C:/Windows/Fonts/simsun.ttc",    # 宋体
                "C:/Windows/Fonts/arial.ttf",     # Arial
                "C:/Windows/Fonts/calibri.ttf",   # Calibri
            ]
            font_paths.extend(windows_fonts)
        elif system == "Darwin":  # macOS
            # macOS 系统字体路径
            macos_fonts = [
                "/System/Library/Fonts/PingFang.ttc",           # 苹方
                "/System/Library/Fonts/Helvetica.ttc",          # Helvetica
                "/System/Library/Fonts/Arial.ttf",              # Arial
                "/Library/Fonts/Arial Unicode MS.ttf",          # Arial Unicode MS
            ]
            font_paths.extend(macos_fonts)
        else:  # Linux
            # Linux 系统字体路径
            linux_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/arphic/uming.ttc",
            ]
            font_paths.extend(linux_fonts)

        # 尝试加载字体
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    logger.info(f"尝试加载字体: {font_path}")
                    font = ImageFont.truetype(font_path, size)
                    # 缓存成功的字体路径和字体对象
                    self._available_font_path = font_path
                    self._font_cache[cache_key] = font
                    logger.info(f"成功加载字体: {font_path}")
                    return font
            except Exception as e:
                logger.debug(f"加载字体失败 {font_path}: {e}")
                continue

        # 如果所有字体都加载失败，使用默认字体
        logger.warning("所有字体加载失败，使用默认字体")
        try:
            font = ImageFont.load_default()
            self._font_cache[cache_key] = font
            return font
        except Exception as e:
            logger.error(f"加载默认字体也失败: {e}")
            # 创建一个最基本的字体对象
            font = ImageFont.load_default()
            self._font_cache[cache_key] = font
            return font
    
    def _calculate_text_size(self, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        """计算文本尺寸"""
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            # 兼容旧版本 PIL
            return font.getsize(text)
    
    def _draw_rectangle(self, draw, bbox, fill, outline=None):
        """绘制简单矩形"""
        draw.rectangle(bbox, fill=fill, outline=outline)
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """文本换行 - 改进版，支持中文"""
        if not text:
            return []

        lines = []

        # 对于中文文本，需要按字符而不是按单词换行
        if self._contains_chinese(text):
            current_line = ""
            for char in text:
                test_line = current_line + char
                text_width, _ = self._calculate_text_size(test_line, font)

                if text_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char

            if current_line:
                lines.append(current_line)
        else:
            # 英文文本按单词换行
            words = text.split()
            current_line = ""

            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                text_width, _ = self._calculate_text_size(test_line, font)

                if text_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

        return lines

    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    async def render_main_page(self, help_page: HelpPage) -> bytes:
        """渲染主页"""
        try:
            plugins = help_page.visible_plugins
            config = self.render_config
            theme = config.theme or ThemeConfig.light_theme()  # 确保theme不为None
            
            # 计算布局
            cols = 2
            rows = math.ceil(len(plugins) / cols)
            card_width = (config.width - config.padding * 2 - config.card_spacing * (cols - 1)) // cols
            card_height = 120
            
            # 计算图片高度
            header_height = 80
            content_height = rows * card_height + (rows - 1) * config.card_spacing
            total_height = header_height + content_height + config.padding * 2
            
            # 创建图片
            img = Image.new('RGB', (config.width, total_height), theme.background_color)
            draw = ImageDraw.Draw(img)
            
            # 绘制标题
            title_font = self._get_font(config.title_font_size)
            title_text = help_page.title
            title_width, title_height = self._calculate_text_size(title_text, title_font)
            title_x = (config.width - title_width) // 2
            title_y = config.padding
            
            draw.text((title_x, title_y), title_text, fill=theme.text_color, font=title_font)
            
            # 绘制副标题
            subtitle_font = self._get_font(config.subtitle_font_size)
            subtitle_text = f"共 {len(plugins)} 个插件"
            subtitle_width, subtitle_height = self._calculate_text_size(subtitle_text, subtitle_font)
            subtitle_x = (config.width - subtitle_width) // 2
            subtitle_y = title_y + title_height + 10
            
            draw.text((subtitle_x, subtitle_y), subtitle_text, fill=theme.secondary_color, font=subtitle_font)
            
            # 绘制插件卡片
            y_offset = header_height + config.padding
            
            for i, plugin in enumerate(plugins):
                row = i // cols
                col = i % cols
                
                x = config.padding + col * (card_width + config.card_spacing)
                y = y_offset + row * (card_height + config.card_spacing)
                
                await self._draw_plugin_card(draw, plugin, x, y, card_width, card_height, i + 1)
            
            # 保存为字节流
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"渲染主页失败: {e}")
            raise
    
    async def _draw_plugin_card(self, draw: ImageDraw.ImageDraw, plugin: PluginInfo, 
                               x: int, y: int, width: int, height: int, index: int):
        """绘制插件卡片"""
        config = self.render_config
        theme = config.theme or ThemeConfig.light_theme()  # 确保theme不为None
        
        # 绘制卡片背景
        self._draw_rectangle(draw, (x, y, x + width, y + height), theme.card_background, theme.border_color)
        
        # 绘制序号
        index_font = self._get_font(config.subtitle_font_size)
        index_text = str(index)
        draw.text((x + 10, y + 10), index_text, fill=theme.primary_color, font=index_font)
        
        # 绘制插件名称
        name_font = self._get_font(config.font_size)
        name_text = plugin.name
        name_lines = self._wrap_text(name_text, name_font, width - 60)
        
        name_y = y + 10
        for line in name_lines[:2]:  # 最多显示2行
            draw.text((x + 40, name_y), line, fill=theme.text_color, font=name_font)
            name_y += config.font_size + 2
        
        # 绘制描述
        if plugin.description:
            desc_font = self._get_font(config.subtitle_font_size)
            desc_text = plugin.description
            desc_lines = self._wrap_text(desc_text, desc_font, width - 20)
            
            desc_y = y + 50
            for line in desc_lines[:2]:  # 最多显示2行
                if desc_y + config.subtitle_font_size > y + height - 20:
                    break
                draw.text((x + 10, desc_y), line, fill=theme.secondary_color, font=desc_font)
                desc_y += config.subtitle_font_size + 2
        
        # 绘制命令数量
        cmd_count = plugin.command_count
        if cmd_count > 0:
            cmd_font = self._get_font(config.subtitle_font_size)
            cmd_text = f"{cmd_count} 个命令"
            cmd_width, cmd_height = self._calculate_text_size(cmd_text, cmd_font)
            draw.text((x + width - cmd_width - 10, y + height - cmd_height - 10), 
                     cmd_text, fill=theme.primary_color, font=cmd_font)
    
    async def render_plugin_detail(self, help_page: HelpPage, plugin: PluginInfo, is_admin: bool = False) -> bytes:
        """渲染插件详情"""
        try:
            config = self.render_config
            theme = config.theme or ThemeConfig.light_theme()  # 确保theme不为None

            # 根据管理员权限过滤命令
            commands = plugin.get_visible_commands(help_page.show_hidden, is_admin)

            # 计算双排布局
            cols = 2
            rows = math.ceil(len(commands) / cols) if commands else 0
            card_width = (config.width - config.padding * 2 - config.card_spacing * (cols - 1)) // cols
            card_height = 80  # 命令卡片高度

            # 计算总高度
            header_height = 120
            content_height = rows * card_height + (rows - 1) * config.card_spacing if rows > 0 else 50
            total_height = header_height + content_height + config.padding * 2
            
            # 创建图片
            img = Image.new('RGB', (config.width, total_height), theme.background_color)
            draw = ImageDraw.Draw(img)
            
            # 绘制标题
            title_font = self._get_font(config.title_font_size)
            title_text = f"🔧 {plugin.name}"
            title_width, title_height = self._calculate_text_size(title_text, title_font)
            title_x = (config.width - title_width) // 2
            title_y = config.padding
            
            draw.text((title_x, title_y), title_text, fill=theme.text_color, font=title_font)
            
            # 绘制插件信息
            info_y = title_y + title_height + 10
            info_font = self._get_font(config.subtitle_font_size)
            
            if plugin.subtitle:
                subtitle_width, subtitle_height = self._calculate_text_size(plugin.subtitle, info_font)
                subtitle_x = (config.width - subtitle_width) // 2
                draw.text((subtitle_x, info_y), plugin.subtitle, fill=theme.secondary_color, font=info_font)
                info_y += subtitle_height + 5
            
            if plugin.description:
                desc_lines = self._wrap_text(plugin.description, info_font, config.width - config.padding * 2)
                for line in desc_lines:
                    line_width, line_height = self._calculate_text_size(line, info_font)
                    line_x = (config.width - line_width) // 2
                    draw.text((line_x, info_y), line, fill=theme.secondary_color, font=info_font)
                    info_y += line_height + 2
            
            # 绘制命令列表（双排布局）
            cmd_y = header_height + config.padding

            if not commands:
                no_cmd_text = "该插件暂无可用命令"
                no_cmd_font = self._get_font(config.font_size)
                no_cmd_width, _ = self._calculate_text_size(no_cmd_text, no_cmd_font)
                no_cmd_x = (config.width - no_cmd_width) // 2
                draw.text((no_cmd_x, cmd_y), no_cmd_text, fill=theme.secondary_color, font=no_cmd_font)
            else:
                for i, command in enumerate(commands):
                    row = i // cols
                    col = i % cols

                    x = config.padding + col * (card_width + config.card_spacing)
                    y = cmd_y + row * (card_height + config.card_spacing)

                    await self._draw_command_card(draw, command, x, y, card_width, card_height, i + 1)
            
            # 保存为字节流
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"渲染插件详情失败: {e}")
            raise
    
    async def _draw_command_item(self, draw: ImageDraw.ImageDraw, command: CommandInfo,
                                x: int, y: int, width: int, height: int, index: int):
        """绘制命令项"""
        config = self.render_config
        theme = config.theme or ThemeConfig.light_theme()  # 确保theme不为None
        
        # 绘制背景
        self._draw_rectangle(draw, (x, y, x + width, y + height), theme.card_background, theme.border_color)
        
        # 绘制序号
        index_font = self._get_font(config.subtitle_font_size)
        index_text = str(index)
        draw.text((x + 10, y + 10), index_text, fill=theme.primary_color, font=index_font)
        
        # 绘制命令名
        name_font = self._get_font(config.font_size)
        name_text = f"/{command.name}"
        draw.text((x + 40, y + 10), name_text, fill=theme.text_color, font=name_font)
        
        # 绘制描述
        if command.description:
            desc_font = self._get_font(config.subtitle_font_size)
            desc_text = command.description
            desc_lines = self._wrap_text(desc_text, desc_font, width - 50)
            
            desc_y = y + 35
            for line in desc_lines[:1]:  # 只显示1行
                draw.text((x + 40, desc_y), line, fill=theme.secondary_color, font=desc_font)
                break
        
        # 绘制标签
        tag_x = x + width - 10
        tag_y = y + 10
        tag_font = self._get_font(config.subtitle_font_size - 2)
        
        if command.admin_only:
            admin_text = "管理员"
            admin_width, admin_height = self._calculate_text_size(admin_text, tag_font)
            tag_x -= admin_width
            
            # 绘制标签背景
            self._draw_rectangle(draw, (tag_x - 5, tag_y - 2, tag_x + admin_width + 5, tag_y + admin_height + 2), theme.primary_color)
            
            draw.text((tag_x, tag_y), admin_text, fill=theme.background_color, font=tag_font)

    async def _draw_command_card(self, draw, command: CommandInfo,
                                x: int, y: int, width: int, height: int, index: int):
        """绘制命令卡片（双排布局样式）"""
        config = self.render_config
        theme = config.theme or ThemeConfig.light_theme()

        # 绘制卡片背景
        self._draw_rectangle(draw, (x, y, x + width, y + height), theme.card_background, theme.border_color)

        # 绘制序号
        index_font = self._get_font(config.subtitle_font_size)
        index_text = str(index)
        draw.text((x + 10, y + 10), index_text, fill=theme.primary_color, font=index_font)

        # 绘制命令名
        name_font = self._get_font(config.font_size)
        name_text = f"/{command.name}"
        draw.text((x + 40, y + 10), name_text, fill=theme.text_color, font=name_font)

        # 绘制描述
        if command.description:
            desc_font = self._get_font(config.subtitle_font_size)
            desc_text = command.description
            desc_lines = self._wrap_text(desc_text, desc_font, width - 20)

            desc_y = y + 40
            for line in desc_lines[:2]:  # 最多显示2行
                if desc_y + config.subtitle_font_size > y + height - 20:
                    break
                draw.text((x + 10, desc_y), line, fill=theme.secondary_color, font=desc_font)
                desc_y += config.subtitle_font_size + 2

        # 绘制管理员标签
        if command.admin_only:
            tag_font = self._get_font(config.subtitle_font_size - 2)
            admin_text = "管理员"
            admin_width, admin_height = self._calculate_text_size(admin_text, tag_font)
            tag_x = x + width - admin_width - 10
            tag_y = y + height - admin_height - 10

            # 绘制标签背景
            self._draw_rectangle(draw, (tag_x - 3, tag_y - 2, tag_x + admin_width + 3, tag_y + admin_height + 2), theme.primary_color)
            draw.text((tag_x, tag_y), admin_text, fill=theme.background_color, font=tag_font)







