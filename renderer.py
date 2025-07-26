"""
帮助图片渲染器
"""
import io
import math
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from astrbot.api import logger

from .models import PluginInfo, CommandInfo, HelpPage, ThemeConfig, RenderConfig


class HelpImageRenderer:
    """帮助图片渲染器"""
    
    def __init__(self, config):
        self.config = config
        self.render_config = self._create_render_config()
        
    def _create_render_config(self) -> RenderConfig:
        """创建渲染配置"""
        theme_name = self.config.get("theme", "light")
        theme = ThemeConfig.light_theme() if theme_name == "light" else ThemeConfig.dark_theme()
        
        return RenderConfig(
            width=self.config.get("image_width", 800),
            font_size=self.config.get("font_size", 16),
            theme=theme,
            max_plugins_per_page=self.config.get("max_plugins_per_page", 12)
        )
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """获取字体"""
        try:
            # 尝试加载系统字体
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            try:
                # Windows 中文字体
                return ImageFont.truetype("msyh.ttc", size)
            except OSError:
                try:
                    # Linux 中文字体
                    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
                except OSError:
                    # 使用默认字体
                    return ImageFont.load_default()
    
    def _calculate_text_size(self, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        """计算文本尺寸"""
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            # 兼容旧版本 PIL
            return font.getsize(text)
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], 
                               radius: int, fill: str, outline: str = None):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = bbox
        
        # 绘制主体矩形
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline)
        
        # 绘制四个角的圆形
        draw.pieslice([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=fill, outline=outline)
        draw.pieslice([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=fill, outline=outline)
        draw.pieslice([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=fill, outline=outline)
        draw.pieslice([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=fill, outline=outline)
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """文本换行"""
        if not text:
            return []
        
        words = text.split()
        lines = []
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
    
    async def render_main_page(self, help_page: HelpPage) -> bytes:
        """渲染主页"""
        try:
            plugins = help_page.visible_plugins
            config = self.render_config
            theme = config.theme
            
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
        theme = config.theme
        
        # 绘制卡片背景
        self._draw_rounded_rectangle(
            draw, (x, y, x + width, y + height),
            config.border_radius, theme.card_background, theme.border_color
        )
        
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
    
    async def render_plugin_detail(self, help_page: HelpPage, plugin: PluginInfo) -> bytes:
        """渲染插件详情"""
        try:
            config = self.render_config
            theme = config.theme
            
            # 计算内容高度
            header_height = 120
            command_height = 60
            commands = plugin.get_visible_commands(help_page.show_hidden)
            content_height = len(commands) * command_height + (len(commands) - 1) * 10
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
            
            # 绘制命令列表
            cmd_y = header_height + config.padding
            
            if not commands:
                no_cmd_text = "该插件暂无可用命令"
                no_cmd_font = self._get_font(config.font_size)
                no_cmd_width, _ = self._calculate_text_size(no_cmd_text, no_cmd_font)
                no_cmd_x = (config.width - no_cmd_width) // 2
                draw.text((no_cmd_x, cmd_y), no_cmd_text, fill=theme.secondary_color, font=no_cmd_font)
            else:
                for i, command in enumerate(commands):
                    await self._draw_command_item(draw, command, config.padding, cmd_y, 
                                                config.width - config.padding * 2, command_height, i + 1)
                    cmd_y += command_height + 10
            
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
        theme = config.theme
        
        # 绘制背景
        self._draw_rounded_rectangle(
            draw, (x, y, x + width, y + height),
            config.border_radius, theme.card_background, theme.border_color
        )
        
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
            self._draw_rounded_rectangle(
                draw, (tag_x - 5, tag_y - 2, tag_x + admin_width + 5, tag_y + admin_height + 2),
                3, theme.primary_color
            )
            
            draw.text((tag_x, tag_y), admin_text, fill=theme.background_color, font=tag_font)
    
    async def render_command_detail(self, help_page: HelpPage, plugin: PluginInfo, command: CommandInfo) -> bytes:
        """渲染命令详情"""
        try:
            config = self.render_config
            theme = config.theme
            
            # 计算内容高度
            base_height = 200
            param_height = len(command.parameters) * 30
            example_height = len(command.examples) * 25
            total_height = base_height + param_height + example_height + config.padding * 2
            
            # 创建图片
            img = Image.new('RGB', (config.width, total_height), theme.background_color)
            draw = ImageDraw.Draw(img)
            
            # 绘制标题
            title_font = self._get_font(config.title_font_size)
            title_text = f"⚡ /{command.name}"
            title_width, title_height = self._calculate_text_size(title_text, title_font)
            title_x = (config.width - title_width) // 2
            title_y = config.padding
            
            draw.text((title_x, title_y), title_text, fill=theme.text_color, font=title_font)
            
            # 绘制插件名
            plugin_font = self._get_font(config.subtitle_font_size)
            plugin_text = f"来自插件: {plugin.name}"
            plugin_width, plugin_height = self._calculate_text_size(plugin_text, plugin_font)
            plugin_x = (config.width - plugin_width) // 2
            plugin_y = title_y + title_height + 10
            
            draw.text((plugin_x, plugin_y), plugin_text, fill=theme.secondary_color, font=plugin_font)
            
            # 绘制描述
            content_y = plugin_y + plugin_height + 20
            
            if command.description:
                desc_font = self._get_font(config.font_size)
                desc_lines = self._wrap_text(command.description, desc_font, config.width - config.padding * 2)
                
                for line in desc_lines:
                    line_width, line_height = self._calculate_text_size(line, desc_font)
                    line_x = (config.width - line_width) // 2
                    draw.text((line_x, content_y), line, fill=theme.text_color, font=desc_font)
                    content_y += line_height + 5
            
            content_y += 20
            
            # 绘制用法
            if command.usage:
                usage_font = self._get_font(config.font_size)
                usage_text = f"用法: /{command.name} {command.usage}"
                usage_width, usage_height = self._calculate_text_size(usage_text, usage_font)
                usage_x = (config.width - usage_width) // 2
                
                # 绘制用法背景
                self._draw_rounded_rectangle(
                    draw, (usage_x - 10, content_y - 5, usage_x + usage_width + 10, content_y + usage_height + 5),
                    config.border_radius, theme.card_background, theme.border_color
                )
                
                draw.text((usage_x, content_y), usage_text, fill=theme.primary_color, font=usage_font)
                content_y += usage_height + 20
            
            # 绘制参数
            if command.parameters:
                param_title_font = self._get_font(config.font_size)
                draw.text((config.padding, content_y), "参数:", fill=theme.text_color, font=param_title_font)
                content_y += config.font_size + 10
                
                param_font = self._get_font(config.subtitle_font_size)
                for param in command.parameters:
                    draw.text((config.padding + 20, content_y), f"• {param}", fill=theme.secondary_color, font=param_font)
                    content_y += 25
                
                content_y += 10
            
            # 绘制示例
            if command.examples:
                example_title_font = self._get_font(config.font_size)
                draw.text((config.padding, content_y), "示例:", fill=theme.text_color, font=example_title_font)
                content_y += config.font_size + 10
                
                example_font = self._get_font(config.subtitle_font_size)
                for example in command.examples:
                    draw.text((config.padding + 20, content_y), f"• {example}", fill=theme.primary_color, font=example_font)
                    content_y += 25
            
            # 保存为字节流
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"渲染命令详情失败: {e}")
            raise
