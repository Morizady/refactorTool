# Java代码解析方法分析

本项目使用了两种主要的Java代码解析方法：**javalang AST语法解析** 和 **正则表达式解析**。以下是详细的功能分类和使用场景分析。

## 🔍 使用javalang AST语法解析的功能

### 1. CallChainAnalyzer (call_chain_analyzer.py)
**文件**: `call_chain_analyzer.py`
**使用场景**: 浅层调用链分析

```python
import javalang  # 需要安装: pip install javalang

# 使用javalang解析Java代码
tree = javalang.parse.parse(content)

# 查找目标方法
for path, node in tree.filter(javalang.tree.MethodDeclaration):
    if node.name == endpoint.handler:
        target_method = node

# 提取方法调用
for path, node in method_node.filter(javalang.tree.MethodInvocation):
    call_info = {
        "method": node.member,
        "object": self._get_qualifier_name(node.qualifier),
        "arguments": len(node.arguments) if node.arguments else 0,
        "position": node.position.line if node.position else 0
    }
```

**优势**:
- 精确的语法分析，能正确识别Java语法结构
- 可以获取准确的AST节点信息（方法声明、方法调用等）
- 提供准确的行号和位置信息
- 能处理复杂的Java语法结构

**局限性**:
- 需要完整的、语法正确的Java代码
- 解析速度相对较慢
- 对于语法错误的代码会解析失败

## 🔧 使用正则表达式解析的功能

### 1. EndpointExtractor (endpoint_extractor.py)
**文件**: `endpoint_extractor.py`
**使用场景**: Spring Boot接口提取

```python
import re

# 提取控制器类名
class_match = re.search(self.patterns["spring"]["controller"], content, re.DOTALL)

# 查找@RequestMapping注解获取基础路径
base_matches = re.finditer(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', content)

# 查找方法映射注解
mapping_match = re.search(self.patterns["spring"]["mapping"], line)

# 查找方法定义
method_match = re.search(self.patterns["spring"]["method"], current_line)
```

### 2. DeepCallChainAnalyzer (main.py)
**文件**: `main.py`
**使用场景**: 深度调用链分析

```python
import re

# 1. 枚举常量调用 EnumClass.CONSTANT.method()
enum_pattern = r'([A-Z]\w*)\.([A-Z_]+)\.(\w+)\s*\(([^)]*)\)'
enum_matches = re.finditer(enum_pattern, line_clean)

# 2. 链式调用 object.method1().method2()
chain_pattern = r'(\w+)(?:\.(\w+)\s*\([^)]*\))+(?:\.(\w+)\s*\([^)]*\))*'
chain_matches = re.finditer(chain_pattern, line_clean)

# 3. 静态方法调用 Class.method()
static_pattern = r'\b([A-Z][A-Z_]*[A-Z]|[A-Z][a-z]*[A-Z]\w*)\.(\w+)\s*\(([^)]*)\)'
static_matches = re.finditer(static_pattern, line_clean)

# 4. 实例方法调用 object.method()
simple_instance_pattern = r'(\w+)\.(\w+)\s*\('
simple_matches = re.finditer(simple_instance_pattern, line_clean)

# 5. 构造函数调用 new Class()
constructor_pattern = r'new\s+([A-Z]\w*)\s*\(([^)]*)\)'
constructor_matches = re.finditer(constructor_pattern, line_clean)
```

### 3. SQLMapperAnalyzer (sql_mapper_analyzer.py)
**文件**: `sql_mapper_analyzer.py`
**使用场景**: MyBatis SQL映射分析

```python
import re

# XML解析失败时的正则表达式备用方案
def _parse_mapper_with_regex(self, content: str, mapper_file: Path, project_root: Path) -> Dict:
    # SQL语句模式匹配
    sql_patterns = [
        (r'<select[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</select>', 'SELECT'),
        (r'<insert[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</insert>', 'INSERT'),
        (r'<update[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</update>', 'UPDATE'),
        (r'<delete[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</delete>', 'DELETE')
    ]
    
    for pattern, sql_type in sql_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)

# 清理SQL文本
sql = re.sub(r'<[^>]+>', ' ', sql)  # 移除XML标签
sql = re.sub(r'\s+', ' ', sql)     # 标准化空格

# 提取表名
matches = re.findall(pattern, sql_lower, re.IGNORECASE)
```

### 4. EquivalenceMatcher (equivalence_matcher.py)
**文件**: `equivalence_matcher.py`
**使用场景**: 接口等价性匹配

```python
import re

# 规范化路径
path = re.sub(r'/api/v\d+/', '/api/', path)           # 移除API版本前缀
path = re.sub(r'/\{[^}]+\}', '/{param}', path)        # 路径参数归一化
path = re.sub(r'/:[^/]+', '/{param}', path)           # 路径参数归一化
path = re.sub(r'/<[^>]+>', '/{param}', path)          # 路径参数归一化

# 分割驼峰命名
words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', text)
```

### 5. 类继承关系分析 (main.py)
**文件**: `main.py`
**使用场景**: 构建类继承关系和接口实现映射

```python
import re

# 查找类定义和接口实现
class_pattern = r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
interface_pattern = r'(?:public\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?'

class_matches = re.finditer(class_pattern, content)
interface_matches = re.finditer(interface_pattern, content)
```

## 📊 对比分析

### javalang AST解析
**优势**:
- ✅ 语法精确性高，能正确理解Java语法结构
- ✅ 提供完整的AST节点信息
- ✅ 能处理复杂的嵌套结构
- ✅ 获取准确的位置信息

**劣势**:
- ❌ 需要完整、语法正确的代码
- ❌ 解析速度较慢
- ❌ 对语法错误敏感
- ❌ 需要额外依赖包

**适用场景**:
- 需要精确语法分析的场景
- 浅层调用链分析
- 方法声明和调用的准确提取

### 正则表达式解析
**优势**:
- ✅ 解析速度快
- ✅ 容错性强，能处理不完整的代码
- ✅ 无需额外依赖
- ✅ 灵活性高，易于定制

**劣势**:
- ❌ 可能出现误匹配
- ❌ 难以处理复杂的嵌套结构
- ❌ 维护复杂的正则表达式困难
- ❌ 无法理解语法上下文

**适用场景**:
- 快速模式匹配
- 注解提取
- 简单的代码结构识别
- 容错性要求高的场景

## 🎯 混合使用策略

本项目采用了**混合解析策略**，根据不同的使用场景选择合适的解析方法：

### 1. 浅层分析 → javalang AST
- **CallChainAnalyzer**: 使用javalang进行精确的方法调用分析
- 适合需要准确语法理解的场景

### 2. 深层分析 → 正则表达式
- **DeepCallChainAnalyzer**: 使用正则表达式进行快速模式匹配
- 适合大规模代码扫描和容错性要求高的场景

### 3. 特定功能 → 正则表达式
- **接口提取**: Spring注解模式匹配
- **SQL分析**: MyBatis XML解析的备用方案
- **路径规范化**: 接口等价性匹配

## 🚀 性能对比

| 解析方法 | 速度 | 准确性 | 容错性 | 维护性 |
|---------|------|--------|--------|--------|
| javalang AST | 慢 | 高 | 低 | 高 |
| 正则表达式 | 快 | 中等 | 高 | 中等 |

## 💡 建议和最佳实践

### 1. 选择原则
- **精确性优先**: 使用javalang AST
- **性能优先**: 使用正则表达式
- **容错性优先**: 使用正则表达式

### 2. 混合策略
- 先用正则表达式快速筛选
- 再用javalang AST精确分析
- 提供正则表达式作为备用方案

### 3. 优化建议
- 缓存AST解析结果
- 优化正则表达式性能
- 提供配置选项让用户选择解析方法

## 📝 总结

本项目通过合理的混合解析策略，既保证了分析的准确性，又兼顾了性能和容错性。javalang AST用于需要精确语法分析的核心功能，正则表达式用于快速模式匹配和容错性要求高的场景，形成了互补的解析体系。