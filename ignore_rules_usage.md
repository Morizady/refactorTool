# 忽略规则使用说明

## 📋 概述

JDT调用链分析器支持通过配置文件来忽略特定的方法调用，避免在调用树中显示不重要的方法，让分析结果更加清晰。

## 🔧 配置文件

忽略规则配置在 `igonre_method.txt` 文件中（注意文件名的拼写）。

### 文件格式

- 每行一个方法名或类名.方法名
- 支持注释（以 `#` 开头的行）
- 空行会被忽略

### 支持的格式

1. **方法名匹配**
   ```
   toString
   equals
   hashCode
   ```

2. **类名.方法名匹配**
   ```
   Anti.execute
   StringUtils.isEmpty
   Collections.sort
   ```

3. **完整类名.方法名匹配**
   ```
   com.unicom.microserv.cs.pcc.config.util.Anti.execute
   java.util.Collections.sort
   ```

## 📝 当前配置的忽略规则

当前 `igonre_method.txt` 文件中配置的忽略规则包括：

### 常用工具方法
- `toString`, `equals`, `hashCode`
- `isEmpty`, `isNotEmpty`, `isBlank`, `isNull`
- `get`, `put`, `size`, `length`
- `split`, `substring`, `contains`

### 日志和响应方法
- `setRSP_CODE`, `setRSP_DESC`, `setRSP`
- `setDATA`, `getDATA`
- `error`, `info`

### 特定类的方法
- `Anti.execute` - 防XSS工具类的执行方法

### 集合和字符串操作
- `stream`, `map`, `orElse`, `ofNullable`
- `asList`, `append`, `encode`

## 🚀 使用效果

### 修复前
```
├── MaterialConfigController.getList()
│   ├── Anti.execute() [具体类]
│   │   ├── object.getClass()
│   │   ├── ClassUtils.isPrimitiveOrWrapper()
│   │   └── ...
```

### 修复后
```
├── MaterialConfigController.getList()
│   ├── SqlUtil.checkInject()
│   ├── MaterialConfig.<init>()
│   ├── ServiceResult.<init>()
│   └── this.baseService.baseListQuery()
```

## 🔍 匹配规则

忽略检查支持以下匹配方式：

1. **精确方法名匹配**
   - 如果忽略列表中有 `execute`，则所有名为 `execute` 的方法都会被忽略

2. **类名.方法名匹配**
   - 如果忽略列表中有 `Anti.execute`，则：
     - `Anti.execute()` 会被忽略
     - `com.example.Anti.execute()` 也会被忽略（简单类名匹配）

3. **完整类名.方法名匹配**
   - 支持完整包名的匹配

## ⚙️ 高级配置

### 构造函数控制
```python
# 在初始化分析器时可以控制是否显示构造函数
analyzer = JDTDeepCallChainAnalyzer(
    project_root, 
    show_constructors=False  # 不显示构造函数
)
```

### Getter/Setter控制
```python
# 控制是否显示简单的getter/setter方法
analyzer = JDTDeepCallChainAnalyzer(
    project_root, 
    show_getters_setters=False  # 不显示getter/setter
)
```

## 📋 添加新的忽略规则

### 1. 编辑配置文件
```bash
# 编辑忽略规则文件
notepad igonre_method.txt
```

### 2. 添加规则
```
# 添加新的忽略规则
MyUtil.helper
AnotherClass.process
commonMethod
```

### 3. 验证规则
运行分析后检查调用树中是否还包含被忽略的方法。

## 🧪 测试忽略规则

可以使用以下代码测试忽略规则是否生效：

```python
from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer

# 初始化分析器
analyzer = JDTDeepCallChainAnalyzer("path/to/project")

# 检查特定方法是否被忽略
should_ignore = analyzer._should_ignore_method("execute", "Anti")
print(f"Anti.execute 是否被忽略: {should_ignore}")

# 查看所有忽略规则
print(f"忽略规则数量: {len(analyzer.ignore_methods)}")
for rule in sorted(analyzer.ignore_methods):
    print(f"  - {rule}")
```

## 🔧 故障排除

### 1. 忽略规则不生效

**可能原因**:
- 文件名拼写错误（应该是 `igonre_method.txt`）
- 规则格式不正确
- 类名匹配不准确

**解决方案**:
- 检查文件名和路径
- 确认规则格式正确
- 使用调试模式查看具体的类名和方法名

### 2. 过度忽略

**问题**: 忽略了不应该忽略的方法

**解决方案**:
- 使用更具体的类名.方法名格式
- 避免使用过于通用的方法名

### 3. 调试忽略规则

启用调试日志查看详细信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 这样可以看到忽略检查的详细过程
analyzer = JDTDeepCallChainAnalyzer("path/to/project")
```

## 📊 最佳实践

1. **优先使用类名.方法名格式**，避免误伤其他类的同名方法
2. **定期检查忽略规则**，确保不会过度过滤重要信息
3. **使用注释**标明忽略规则的用途
4. **测试验证**每次修改忽略规则后都要验证效果
5. **备份配置**保存忽略规则文件的备份

## 🎯 示例配置

```
# 通用工具方法
toString
equals
hashCode
isEmpty
isNotEmpty

# 日志相关
error
info
debug

# 特定工具类
Anti.execute
StringUtils.isEmpty
CollectionUtils.isNotEmpty

# 响应对象方法
setRSP_CODE
setRSP_DESC
getDATA
setDATA

# 注释：这些是常用的不重要的方法调用
```