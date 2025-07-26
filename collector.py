"""
插件信息收集器 - 重写版本
根据AstrBot文档正确获取插件信息和指令
"""
import inspect
from typing import List, Optional

from astrbot.api import logger
from astrbot.api.star import Context

from .models import CommandInfo, PluginInfo


class PluginInfoCollector:
    """插件信息收集器 - 重写版本"""
    
    def __init__(self, context: Context):
        self.context = context

    async def collect_plugins(self, show_hidden: bool = False) -> List[PluginInfo]:
        """收集所有插件信息"""
        try:
            plugins = []
            
            # 根据文档，使用 context.get_all_stars() 获取所有已加载的插件
            all_stars = self.context.get_all_stars()
            logger.debug(f"获取到 {len(all_stars)} 个StarMetadata对象")
            
            for star_metadata in all_stars:
                try:
                    # 获取插件名称用于过滤
                    plugin_name = getattr(star_metadata, 'name', 'Unknown')
                    
                    # 排除系统插件，只保留用户插件
                    if self._should_exclude_plugin(star_metadata, plugin_name):
                        logger.debug(f"跳过系统插件: {plugin_name}")
                        continue
                    
                    plugin_info = await self.collect_plugin_info(star_metadata)
                    if plugin_info and (show_hidden or not plugin_info.hidden):
                        plugins.append(plugin_info)
                        logger.debug(f"收集到插件: {plugin_info.name} ({len(plugin_info.commands)} 个命令)")
                        
                except Exception as e:
                    plugin_name = getattr(star_metadata, 'name', 'Unknown')
                    logger.warning(f"收集插件信息失败: {plugin_name}: {e}")
            
            # 按名称排序
            plugins.sort(key=lambda p: p.name.lower())
            
            logger.info(f"收集到 {len(plugins)} 个插件信息")
            return plugins
            
        except Exception as e:
            logger.error(f"收集插件信息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _should_exclude_plugin(self, star_metadata, plugin_name: str) -> bool:
        """判断是否应该排除插件"""
        try:
            # 检查模块路径
            module_path = getattr(star_metadata, 'module_path', '')
            if not module_path:
                # 尝试从其他属性获取
                if hasattr(star_metadata, 'star_instance'):
                    star_instance = star_metadata.star_instance
                    module_path = getattr(star_instance, '__module__', '')
                elif hasattr(star_metadata, 'star_cls'):
                    star_cls = star_metadata.star_cls
                    module_path = getattr(star_cls, '__module__', '')
            
            logger.debug(f"插件 {plugin_name} 的模块路径: {module_path}")
            
            # 排除packages文件夹中的插件，但astrbot文件夹除外
            if 'packages' in module_path and 'astrbot' not in module_path:
                return True

            # 保留以astrbot_plugin_开头的插件（用户插件）
            if plugin_name.startswith('astrbot_plugin_'):
                return False

            # 保留astrbot插件（核心功能插件）
            if plugin_name == 'astrbot':
                return False

            # 排除其他系统插件
            system_plugins = [
                'python_interpreter', 'code_interpreter', 'websearch',
                'function_calling', 'tts', 'stt', 'image_generation'
            ]

            if plugin_name in system_plugins:
                return True

            return False
            
        except Exception as e:
            logger.debug(f"检查插件排除状态失败: {e}")
            return False

    async def collect_plugin_info(self, star_metadata) -> Optional[PluginInfo]:
        """收集单个插件信息"""
        try:
            # 获取基本信息
            name = getattr(star_metadata, 'name', 'Unknown')
            description = getattr(star_metadata, 'desc', None) or getattr(star_metadata, 'description', None)
            version = getattr(star_metadata, 'version', None)
            author = getattr(star_metadata, 'author', None)
            
            logger.debug(f"收集插件信息: {name} by {author}")
            
            # 获取插件实例用于命令收集
            star_instance = self._get_star_instance(star_metadata, name)
            
            if not star_instance:
                logger.warning(f"无法获取插件实例: {name}")
                return None
            
            # 收集命令信息
            commands = await self.collect_commands_from_registry(star_metadata, star_instance)
            
            # 判断是否为隐藏插件
            hidden = self._is_hidden_plugin(star_metadata, name)
            
            # 检查插件是否激活
            activated = getattr(star_metadata, 'activated', True)
            if not activated:
                hidden = True
            
            # 获取插件类型
            plugin_type = getattr(star_metadata, 'type', 'application')
            if plugin_type == 'library':
                hidden = True
            
            plugin_info = PluginInfo(
                name=name,
                description=description,
                version=version,
                author=author,
                commands=commands,
                hidden=hidden,
                plugin_type=plugin_type,
                usage=self._extract_usage_from_instance(star_instance)
            )
            
            logger.debug(f"插件 {name} 收集完成: {len(commands)} 个命令")
            return plugin_info
            
        except Exception as e:
            plugin_name = getattr(star_metadata, 'name', 'Unknown')
            logger.error(f"收集插件信息失败 {plugin_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _get_star_instance(self, star_metadata, name: str):
        """获取插件实例"""
        # 检查常见的实例属性名
        for attr_name in ['star_instance', 'instance', 'star', 'plugin_instance']:
            if hasattr(star_metadata, attr_name):
                star_instance = getattr(star_metadata, attr_name)
                if star_instance:
                    logger.debug(f"从 {attr_name} 获取到插件实例: {name}")
                    return star_instance
        
        # 如果还没找到实例，检查是否有star_cls
        if hasattr(star_metadata, 'star_cls'):
            star_cls = star_metadata.star_cls
            if hasattr(star_cls, '__name__'):
                logger.debug(f"找到star_cls: {star_cls.__name__}")
                return star_metadata
        
        # 使用star_metadata本身
        logger.debug(f"使用star_metadata作为实例: {name}")
        return star_metadata
    
    def _is_hidden_plugin(self, star_metadata, name: str) -> bool:
        """判断插件是否隐藏"""
        try:
            # 检查插件类型
            plugin_type = getattr(star_metadata, 'type', 'application')
            if plugin_type == 'library':
                return True
            
            # 检查插件名称
            if name.startswith('_') or 'hidden' in name.lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    def _extract_usage_from_instance(self, star_instance) -> Optional[str]:
        """从插件实例提取用法信息"""
        try:
            # 检查插件的文档字符串
            doc = inspect.getdoc(star_instance.__class__)
            if doc and '用法:' in doc:
                lines = doc.split('\n')
                for line in lines:
                    if '用法:' in line:
                        return line.split('用法:')[1].strip()
            
            return None
        except Exception:
            return None

    async def collect_commands_from_registry(self, star_metadata, star_instance) -> List[CommandInfo]:
        """从star_handlers_registry收集插件的命令信息"""
        commands = []

        try:
            # 使用star_handlers_registry获取命令信息
            try:
                from astrbot.core.star.filter.command import CommandFilter
                from astrbot.core.star.filter.command_group import CommandGroupFilter
                from astrbot.core.star.star_handler import (
                    StarHandlerMetadata,
                    star_handlers_registry,
                )

                # 获取插件的模块路径
                plugin_name = getattr(star_metadata, 'name', 'Unknown')
                module_path = self._get_module_path(star_metadata, star_instance)
                
                logger.debug(f"插件 {plugin_name} 的模块路径: {module_path}")
                logger.debug(f"star_handlers_registry 中有 {len(star_handlers_registry)} 个处理器")

                if module_path:
                    # 遍历star_handlers_registry查找匹配的命令
                    logger.info(f"开始为插件 {plugin_name} 匹配命令，模块路径: {module_path}")

                    for handler in star_handlers_registry:
                        if isinstance(handler, StarHandlerMetadata):
                            handler_module = getattr(handler, 'handler_module_path', '')

                            # 改进模块路径匹配逻辑
                            is_match = self._is_module_match(handler_module, module_path, plugin_name)

                            if is_match:
                                logger.info(f"✅ 找到匹配的handler: {handler.handler_name} in {handler_module}")

                                # 提取命令信息
                                for filter_ in handler.event_filters:
                                    if isinstance(filter_, CommandFilter):
                                        cmd = self._create_command_from_filter(filter_, handler)
                                        if cmd:
                                            commands.append(cmd)
                                            logger.info(f"✅ 从registry找到命令: {filter_.command_name} for {plugin_name}")
                                    elif isinstance(filter_, CommandGroupFilter):
                                        cmd = self._create_command_group_from_filter(filter_, handler)
                                        if cmd:
                                            commands.append(cmd)
                                            logger.info(f"✅ 从registry找到命令组: {filter_.group_name} for {plugin_name}")

                    logger.info(f"插件 {plugin_name} 从registry收集到 {len(commands)} 个命令")

            except ImportError as e:
                logger.debug(f"无法导入star_handlers_registry: {e}")
            except Exception as e:
                logger.debug(f"从registry获取命令失败: {e}")

            # 如果从registry获取失败，回退到方法检查
            if not commands:
                logger.debug(f"从registry未找到命令，使用方法检查: {plugin_name}")
                commands = await self._collect_commands_from_methods(star_instance)

            # 按命令名排序
            commands.sort(key=lambda c: c.name.lower())

            if commands:
                logger.debug(f"插件 {plugin_name} 收集到 {len(commands)} 个命令")

        except Exception as e:
            logger.error(f"收集命令信息失败: {e}")

        return commands
    
    def _get_module_path(self, star_metadata, star_instance) -> str:
        """获取插件的模块路径"""
        # 尝试多种方式获取模块路径
        module_path = getattr(star_metadata, 'module_path', '')
        
        if not module_path and star_instance:
            module_path = getattr(star_instance, '__module__', '')
            
        if not module_path and star_instance:
            module_path = getattr(star_instance.__class__, '__module__', '')
            
        if not module_path and hasattr(star_metadata, 'star_cls'):
            star_cls = star_metadata.star_cls
            module_path = getattr(star_cls, '__module__', '')
        
        return module_path

    def _is_module_match(self, handler_module: str, module_path: str, plugin_name: str) -> bool:
        """判断模块路径是否匹配 - 严格匹配版本"""
        if not handler_module or not module_path:
            return False

        # 精确匹配
        if handler_module == module_path:
            return True

        # 对于用户插件，使用严格的插件名匹配
        if plugin_name.startswith('astrbot_plugin_'):
            # 只有当handler_module包含完整的插件名时才匹配
            if plugin_name in handler_module and plugin_name in module_path:
                return True
            return False

        # 对于astrbot核心插件，使用更严格的匹配
        if plugin_name == 'astrbot':
            # 确保handler_module确实属于astrbot插件
            if ('astrbot' in handler_module and
                'astrbot' in module_path and
                'astrbot_plugin_' not in handler_module):  # 排除用户插件
                return True
            return False

        # 对于其他插件，使用精确匹配
        return False

    def _create_command_from_filter(self, filter_, handler) -> Optional[CommandInfo]:
        """从CommandFilter创建CommandInfo"""
        try:
            return CommandInfo(
                name=filter_.command_name,
                description=getattr(handler, 'desc', None) or f"{filter_.command_name}命令",
                usage=self._extract_usage_from_handler(handler),
                aliases=getattr(filter_, 'aliases', []),
                parameters=self._extract_parameters_from_handler(handler),
                examples=self._extract_examples_from_handler(handler),
                hidden=False,
                admin_only=self._is_admin_command_from_handler(handler)
            )
        except Exception as e:
            logger.debug(f"创建命令失败: {e}")
            return None

    def _create_command_group_from_filter(self, filter_, handler) -> Optional[CommandInfo]:
        """从CommandGroupFilter创建CommandInfo"""
        try:
            return CommandInfo(
                name=filter_.group_name,
                description=getattr(handler, 'desc', None) or f"{filter_.group_name}命令组",
                usage=None,
                aliases=[],
                parameters=[],
                examples=[],
                hidden=False,
                admin_only=self._is_admin_command_from_handler(handler)
            )
        except Exception as e:
            logger.debug(f"创建命令组失败: {e}")
            return None

    async def _collect_commands_from_methods(self, star_instance) -> List[CommandInfo]:
        """从方法检查收集命令（回退方法）"""
        commands = []

        try:
            for method_name in dir(star_instance):
                if method_name.startswith('_'):
                    continue

                method = getattr(star_instance, method_name)

                # 检查是否为命令方法
                if self._is_command_method(method):
                    command_info = self._extract_command_info_from_method(method, method_name)
                    if command_info:
                        commands.append(command_info)
                        logger.debug(f"从方法检查找到命令: {command_info.name}")

        except Exception as e:
            logger.debug(f"从方法收集命令失败: {e}")

        return commands

    def _extract_usage_from_handler(self, handler) -> Optional[str]:
        """从处理器提取用法信息"""
        try:
            desc = getattr(handler, 'desc', '')
            if desc and '用法:' in desc:
                lines = desc.split('\n')
                for line in lines:
                    if '用法:' in line:
                        return line.split('用法:')[1].strip()
            return None
        except Exception:
            return None

    def _extract_parameters_from_handler(self, handler) -> List[str]:
        """从处理器提取参数信息"""
        try:
            desc = getattr(handler, 'desc', '')
            if desc and '参数:' in desc:
                lines = desc.split('\n')
                params = []
                in_params = False
                for line in lines:
                    line = line.strip()
                    if '参数:' in line:
                        in_params = True
                        continue
                    elif in_params and line.startswith('-'):
                        params.append(line[1:].strip())
                    elif in_params and not line:
                        break
                return params
            return []
        except Exception:
            return []

    def _extract_examples_from_handler(self, handler) -> List[str]:
        """从处理器提取示例信息"""
        try:
            desc = getattr(handler, 'desc', '')
            if desc and '示例:' in desc:
                lines = desc.split('\n')
                examples = []
                in_examples = False
                for line in lines:
                    line = line.strip()
                    if '示例:' in line:
                        in_examples = True
                        continue
                    elif in_examples and line.startswith('/'):
                        examples.append(line)
                    elif in_examples and not line:
                        break
                return examples
            return []
        except Exception:
            return []

    def _is_admin_command_from_handler(self, handler) -> bool:
        """从处理器判断是否为管理员命令"""
        try:
            # 检查是否有权限过滤器
            from astrbot.api.event.filter import PermissionType
            from astrbot.core.star.filter.permission import PermissionTypeFilter

            for filter_ in getattr(handler, 'event_filters', []):
                if hasattr(filter_, 'permission_type'):
                    return getattr(filter_, 'permission_type') == PermissionType.ADMIN

            # 检查方法名或描述
            handler_name = getattr(handler, 'handler_name', '')
            desc = getattr(handler, 'desc', '')

            if 'admin' in handler_name.lower() or 'admin' in desc.lower():
                return True

            return False

        except Exception:
            return False

    def _is_command_method(self, method) -> bool:
        """检查方法是否为命令方法"""
        try:
            if not callable(method):
                return False

            # 检查是否为异步函数或异步生成器函数（AstrBot命令的特征）
            if not (inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(method)):
                return False

            return True

        except Exception:
            return False

    def _extract_command_info_from_method(self, method, method_name: str) -> Optional[CommandInfo]:
        """从方法提取命令信息"""
        try:
            # 获取方法的文档字符串作为描述
            description = inspect.getdoc(method) or f"{method_name}命令"

            return CommandInfo(
                name=method_name,
                description=description,
                usage=None,
                aliases=[],
                parameters=[],
                examples=[],
                hidden=False,
                admin_only='admin' in method_name.lower()
            )
        except Exception as e:
            logger.debug(f"提取方法命令信息失败: {e}")
            return None
