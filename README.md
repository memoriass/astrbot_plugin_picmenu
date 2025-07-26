# PicMenu - 新一代图片帮助插件

基于 NoneBot 插件 `nonebot-plugin-picmenu-next` 开发的 AstrBot 版本，提供美观的图片化帮助界面和智能搜索功能。

## 功能特性

- 🎨 **美观的图片界面** - 生成精美的图片化帮助菜单
- 🔍 **智能搜索系统** - 支持插件名称和命令的模糊匹配
- 🈯 **拼音搜索支持** - 中文环境下的拼音搜索功能
- 📱 **三级菜单导航** - 主页 → 插件详情 → 命令详情
- 🎭 **多主题支持** - 浅色/深色主题切换
- 💾 **智能缓存系统** - 缓存生成的图片提高响应速度
- 👥 **权限控制** - 管理员权限和隐藏内容管理
- ⚙️ **高度可配置** - 丰富的配置选项满足不同需求

## 安装配置

### 1. 插件安装

将插件文件夹放置到 AstrBot 的 `data/plugins/` 目录下：

```
AstrBot/
└── data/
    └── plugins/
        └── astrbot_plugin_picmenu/
            ├── main.py
            ├── models.py
            ├── collector.py
            ├── renderer.py
            ├── metadata.yaml
            ├── requirements.txt
            ├── _conf_schema.json
            └── README.md
```

### 2. 依赖安装

插件需要以下依赖包：
- `Pillow>=9.0.0` - 图片处理
- `fuzzywuzzy>=0.18.0` - 模糊搜索
- `python-levenshtein>=0.12.0` - 字符串匹配优化
- `pypinyin>=0.47.0` - 拼音转换

### 3. 配置插件

在 AstrBot 管理面板中配置以下参数：

**界面配置：**
- `theme`: 界面主题（light/dark/auto）
- `image_width`: 图片宽度（默认: 800px）
- `font_size`: 基础字体大小（默认: 16px）

**功能配置：**
- `fuzzy_search_threshold`: 模糊搜索阈值（默认: 60）
- `enable_pinyin_search`: 启用拼音搜索（默认: true）
- `max_plugins_per_page`: 每页最大插件数（默认: 12）

**权限配置：**
- `admin_users`: 管理员用户ID列表
- `show_hidden_plugins`: 显示隐藏插件（默认: false）
- `admin_only_hidden`: 仅管理员查看隐藏内容（默认: true）

**缓存配置：**
- `cache_enabled`: 启用缓存（默认: true）
- `cache_expire_minutes`: 缓存过期时间（默认: 30分钟）

## 使用方法

### 基本命令

- `/help` - 显示主帮助页面
- `/help <插件名>` - 显示指定插件的详情
- `/help <插件名> <命令名>` - 显示指定命令的详情
- `/帮助` - help 命令的中文别名
- `/菜单` - help 命令的菜单别名

### 搜索功能

支持多种搜索方式：

```bash
# 精确匹配
/help 基础功能

# 模糊搜索
/help 基础

# 拼音搜索
/help jc

# 数字索引
/help 1        # 第1个插件
/help 1 2      # 第1个插件的第2个命令
```

### 管理命令

- `/picmenu_status` - 查看插件状态
- `/picmenu_clear_cache` - 清理缓存（仅管理员）

## 界面展示

### 主页面
- 显示所有可用插件的卡片式布局
- 每个插件显示名称、描述、命令数量
- 支持分页显示和主题切换

### 插件详情页
- 显示插件的详细信息
- 列出所有可用命令
- 显示插件版本、作者等元信息

### 命令详情页
- 显示命令的完整说明
- 包含用法、参数、示例等信息
- 标识管理员专用命令

## 配置示例

```json
{
  "theme": "light",
  "image_width": 800,
  "font_size": 16,
  "fuzzy_search_threshold": 60,
  "enable_pinyin_search": true,
  "max_plugins_per_page": 12,
  "admin_users": "123456789,987654321",
  "show_hidden_plugins": false,
  "admin_only_hidden": true,
  "cache_enabled": true,
  "cache_expire_minutes": 30
}
```

## 开发说明

### 插件架构

```
astrbot_plugin_picmenu/
├── main.py          # 主插件类和命令处理
├── models.py        # 数据模型定义
├── collector.py     # 插件信息收集器
├── renderer.py      # 图片渲染器
├── __init__.py      # 包初始化
└── test_plugin.py   # 测试脚本
```

### 核心组件

1. **PluginInfoCollector** - 自动收集 AstrBot 插件信息
2. **HelpImageRenderer** - 生成美观的帮助图片
3. **模糊搜索引擎** - 基于 fuzzywuzzy 的智能搜索
4. **缓存系统** - 内存缓存提高响应速度
5. **主题系统** - 支持浅色和深色主题

### 扩展开发

可以通过以下方式扩展插件：

1. **自定义主题** - 修改 `ThemeConfig` 类
2. **新增渲染模式** - 扩展 `HelpImageRenderer` 类
3. **改进搜索算法** - 优化模糊搜索逻辑
4. **添加新的页面类型** - 扩展 `PageType` 枚举

## 性能优化

- **智能缓存** - 缓存生成的图片避免重复渲染
- **异步处理** - 所有图片生成都是异步的
- **内存管理** - 自动清理过期缓存
- **字体优化** - 智能字体选择和大小调整

## 故障排除

### 常见问题

1. **图片生成失败**
   ```
   错误：PIL 相关错误
   解决：确保 Pillow 库正确安装
   ```

2. **搜索功能异常**
   ```
   错误：fuzzywuzzy 相关错误
   解决：安装 python-levenshtein 优化包
   ```

3. **拼音搜索不工作**
   ```
   错误：pypinyin 导入失败
   解决：安装 pypinyin 包
   ```

4. **字体显示异常**
   ```
   错误：中文字符显示为方块
   解决：确保系统有中文字体
   ```

### 调试方法

1. 查看 AstrBot 日志中的 PicMenu 相关信息
2. 使用 `/picmenu_status` 检查插件状态
3. 运行测试脚本验证功能
4. 检查配置参数是否正确

## 从 NoneBot 迁移

本插件基于 `nonebot-plugin-picmenu-next` 开发，主要改进：

### 功能对比

| 功能 | NoneBot 版本 | AstrBot 版本 |
|------|-------------|-------------|
| 图片生成 | ✅ | ✅ 优化渲染 |
| 模糊搜索 | ✅ | ✅ 增强算法 |
| 拼音搜索 | ✅ | ✅ 完全兼容 |
| 主题支持 | ✅ | ✅ 新增配置 |
| 缓存系统 | ✅ | ✅ 智能管理 |
| 权限控制 | ✅ | ✅ 灵活配置 |
| 配置管理 | 环境变量 | 可视化界面 |

### 迁移优势

1. **更好的集成** - 深度集成 AstrBot 插件系统
2. **可视化配置** - 无需修改配置文件
3. **多平台支持** - 支持更多消息平台
4. **增强功能** - 更多配置选项和优化
5. **更好的维护性** - 清晰的代码结构

## 许可证

本插件遵循 MIT 许可证。

## 致谢

感谢原始 NoneBot 插件 `nonebot-plugin-picmenu-next` 的开发者提供的优秀设计思路。
