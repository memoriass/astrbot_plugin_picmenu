"""
插件信息收集器
"""
import inspect
import re
from typing import List, Dict, Any, Optional
from astrbot.api.star import Context
from astrbot.api import logger

from .models import PluginInfo, CommandInfo


class PluginInfoCollector:
    """插件信息收集器"""
    
    def __init__(self, context: Context):
        self.context = context
        
    async def collect_plugins(self, show_hidden: bool = False) -> List[PluginInfo]:
        """收集所有插件信息"""
        try:
            plugins = []
            
            # 获取所有已加载的插件
            all_stars = self.context.get_all_stars()
            
            for star_metadata in all_stars:
                try:
                    plugin_info = await self.collect_plugin_info(star_metadata)
                    if plugin_info and (show_hidden or not plugin_info.hidden):
                        plugins.append(plugin_info)
                except Exception as e:
                    logger.warning(f"收集插件信息失败: {star_metadata.name if hasattr(star_metadata, 'name') else 'Unknown'}: {e}")
            
            # 按名称排序
            plugins.sort(key=lambda p: p.name.lower())
            
            logger.info(f"收集到 {len(plugins)} 个插件信息")
            return plugins
            
        except Exception as e:
            logger.error(f"收集插件信息失败: {e}")
            return []
    
    async def collect_plugin_info(self, star_metadata) -> Optional[PluginInfo]:
        """收集单个插件信息"""
        try:
            # 获取插件实例
            star_instance = star_metadata.star_instance
            if not star_instance:
                return None
            
            # 获取基本信息
            name = getattr(star_metadata, 'name', star_instance.__class__.__name__)
            description = getattr(star_metadata, 'description', None)
            version = getattr(star_metadata, 'version', None)
            author = getattr(star_metadata, 'author', None)
            
            # 收集命令信息
            commands = await self.collect_commands(star_instance)
            
            # 判断是否为隐藏插件
            hidden = self.is_hidden_plugin(star_instance, star_metadata)
            
            # 获取插件类型
            plugin_type = getattr(star_metadata, 'type', 'application')
            if plugin_type == 'library':
                hidden = True  # library 类型默认隐藏
            
            return PluginInfo(
                name=name,
                description=description,
                version=version,
                author=author,
                commands=commands,
                hidden=hidden,
                plugin_type=plugin_type,
                usage=self.extract_usage(star_instance)
            )
            
        except Exception as e:
            logger.error(f"收集插件信息失败: {e}")
            return None
    
    async def collect_commands(self, star_instance) -> List[CommandInfo]:
        """收集插件的命令信息"""
        commands = []
        
        try:
            # 获取插件类的所有方法
            for method_name in dir(star_instance):
                method = getattr(star_instance, method_name)
                
                # 检查是否为命令方法
                if self.is_command_method(method):
                    command_info = self.extract_command_info(method, method_name)
                    if command_info:
                        commands.append(command_info)
            
            # 按命令名排序
            commands.sort(key=lambda c: c.name.lower())
            
        except Exception as e:
            logger.error(f"收集命令信息失败: {e}")
        
        return commands
    
    def is_command_method(self, method) -> bool:
        """检查方法是否为命令方法"""
        try:
            # 检查是否有 filter 装饰器
            if hasattr(method, '__wrapped__'):
                return True
            
            # 检查方法名是否包含命令相关的关键词
            method_name = getattr(method, '__name__', '')
            if any(keyword in method_name.lower() for keyword in ['command', 'handle', 'cmd']):
                return True
            
            # 检查是否为异步方法且有特定的参数签名
            if inspect.iscoroutinefunction(method):
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                if len(params) >= 2 and 'event' in params[1].lower():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def extract_command_info(self, method, method_name: str) -> Optional[CommandInfo]:
        """提取命令信息"""
        try:
            # 获取命令名称
            command_name = self.extract_command_name(method, method_name)
            if not command_name:
                return None
            
            # 获取描述
            description = self.extract_description(method)
            
            # 获取用法
            usage = self.extract_method_usage(method)
            
            # 获取参数
            parameters = self.extract_parameters(method)
            
            # 获取示例
            examples = self.extract_examples(method)
            
            # 检查是否隐藏
            hidden = self.is_hidden_command(method, method_name)
            
            # 检查是否需要管理员权限
            admin_only = self.is_admin_only_command(method)
            
            return CommandInfo(
                name=command_name,
                description=description,
                usage=usage,
                parameters=parameters,
                examples=examples,
                hidden=hidden,
                admin_only=admin_only
            )
            
        except Exception as e:
            logger.error(f"提取命令信息失败: {e}")
            return None
    
    def extract_command_name(self, method, method_name: str) -> Optional[str]:
        """提取命令名称"""
        try:
            # 尝试从装饰器获取
            if hasattr(method, '__wrapped__'):
                # 这里需要根据 AstrBot 的实际装饰器实现来获取命令名
                # 暂时使用方法名作为命令名
                pass
            
            # 从方法名推断命令名
            if method_name.endswith('_command'):
                return method_name[:-8]  # 移除 '_command' 后缀
            elif method_name.startswith('cmd_'):
                return method_name[4:]   # 移除 'cmd_' 前缀
            elif method_name.startswith('handle_'):
                return method_name[7:]   # 移除 'handle_' 前缀
            else:
                return method_name
                
        except Exception:
            return method_name
    
    def extract_description(self, method) -> Optional[str]:
        """提取命令描述"""
        try:
            doc = inspect.getdoc(method)
            if doc:
                # 获取第一行作为描述
                lines = doc.strip().split('\n')
                return lines[0].strip()
            return None
        except Exception:
            return None
    
    def extract_method_usage(self, method) -> Optional[str]:
        """提取方法用法"""
        try:
            sig = inspect.signature(method)
            params = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'event']:
                    continue
                
                if param.default == inspect.Parameter.empty:
                    params.append(f"<{param_name}>")
                else:
                    params.append(f"[{param_name}]")
            
            if params:
                return " ".join(params)
            return None
            
        except Exception:
            return None
    
    def extract_parameters(self, method) -> List[str]:
        """提取参数列表"""
        try:
            sig = inspect.signature(method)
            params = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'event']:
                    continue
                
                param_info = param_name
                if param.annotation != inspect.Parameter.empty:
                    param_info += f": {param.annotation.__name__}"
                
                if param.default != inspect.Parameter.empty:
                    param_info += f" = {param.default}"
                
                params.append(param_info)
            
            return params
            
        except Exception:
            return []
    
    def extract_examples(self, method) -> List[str]:
        """提取使用示例"""
        try:
            doc = inspect.getdoc(method)
            if not doc:
                return []
            
            examples = []
            lines = doc.split('\n')
            in_examples = False
            
            for line in lines:
                line = line.strip()
                if '示例' in line or 'example' in line.lower():
                    in_examples = True
                    continue
                
                if in_examples and line:
                    if line.startswith('/') or line.startswith('!'):
                        examples.append(line)
            
            return examples
            
        except Exception:
            return []
    
    def is_hidden_command(self, method, method_name: str) -> bool:
        """检查命令是否隐藏"""
        try:
            # 检查方法名
            if method_name.startswith('_') or 'hidden' in method_name.lower():
                return True
            
            # 检查文档字符串
            doc = inspect.getdoc(method)
            if doc and ('hidden' in doc.lower() or '隐藏' in doc):
                return True
            
            return False
            
        except Exception:
            return False
    
    def is_admin_only_command(self, method) -> bool:
        """检查命令是否仅管理员可用"""
        try:
            # 检查方法名
            method_name = getattr(method, '__name__', '')
            if 'admin' in method_name.lower():
                return True
            
            # 检查文档字符串
            doc = inspect.getdoc(method)
            if doc and ('admin' in doc.lower() or '管理员' in doc):
                return True
            
            return False
            
        except Exception:
            return False
    
    def is_hidden_plugin(self, star_instance, star_metadata) -> bool:
        """检查插件是否隐藏"""
        try:
            # 检查插件类型
            plugin_type = getattr(star_metadata, 'type', 'application')
            if plugin_type == 'library':
                return True
            
            # 检查插件名称
            name = getattr(star_metadata, 'name', '')
            if name.startswith('_') or 'hidden' in name.lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    def extract_usage(self, star_instance) -> Optional[str]:
        """提取插件用法"""
        try:
            # 尝试从类文档字符串获取
            doc = inspect.getdoc(star_instance.__class__)
            if doc:
                lines = doc.strip().split('\n')
                for line in lines:
                    if '用法' in line or 'usage' in line.lower():
                        return line.strip()
            
            return None
            
        except Exception:
            return None
