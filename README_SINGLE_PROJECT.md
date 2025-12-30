# 单项目接口分析功能

## 概述

新增的单项目分析功能允许你只分析一个项目的接口结构，而不需要进行新旧项目的对比。这对于以下场景特别有用：

- 了解现有项目的接口结构
- 评估项目的复杂度
- 生成接口文档
- 代码审查和重构准备

## 使用方法

### 1. 单项目分析

```bash
# 分析单个项目
python main.py --single /path/to/your/project

# 显示详细信息
python main.py --single /path/to/your/project --verbose

# 自定义输出目录
python main.py --single /path/to/your/project --output ./my_analysis
```

### 2. 接口详情查看 (新功能)

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

### 3. 迁移分析（原功能）

```bash
# 基本迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new

# 详细迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new --verbose
```

### 参数说明

#### 必需参数
- `--single PROJECT_PATH`: 指定要分析的项目路径

#### 可选参数
- `--output DIR`: 输出目录（默认：./migration_output）
- `--verbose, -v`: 显示详细分析信息
- `--model MODEL`: AI模型名称（默认：gpt-3.5-turbo）
- `--api-key KEY`: OpenAI API密钥（单项目模式通常不需要）

### 示例

```bash
# 分析测试项目
python main_single.py --single test_projects/new_project --verbose

# 分析实际项目
python main_single.py --single /home/user/my-spring-project --output ./analysis_results
```

## 输出结果

单项目分析会生成以下文件：

### 1. endpoints.json
包含所有提取的接口信息：
```json
[
  {
    "name": "NewUserController.getAllUsers",
    "path": "/api/users/getAll",
    "method": "GET",
    "controller": "NewUserController",
    "handler": "getAllUsers",
    "file_path": "test_projects\\new_project\\NewUserController.java",
    "line_number": 9,
    "framework": "spring"
  }
]
```

### 2. endpoint_analysis.json
包含详细的分析结果：
```json
[
  {
    "endpoint": { /* 接口信息 */ },
    "call_chain": {
      "method_calls": [
        {"object": "Response", "method": "success"},
        {"object": "userService", "method": "getAllUsers"}
      ],
      "sql_statements": [],
      "files": []
    },
    "sql_mappings": [],
    "complexity_score": 2
  }
]
```

### 3. analysis_report.md
人类可读的分析报告，包含：
- 统计概览（总接口数、复杂接口数等）
- 接口详情列表
- 复杂度评估

## 分析功能

### 接口提取
- 自动识别Spring Boot、Flask、Django、Express等框架
- 提取接口路径、HTTP方法、处理函数等信息
- 支持多种编程语言（Java、Python、Go、JavaScript/TypeScript）

### 调用链分析
- 分析接口内部的方法调用
- 识别Service、DAO等依赖关系
- 提取SQL语句（如果存在）

### 复杂度评估
复杂度得分基于以下因素：
- 方法调用数量（每个调用 +1 分）
- SQL语句数量（每个语句 +2 分）
- SQL映射文件数量（每个文件 +3 分）
- 相关文件数量（每个文件 +1 分）

### 支持的框架

#### Java
- Spring Boot (RestController, RequestMapping等注解)
- Spring MVC

#### Python
- Flask (@app.route装饰器)
- Django (URL配置)

#### Go
- Gin框架

#### JavaScript/TypeScript
- Express.js
- 基本的路由定义

## 与迁移模式的区别

| 功能 | 单项目模式 | 迁移模式 |
|------|------------|----------|
| 项目数量 | 1个 | 2个（新旧对比） |
| 接口匹配 | 无 | 有 |
| AI代码生成 | 无 | 有（可选） |
| 复杂度分析 | 有 | 有 |
| 调用链分析 | 有 | 有 |
| 输出报告 | 简化版 | 完整版 |

## 使用场景

### 1. 项目评估
```bash
# 评估项目复杂度，为重构做准备
python main_single.py --single /path/to/legacy/project --verbose
```

### 2. 接口文档生成
```bash
# 生成接口清单和分析报告
python main_single.py --single /path/to/api/project --output ./api_docs
```

### 3. 代码审查
```bash
# 分析接口结构，识别复杂的接口
python main_single.py --single /path/to/review/project --verbose
```

### 4. 技术债务评估
```bash
# 识别高复杂度接口，优先重构
python main_single.py --single /path/to/project --output ./tech_debt_analysis
```

## 注意事项

1. **文件编码**: 确保项目文件使用UTF-8编码
2. **框架支持**: 目前支持主流框架，如需支持其他框架可扩展
3. **大型项目**: 对于非常大的项目，分析可能需要一些时间
4. **路径格式**: 使用正斜杠或反斜杠都可以，工具会自动处理

## 故障排除

### 常见问题

1. **没有找到接口**
   - 检查项目路径是否正确
   - 确认项目使用支持的框架
   - 查看控制器文件是否包含正确的注解

2. **路径解析错误**
   - 检查注解格式是否标准
   - 确认字符串引号使用正确

3. **编码问题**
   - 确保文件使用UTF-8编码
   - 检查文件是否包含特殊字符

### 调试模式

使用 `--verbose` 参数可以看到详细的分析过程：
```bash
python main_single.py --single your_project --verbose
```

这会显示：
- 每个接口的详细信息
- 调用链分析结果
- 复杂度计算过程