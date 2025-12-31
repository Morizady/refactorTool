# Java项目接口分析工具

专注于Java Spring Boot项目的接口分析工具，提供深度的调用链分析和接口结构解析。

## 🚀 主要功能

### 单项目分析
分析Java Spring Boot项目的接口结构，生成详细的分析报告。

```bash
# 分析单个Java项目
python main.py --single /path/to/your/java/project

# 显示详细信息
python main.py --single /path/to/your/java/project --verbose

# 自定义输出目录
python main.py --single /path/to/your/java/project --output ./my_analysis
```

### 接口详情查看
查看特定接口的详细信息和源代码。

```bash
# 查看特定接口的详细信息
python main.py --show-endpoint "/admin/category/page"

# 支持模糊匹配
python main.py --show-endpoint "login"

# 支持部分路径匹配
python main.py --show-endpoint "category/page"
```

**接口查看功能特点**：
- 📋 显示接口基本信息（路径、方法、控制器等）
- 🔗 展示完整的调用链分析
- 📁 列出相关文件（Service、DTO、VO等）
- 🗄️ 显示SQL映射信息
- 📝 自动定位并显示源代码片段

### 深度调用链分析
生成接口的深度调用链树，分析方法调用关系。

```bash
# 生成调用链树
python main.py --call-tree "/admin/category/page"
```

### 迁移分析
对比新旧Java项目的接口差异，辅助系统迁移。

```bash
# 基本迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new

# 详细迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new --verbose
```

## 📋 输出文件

分析完成后，工具会在输出目录生成以下文件：

- `endpoints.json` - 所有接口的详细信息
- `endpoint_analysis.json` - 完整的分析结果数据
- `analysis_report.md` - 人类可读的分析报告
- `call_tree_*.md` - 接口调用链树（使用--call-tree时生成）

## 🛠️ 快速开始

### 分析示例项目

```bash
# 分析测试项目
python main.py --single test_projects/sc_pcc_business --verbose

# 分析实际项目
python main.py --single /home/user/my-spring-project --output ./analysis_results
```

## 🔧 安装依赖

```bash
pip install javalang
```

## 📊 功能特性

### 接口提取
- 自动识别Spring Boot框架
- 提取接口路径、HTTP方法、处理函数等信息
- 支持Java项目分析

### 调用链分析
- 深度分析方法调用关系
- 识别Service、DAO等依赖
- 提取SQL映射信息
- 计算接口复杂度

### 支持的Java框架

#### Spring Boot
- Spring MVC
- Spring WebFlux
- REST Controller

## 💡 使用场景

### 代码审查
```bash
# 评估项目复杂度，为重构做准备
python main.py --single /path/to/legacy/project --verbose
```

### 文档生成
```bash
# 生成接口清单和分析报告
python main.py --single /path/to/api/project --output ./api_docs
```

### 代码重构
```bash
# 分析接口结构，识别复杂的接口
python main.py --single /path/to/review/project --verbose
```

### 技术债务分析
```bash
# 识别高复杂度接口，优先重构
python main.py --single /path/to/project --output ./tech_debt_analysis
```

## 📈 分析报告示例

工具会生成包含以下信息的详细报告：

- 📊 项目统计信息（接口数量、复杂度分布）
- 🔗 接口列表（按复杂度排序）
- 📁 文件结构分析
- 🗄️ SQL映射统计
- ⚡ 性能建议

## 🎯 高级功能

### 详细模式

使用 `--verbose` 参数可以看到详细的分析过程：
```bash
python main.py --single your_project --verbose
```

### 调用链树生成

生成特定接口的深度调用链分析：
```bash
# 先分析项目生成数据
python main.py --single /path/to/project --output ./output

# 生成调用链树
python main.py --call-tree /api/endpoint/path --output ./output
```

## 🔍 示例输出

### 接口列表示例
```
📊 接口复杂度统计:
- 简单接口 (1-5个调用): 12个
- 中等接口 (6-15个调用): 8个  
- 复杂接口 (16+个调用): 3个

🔗 复杂度最高的接口:
1. POST /admin/employee/login (复杂度: 23)
2. GET /admin/category/page (复杂度: 18)
3. POST /admin/dish/save (复杂度: 15)
```

### 调用链树示例
```
📁 merge() - 主方法
  ├── ServiceResult.ServiceResult() [构造] - 0个参数 (行:42)
  ├── MapUtils.getString() [静态] - 2个参数 (行:44)
  ├── StringUtils.isNullOrBlank() [静态] - 1个参数 (行:45)
  ├── result.setRSP() [链式] - 1个参数 (行:46)
  ├── sheetMergeService.merge() - 3个参数 (行:60)
```

## 📝 注意事项

- 目前只支持Java Spring Boot项目
- 需要安装javalang依赖包
- 建议在项目根目录运行分析
- 大型项目分析可能需要较长时间

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个工具！