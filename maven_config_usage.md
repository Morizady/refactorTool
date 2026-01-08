# Maven配置使用说明

## 📋 概述

现在Maven依赖分析器已经支持从配置文件读取Maven仓库路径，无需在代码中硬编码路径。

## 🔧 配置方法

### 1. 修改config.yml文件

在`config.yml`文件中已经添加了Maven配置部分：

```yaml
# Maven配置
maven:
  # Maven本地仓库路径
  repository_path: "D:\\Program Files\\Apache\\apache-maven-repository"
  
  # Maven设置文件路径 (可选)
  settings_file: ""
  
  # 是否启用Maven依赖分析
  enable_dependency_analysis: true
```

### 2. 路径配置说明

- **repository_path**: Maven本地仓库的完整路径
  - Windows路径使用双反斜杠 `\\` 或正斜杠 `/`
  - 示例: `"D:\\Program Files\\Apache\\apache-maven-repository"`
  - 示例: `"D:/Program Files/Apache/apache-maven-repository"`

- **settings_file**: Maven设置文件路径（可选）
  - 如果不需要特殊设置，保持为空字符串

- **enable_dependency_analysis**: 是否启用Maven依赖分析
  - 设置为 `true` 启用，`false` 禁用

## 🚀 使用方法

### 1. 直接使用（推荐）

```python
from maven_dependency_analyzer import MavenDependencyAnalyzer

# 不传入路径参数，自动使用配置文件中的路径
analyzer = MavenDependencyAnalyzer()

# 解析POM文件
dependencies = analyzer.parse_pom("path/to/pom.xml")

# 生成分析报告
analyzer.generate_dependency_report("output/maven_report.md")
```

### 2. 手动指定路径（覆盖配置）

```python
from maven_dependency_analyzer import MavenDependencyAnalyzer

# 手动指定路径，会覆盖配置文件中的设置
analyzer = MavenDependencyAnalyzer("custom/maven/repository/path")
```

### 3. 使用配置加载器

```python
from config_loader import get_config

config = get_config()

# 获取Maven仓库路径
repo_path = config.get_maven_repository_path()
print(f"Maven仓库路径: {repo_path}")

# 检查是否启用Maven依赖分析
if config.is_maven_dependency_analysis_enabled():
    print("Maven依赖分析已启用")
```

## 🧪 测试配置

运行测试脚本验证配置是否正确：

```bash
python test_maven_config.py
```

测试脚本会：
1. 验证配置文件加载
2. 检查Maven仓库路径是否存在
3. 创建测试POM文件进行完整测试
4. 生成分析报告

## 📊 功能特性

### ✅ 支持的功能

- 从配置文件自动读取Maven仓库路径
- 自动验证Maven仓库是否存在
- 支持手动路径覆盖配置文件设置
- 完整的依赖解析和JAR包分析
- 生成详细的分析报告
- 支持多种路径格式（Windows/Linux/macOS）

### 📋 分析内容

- 解析pom.xml中的所有依赖
- 从本地Maven仓库查找对应JAR包
- 分析JAR包内容（类、包、MANIFEST等）
- 按scope分类统计
- 识别缺失的依赖
- 生成Markdown格式的详细报告

## 🔍 故障排除

### 1. Maven仓库路径不存在

**问题**: 日志显示"Maven仓库路径不存在"

**解决方案**:
- 检查`config.yml`中的`maven.repository_path`配置
- 确保路径使用正确的分隔符（Windows使用`\\`或`/`）
- 验证路径确实存在且可访问

### 2. 配置文件加载失败

**问题**: 无法加载配置文件

**解决方案**:
- 确保`config.yml`文件存在于项目根目录
- 检查YAML语法是否正确
- 确保文件编码为UTF-8

### 3. 依赖解析失败

**问题**: 大部分依赖显示为"缺失"

**解决方案**:
- 确保Maven仓库包含所需的依赖
- 运行`mvn dependency:resolve`下载缺失的依赖
- 检查依赖版本是否在仓库中存在

## 📝 配置示例

### Windows配置示例

```yaml
maven:
  repository_path: "C:\\Users\\username\\.m2\\repository"
  settings_file: "C:\\Users\\username\\.m2\\settings.xml"
  enable_dependency_analysis: true
```

### Linux/macOS配置示例

```yaml
maven:
  repository_path: "/home/username/.m2/repository"
  settings_file: "/home/username/.m2/settings.xml"
  enable_dependency_analysis: true
```

### 自定义仓库配置示例

```yaml
maven:
  repository_path: "/opt/maven/repository"
  settings_file: ""
  enable_dependency_analysis: true
```

## 🎯 最佳实践

1. **使用绝对路径**: 避免相对路径可能导致的问题
2. **定期验证**: 运行测试脚本确保配置正确
3. **备份配置**: 保存配置文件的备份
4. **路径格式**: 在Windows上推荐使用正斜杠`/`或双反斜杠`\\`
5. **权限检查**: 确保程序有权限访问Maven仓库目录

## 🔄 升级说明

从硬编码路径升级到配置文件的变更：

### 旧方式（已弃用）
```python
# 硬编码路径
analyzer = MavenDependencyAnalyzer("apache-maven-repository")
```

### 新方式（推荐）
```python
# 使用配置文件
analyzer = MavenDependencyAnalyzer()  # 自动读取配置
```

现有代码无需修改，仍然支持手动传入路径参数。