# 更新日志

## v2.0.0 - 新增接口查看功能

### 🎉 新增功能

#### 接口详情查看功能
- **新增参数**: `--show-endpoint ENDPOINT_PATH`
- **功能描述**: 查看特定接口的详细信息和源代码
- **支持特性**:
  - 📋 显示接口基本信息（路径、方法、控制器、复杂度等）
  - 🔗 展示完整的调用链分析（方法调用顺序和参数）
  - 📁 列出相关文件（按Service、DTO、VO等类型分组）
  - 🗄️ 显示SQL映射信息
  - 📝 自动定位并显示源代码片段（带行号高亮）

#### 智能匹配机制
- **完整路径匹配**: `/admin/category/page`
- **部分路径匹配**: `category/page`
- **关键词匹配**: `login`
- **多选支持**: 当有多个匹配结果时，提供选择列表

#### 使用示例
```bash
# 查看特定接口
python main.py --show-endpoint "/admin/category/page"

# 模糊匹配
python main.py --show-endpoint "login"

# 查看帮助
python main.py --help
```

### 🔧 技术实现

#### 新增函数
- `show_endpoint_details()`: 主要的接口查看逻辑
- `_display_endpoint_details()`: 格式化显示接口信息
- `_display_source_code()`: 智能定位和显示源代码

#### 源代码解析
- 自动定位方法定义的开始和结束位置
- 智能计算大括号平衡来确定方法边界
- 高亮显示接口定义行
- 支持多种编程语言的源文件

#### 错误处理
- 分析文件不存在时的友好提示
- 接口未找到时显示可用接口列表
- 源文件读取失败的异常处理

### 📚 文档更新

#### 新增文档
- `endpoint_viewer_usage.md`: 详细的使用指南
- `test_new_feature.py`: 功能测试脚本

#### 更新文档
- `README_SINGLE_PROJECT.md`: 添加新功能说明
- `CHANGELOG.md`: 记录功能变更

### 🎯 使用场景

1. **代码审查**: 快速了解接口实现逻辑
2. **学习研究**: 学习优秀项目的代码结构
3. **问题排查**: 定位接口相关的问题
4. **文档生成**: 为接口生成详细文档
5. **重构准备**: 识别需要重构的复杂接口

### 💡 功能亮点

- **零配置**: 基于已有的分析数据，无需额外配置
- **智能匹配**: 支持多种匹配方式，使用灵活
- **信息丰富**: 一次查看获得接口的全面信息
- **源码定位**: 自动定位并显示完整的方法代码
- **用户友好**: 清晰的格式化输出和错误提示

---

## v1.0.0 - 单项目分析模式

### 概述
在原有的新旧项目对比迁移功能基础上，新增了单项目分析模式，允许用户只分析一个项目的接口结构，无需进行新旧对比。

### 主要变更

#### 1. 新增参数支持
- 添加了 `--single PROJECT_PATH` 参数，用于指定单项目分析模式
- 保持了原有的 `--migrate --old --new` 参数组合用于迁移模式
- 两种模式互斥，必须选择其中一种

#### 2. 新增单项目分析功能
- **接口提取**: 自动识别并提取项目中的所有API接口
- **调用链分析**: 分析每个接口内部的方法调用关系
- **复杂度评估**: 基于方法调用、SQL语句等因素计算接口复杂度
- **依赖分析**: 识别Service、DAO等依赖关系
- **SQL映射分析**: 提取和分析MyBatis等ORM映射

#### 3. 增强的输出功能
单项目模式生成以下文件：
- `endpoints.json`: 所有接口的详细信息
- `endpoint_analysis.json`: 完整的分析结果数据
- `analysis_report.md`: 人类可读的分析报告

#### 4. 改进的用户体验
- 详细的进度提示
- 复杂度排序显示
- 统计信息概览
- 支持详细模式（--verbose）

### 使用方法

#### 单项目分析
```bash
# 基本分析
python main.py --single /path/to/project

# 详细分析
python main.py --single /path/to/project --verbose

# 自定义输出目录
python main.py --single /path/to/project --output ./my_analysis
```

#### 迁移分析（原功能保持不变）
```bash
# 基本迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new

# 详细迁移分析
python main.py --migrate --old /path/to/old --new /path/to/new --verbose
```

### 技术实现

#### 1. 代码结构调整
- 修改了 `Config` 类，添加单项目模式相关字段
- 在 `MigrationTool` 类中添加了 `run_single_project_analysis()` 方法
- 新增了复杂度计算和单项目结果保存功能

#### 2. 接口提取器优化
- 修复了Spring Boot接口提取的正则表达式问题
- 改进了路径解析逻辑
- 增强了对不同框架的支持

#### 3. 分析功能增强
- 新增接口复杂度评分算法
- 改进了调用链分析的准确性
- 增加了统计信息生成

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

### 复杂度评估算法

复杂度得分基于以下因素：
- 方法调用数量：每个调用 +1 分
- SQL语句数量：每个语句 +2 分  
- SQL映射文件数量：每个文件 +3 分
- 相关文件数量：每个文件 +1 分

### 输出示例

#### 控制台输出
```
🚀 开始分析项目接口...
📋 提取项目接口...
✅ 提取完成: 共找到 3 个接口
🔍 分析接口调用链和依赖...
  分析接口 1/3: NewUserController.getAllUsers
  分析接口 2/3: NewUserController.getAllUsers  
  分析接口 3/3: NewUserController.createUser

=== 单项目接口分析结果 ===
总接口数: 3
复杂接口数: 0
简单接口数: 3
💾 保存分析结果...
🎉 单项目分析完成! 结果已保存到: ./migration_output
```

#### 分析报告示例
```markdown
# 项目接口分析报告

## 统计概览
- 总接口数: 3
- 复杂接口数: 0
- 简单接口数: 3
- 使用框架: spring

## 接口详情
### 1. NewUserController.getAllUsers
- **路径**: GET /api/users/getAll
- **文件**: test_projects\new_project\NewUserController.java:9
- **复杂度**: 2
- **框架**: spring
- **方法调用**: 2 个
```

### 兼容性

- 完全向后兼容原有的迁移分析功能
- 新增功能不影响现有工作流程
- 支持所有原有的参数和选项

### 文件变更

#### 新增文件
- `main_single.py`: 包含单项目功能的独立版本
- `README_SINGLE_PROJECT.md`: 单项目功能详细文档
- `usage_examples.py`: 使用示例脚本
- `CHANGELOG.md`: 本更新日志

#### 修改文件
- `main.py`: 集成单项目分析功能
- `endpoint_extractor.py`: 修复Spring接口提取问题

### 测试验证

已通过以下测试：
- ✅ 单项目分析基本功能
- ✅ 详细模式输出
- ✅ 迁移模式兼容性
- ✅ 参数验证和错误处理
- ✅ 输出文件生成

### 后续计划

1. 支持更多编程语言和框架
2. 增加接口性能分析功能
3. 提供Web界面
4. 集成CI/CD流程
5. 添加接口变更检测功能