# Java 项目接口分析工具使用指南

分析 Java Spring Boot 项目的 API 接口，生成深度调用链树和方法映射报告。

## 环境要求

- Python 3.7+
- Java 8+ (推荐 Java 11)
- 内存 4GB+

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 自动配置 JDT 环境
python setup_jdt.py
```

或手动配置 `config.yml`：

```yaml
java:
  java_home: "D:/Program Files/Java/jdk-1.8"  # 修改为你的 JDK 路径
  jdt_lib_dir: "./lib/jdt"
```

## 快速开始

### 1. 分析项目

```bash
# 分析 Java 项目，生成接口数据
python main.py --single test_projects/sc_pcc_business

# 带详细输出
python main.py --single test_projects/sc_pcc_business --verbose
```

### 2. 生成调用链树

```bash
# JDT 解析（推荐，最精确）
python main.py --call-tree "/sheetmerge/merge" --parse-method jdt --max-depth 6

# AST 语法树解析
python main.py --call-tree "/sheetmerge/merge" --parse-method ast --max-depth 6

# 正则表达式解析（默认，最快）
python main.py --call-tree "/sheetmerge/merge" --parse-method regex --max-depth 4
```

### 3. 查看接口详情

```bash
python main.py --show-endpoint "/sheetmerge/merge"
```

## 直接使用分析器（Python API）

```python
from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer

# 初始化分析器
analyzer = JDTDeepCallChainAnalyzer(
    'test_projects/sc_pcc_business',
    show_getters_setters=False,  # 过滤 getter/setter
    show_constructors=False       # 过滤构造函数
)

# 分析调用树
call_tree = analyzer.analyze_deep_call_tree(
    'test_projects/sc_pcc_business/src/main/java/.../SheetMergeController.java',
    'merge',
    max_depth=6
)

# 生成报告
analyzer.generate_call_tree_report(call_tree, 'POST /sheetmerge/merge', 'test_output')

# 关闭分析器
analyzer.shutdown()
```

运行测试脚本：

```bash
python test_jdt_deep_analysis.py
```

## 解析方法对比

| 方法 | 精确度 | 速度 | 适用场景 |
|------|--------|------|----------|
| jdt | 极高 | 中等 | 精确分析，生产环境 |
| ast | 高 | 中等 | 一般分析 |
| regex | 中等 | 快 | 快速扫描，大型项目 |

## 输出文件

分析结果保存在 `test_output/` 或 `migration_output/` 目录：

- `deep_call_tree_*.md` - 调用树报告
- `method_mappings_*.json` - 方法映射（接口调用 → 实现类）
- `import_statements_*.txt` - import 语句
- `endpoint_analysis.json` - 接口分析数据

## 配置忽略方法

编辑 `igonre_method.txt`，每行一个方法名：

```
toString
hashCode
equals
```

## 常见问题

### JDT 初始化失败

```bash
# 重新安装 JPype
pip uninstall JPype1
pip install JPype1

# 检查 Java 版本
java -version
```

### 内存不足

修改 `config.yml`：

```yaml
java:
  jvm_args:
    - "-Xmx4g"
    - "-Xms1g"
```

### 解析超时

```yaml
performance:
  parse_timeout: 120
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `--single <path>` | 分析单个项目 |
| `--call-tree <endpoint>` | 生成调用链树 |
| `--show-endpoint <path>` | 查看接口详情 |
| `--parse-method <method>` | 解析方法: jdt/ast/regex |
| `--max-depth <n>` | 最大分析深度 (默认 4) |
| `--output <dir>` | 输出目录 |
| `--verbose` | 详细输出 |
