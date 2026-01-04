# JDT Java代码解析器配置指南

本指南将帮助您配置基于Eclipse JDT和JPype的精确Java代码解析环境。

## 概述

本项目现在支持三种Java代码解析方法：
- **JDT (推荐)**: 使用Eclipse JDT提供最精确的Java代码分析
- **AST**: 使用javalang库进行语法树解析
- **Regex**: 使用正则表达式进行基础解析

## 系统要求

### 必需组件
- Python 3.7+
- Java 8+ (推荐Java 11或更高版本)
- 足够的内存 (推荐4GB+)

### 支持的操作系统
- Windows 10/11
- Linux (Ubuntu 18.04+, CentOS 7+)
- macOS 10.14+

## 快速开始

### 1. 自动安装 (推荐)

运行自动安装脚本：

```bash
python setup_jdt.py
```

脚本将自动：
- 检查Java环境
- 安装JPype依赖
- 下载Eclipse JDT库
- 配置config.yml文件
- 测试环境设置

### 2. 手动安装

如果自动安装失败，请按以下步骤手动配置：

#### 步骤1: 安装Java

**Windows:**
1. 下载OpenJDK或Oracle JDK
2. 安装到默认位置 (如 `C:\Program Files\Java\jdk-11.0.16`)
3. 设置环境变量 `JAVA_HOME`

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-11-jdk

# CentOS/RHEL
sudo yum install java-11-openjdk-devel

# 设置JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
```

**macOS:**
```bash
# 使用Homebrew
brew install openjdk@11

# 设置JAVA_HOME
export JAVA_HOME=/usr/local/opt/openjdk@11
```

#### 步骤2: 安装Python依赖

```bash
pip install JPype1 pyyaml
```
#### 步骤3: 下载JDT库

创建库目录并下载JDT Core：

```bash
mkdir -p lib/jdt
cd lib/jdt

# 下载JDT Core JAR (版本3.32.0)
curl -O https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/3.32.0/org.eclipse.jdt.core-3.32.0.jar
mv org.eclipse.jdt.core-3.32.0.jar org.eclipse.jdt.core.jar

cd ../..
```

#### 步骤4: 配置config.yml

编辑 `config.yml` 文件，设置正确的Java路径：

```yaml
java:
  # 根据您的系统修改此路径
  java_home: "C:/Program Files/Java/jdk-11.0.16"  # Windows
  # java_home: "/usr/lib/jvm/java-11-openjdk"     # Linux
  # java_home: "/usr/local/opt/openjdk@11"        # macOS
  
  jvm_args:
    - "-Xmx2g"
    - "-Xms512m"
    - "-Dfile.encoding=UTF-8"
  
  jdt_lib_dir: "./lib/jdt"
  auto_download_jdt: true

parsing:
  method: "jdt"  # 使用JDT解析
  source_encoding: "UTF-8"
  java_version: "11"
```

## 使用方法

### 基本命令

1. **分析单个项目**：
```bash
python main.py --single /path/to/java/project --parse-method jdt
```

2. **生成调用链树**：
```bash
python main.py --call-tree /api/user/login --parse-method jdt --max-depth 5
```

3. **查看接口详情**：
```bash
python main.py --show-endpoint /api/user/list --parse-method jdt
```

### 高级选项

- `--max-depth N`: 设置调用链分析的最大深度 (默认4)
- `--verbose`: 显示详细分析信息
- `--output DIR`: 指定输出目录

### 性能优化

在 `config.yml` 中调整性能参数：

```yaml
java:
  jvm_args:
    - "-Xmx4g"      # 增加堆内存
    - "-Xms1g"      # 增加初始内存
    - "-XX:+UseG1GC"  # 使用G1垃圾收集器

performance:
  max_threads: 8        # 增加并发线程
  max_file_size: 20     # 增加文件大小限制
  parse_timeout: 60     # 增加解析超时时间
```

## 故障排除

### 常见问题

#### 1. "未找到JAVA_HOME"

**解决方案**：
- 确保已安装Java
- 设置JAVA_HOME环境变量
- 在config.yml中手动指定java_home路径

#### 2. "JPype初始化失败"

**解决方案**：
```bash
# 重新安装JPype
pip uninstall JPype1
pip install JPype1

# 检查Java版本兼容性
java -version
```

#### 3. "JDT依赖下载失败"

**解决方案**：
- 检查网络连接
- 手动下载JDT JAR文件
- 确保lib/jdt目录存在且可写

#### 4. "内存不足"

**解决方案**：
在config.yml中增加JVM内存：
```yaml
java:
  jvm_args:
    - "-Xmx4g"  # 增加到4GB
    - "-Xms1g"
```

#### 5. "解析超时"

**解决方案**：
```yaml
performance:
  parse_timeout: 120  # 增加到120秒
  max_file_size: 50   # 增加文件大小限制
```

### 调试模式

启用详细日志：

```yaml
logging:
  level: "DEBUG"
  console: true
  file: "./logs/jdt_debug.log"
```

然后运行：
```bash
python main.py --single /path/to/project --parse-method jdt --verbose
```

### 验证安装

运行测试脚本验证环境：

```bash
python -c "
from jdt_parser import JDTParser
parser = JDTParser()
if parser.initialize_jdt():
    print('✅ JDT环境正常')
    parser.shutdown()
else:
    print('❌ JDT环境异常')
"
```

## 与javalang的对比

| 特性 | JDT | javalang |
|------|-----|----------|
| 解析精度 | 极高 | 中等 |
| 性能 | 高 | 中等 |
| 内存使用 | 较高 | 较低 |
| Java版本支持 | 全面 | 有限 |
| 错误处理 | 优秀 | 一般 |
| 依赖复杂度 | 较高 | 低 |

## 最佳实践

1. **内存管理**：为大型项目分配足够的JVM内存
2. **并发控制**：根据CPU核心数调整线程数
3. **缓存使用**：启用解析结果缓存以提高重复分析性能
4. **错误处理**：使用verbose模式诊断解析问题
5. **版本兼容**：确保Java版本与目标项目兼容

## 支持与反馈

如果遇到问题：
1. 检查本文档的故障排除部分
2. 查看日志文件获取详细错误信息
3. 确认Java和Python环境配置正确
4. 尝试使用较小的测试项目验证环境

---

**注意**: JDT解析器提供了比javalang更精确的Java代码分析能力，但需要更多的系统资源和配置。对于简单的分析任务，您仍然可以使用 `--parse-method ast` 或 `--parse-method regex` 选项。