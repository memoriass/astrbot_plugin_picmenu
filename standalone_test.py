#!/usr/bin/env python3
"""
PicMenu 插件独立测试脚本
不依赖 AstrBot 环境的测试
"""

import asyncio
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from models import PluginInfo, CommandInfo, HelpPage, ThemeConfig, RenderConfig


class StandaloneTester:
    def __init__(self):
        pass
    
    def create_mock_plugins(self):
        """创建模拟插件数据"""
        plugins = []
        
        # 插件1: 基础功能插件
        plugin1 = PluginInfo(
            name="基础功能",
            description="提供机器人的基础功能和管理命令",
            version="1.0.0",
            author="AstrBot",
            commands=[
                CommandInfo(
                    name="help",
                    description="显示帮助信息",
                    usage="[插件名] [命令名]",
                    examples=["/help", "/help 基础功能", "/help 基础功能 status"]
                ),
                CommandInfo(
                    name="status",
                    description="查看机器人状态",
                    usage="",
                    examples=["/status"]
                ),
                CommandInfo(
                    name="admin",
                    description="管理员命令",
                    usage="<操作>",
                    admin_only=True,
                    examples=["/admin reload", "/admin stop"]
                )
            ]
        )
        plugins.append(plugin1)
        
        # 插件2: 娱乐插件
        plugin2 = PluginInfo(
            name="娱乐功能",
            description="提供各种娱乐和互动功能",
            version="2.1.0",
            author="Community",
            commands=[
                CommandInfo(
                    name="roll",
                    description="掷骰子",
                    usage="[面数]",
                    examples=["/roll", "/roll 20"]
                ),
                CommandInfo(
                    name="joke",
                    description="随机笑话",
                    usage="",
                    examples=["/joke"]
                )
            ]
        )
        plugins.append(plugin2)
        
        # 插件3: 隐藏插件
        plugin3 = PluginInfo(
            name="调试工具",
            description="开发和调试用的工具集合",
            version="0.9.0",
            author="Developer",
            hidden=True,
            commands=[
                CommandInfo(
                    name="debug",
                    description="调试信息",
                    hidden=True,
                    admin_only=True
                )
            ]
        )
        plugins.append(plugin3)
        
        return plugins
    
    def test_models(self):
        """测试数据模型"""
        print("=== 测试数据模型 ===")
        
        # 测试 CommandInfo
        cmd = CommandInfo(
            name="test",
            description="测试命令",
            usage="<参数>",
            examples=["/test hello"]
        )
        print(f"命令: {cmd.name} - {cmd.description}")
        assert cmd.name == "test"
        assert cmd.description == "测试命令"
        assert not cmd.hidden
        assert not cmd.admin_only
        
        # 测试 PluginInfo
        plugin = PluginInfo(
            name="测试插件",
            description="这是一个测试插件",
            commands=[cmd]
        )
        print(f"插件: {plugin.name} - {plugin.command_count} 个命令")
        print(f"副标题: {plugin.subtitle}")
        assert plugin.name == "测试插件"
        assert plugin.command_count == 1
        assert len(plugin.get_visible_commands()) == 1
        
        # 测试 ThemeConfig
        light_theme = ThemeConfig.light_theme()
        dark_theme = ThemeConfig.dark_theme()
        print(f"浅色主题: {light_theme.name}")
        print(f"深色主题: {dark_theme.name}")
        assert light_theme.name == "light"
        assert dark_theme.name == "dark"
        assert light_theme.background_color == "#FFFFFF"
        assert dark_theme.background_color == "#1E1E1E"
        
        print("✅ 数据模型测试通过\n")
    
    def test_fuzzy_search(self):
        """测试模糊搜索"""
        print("=== 测试模糊搜索 ===")
        
        try:
            from fuzzywuzzy import fuzz
            
            plugins = self.create_mock_plugins()
            
            # 模拟搜索功能
            query = "基础"
            results = []
            
            for plugin in plugins:
                score = fuzz.partial_ratio(query, plugin.name)
                if score >= 60:
                    results.append((plugin, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"搜索 '{query}' 的结果:")
            for plugin, score in results:
                print(f"  {plugin.name} (匹配度: {score})")
            
            assert len(results) > 0
            assert results[0][0].name == "基础功能"
            
            print("✅ 模糊搜索测试通过\n")
            
        except ImportError:
            print("⚠️  fuzzywuzzy 未安装，跳过模糊搜索测试\n")
    
    def test_pinyin_search(self):
        """测试拼音搜索"""
        print("=== 测试拼音搜索 ===")
        
        try:
            from pypinyin import lazy_pinyin, Style
            
            # 测试拼音转换
            text = "基础功能"
            pinyin = "".join(lazy_pinyin(text, style=Style.NORMAL))
            print(f"'{text}' 的拼音: {pinyin}")
            
            assert "ji" in pinyin
            assert "chu" in pinyin
            
            print("✅ 拼音搜索测试通过\n")
            
        except ImportError:
            print("⚠️  pypinyin 未安装，跳过拼音搜索测试\n")
    
    def test_theme_config(self):
        """测试主题配置"""
        print("=== 测试主题配置 ===")
        
        # 测试浅色主题
        light = ThemeConfig.light_theme()
        print(f"浅色主题背景: {light.background_color}")
        print(f"浅色主题文字: {light.text_color}")
        assert light.background_color == "#FFFFFF"
        assert light.text_color == "#333333"
        
        # 测试深色主题
        dark = ThemeConfig.dark_theme()
        print(f"深色主题背景: {dark.background_color}")
        print(f"深色主题文字: {dark.text_color}")
        assert dark.background_color == "#1E1E1E"
        assert dark.text_color == "#FFFFFF"
        
        # 测试渲染配置
        render_config = RenderConfig(width=800, font_size=16)
        print(f"渲染配置宽度: {render_config.width}")
        print(f"标题字体大小: {render_config.title_font_size}")
        assert render_config.width == 800
        assert render_config.title_font_size == 24  # 16 * 1.5
        
        print("✅ 主题配置测试通过\n")
    
    def test_help_page(self):
        """测试帮助页面"""
        print("=== 测试帮助页面 ===")
        
        plugins = self.create_mock_plugins()
        
        # 测试主页
        main_page = HelpPage(
            title="主页",
            plugins=plugins,
            show_hidden=False
        )
        
        visible_count = len(main_page.visible_plugins)
        total_count = len(plugins)
        print(f"总插件数: {total_count}")
        print(f"可见插件数: {visible_count}")
        assert total_count == 3
        assert visible_count == 2  # 隐藏了1个
        
        # 测试显示隐藏插件
        hidden_page = HelpPage(
            title="主页",
            plugins=plugins,
            show_hidden=True
        )
        
        hidden_visible_count = len(hidden_page.visible_plugins)
        print(f"显示隐藏后可见插件数: {hidden_visible_count}")
        assert hidden_visible_count == 3
        
        print("✅ 帮助页面测试通过\n")
    
    def test_command_info(self):
        """测试命令信息"""
        print("=== 测试命令信息 ===")
        
        # 测试普通命令
        normal_cmd = CommandInfo(
            name="normal",
            description="普通命令",
            usage="<参数>",
            examples=["/normal test"]
        )
        
        print(f"普通命令: {normal_cmd.name}")
        print(f"隐藏状态: {normal_cmd.hidden}")
        print(f"管理员专用: {normal_cmd.admin_only}")
        assert normal_cmd.name == "normal"
        assert not normal_cmd.hidden
        assert not normal_cmd.admin_only
        
        # 测试管理员命令
        admin_cmd = CommandInfo(
            name="admin",
            description="管理员命令",
            admin_only=True,
            hidden=False
        )
        
        print(f"管理员命令: {admin_cmd.name}")
        print(f"管理员专用: {admin_cmd.admin_only}")
        assert admin_cmd.name == "admin"
        assert admin_cmd.admin_only
        
        print("✅ 命令信息测试通过\n")
    
    def test_plugin_info(self):
        """测试插件信息"""
        print("=== 测试插件信息 ===")
        
        plugins = self.create_mock_plugins()
        
        # 测试基础功能插件
        basic_plugin = plugins[0]
        print(f"插件名: {basic_plugin.name}")
        print(f"命令数: {basic_plugin.command_count}")
        print(f"副标题: {basic_plugin.subtitle}")
        
        assert basic_plugin.name == "基础功能"
        assert basic_plugin.command_count == 3
        assert "AstrBot" in basic_plugin.subtitle
        assert "1.0.0" in basic_plugin.subtitle
        
        # 测试可见命令
        visible_commands = basic_plugin.get_visible_commands(show_hidden=False)
        all_commands = basic_plugin.get_visible_commands(show_hidden=True)
        
        print(f"可见命令数: {len(visible_commands)}")
        print(f"全部命令数: {len(all_commands)}")
        
        assert len(visible_commands) == 3  # 没有隐藏命令
        assert len(all_commands) == 3
        
        print("✅ 插件信息测试通过\n")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始 PicMenu 插件独立测试")
        print("=" * 50)
        
        try:
            self.test_models()
            self.test_fuzzy_search()
            self.test_pinyin_search()
            self.test_theme_config()
            self.test_help_page()
            self.test_command_info()
            self.test_plugin_info()
            
            print("=" * 50)
            print("🎉 所有测试完成！")
            
        except Exception as e:
            print(f"\n❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    tester = StandaloneTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
