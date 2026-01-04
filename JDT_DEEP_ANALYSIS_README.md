# JDT深度调用链分析功能

## 功能概述

本项目现已集成基于Eclipse JDT的深度调用链分析功能，能够：

1. **精确解析Java代码**：使用Eclipse JDT提供IDE级别的代码分析精度
2. **生成深度调用树**：递归分析方法调用，支持6层以上的深度分析
3. **方法映射记录**：记录接口调用到具体实现的映射关系
4. **多态和继承分析**：正确处理Java的多态、继承特性
5. **Import语句生成**：自动生成所需的import语句

## 核心特性

### 1. 深度调用树分析

```bash
# 使用JDT分析深度调用树
python main.py --call-tree /sheetmerge/merge --parse-method jdt --max-depth 6
```

**输出文件**：
- `deep_call_tree_merge_jdt.md` - 详细的调用树报告
- `method_mappings_merge_jdt.json` - 方法映射JSON数据
- `import_statements_merge_jdt.txt` - 所需的import语句

### 2. 方法映射功能

对于调用 `sheetMergeService.merge(sheetId, mergedSheetId, reason)`，系统会记录：

```json
{
  "interface_call": "sheetMergeService.merge()",
  "implementation_call": "SheetMergeServiceImpl.merge()",
  "import_statement": "import com.unicom.microserv.cs.pcc.core.sheetmerge.service.SheetMergeServiceImpl;",
  "call_type": "service_impl",
  "line_number": 45,
  "file_path": "SheetMergeController.java"
}
```

### 3. 多态和继承处理

系统能够正确识别：
- **接口实现**：`Service` -> `ServiceImpl`
- **类继承**：父类方法调用
- **多态调用**：运行时类型确定
- **Spring注入**：`@Autowired`字段类型解析

## 使用方法

### 快速开始

1. **环境配置**：
```bash
python setup_jdt.py
python test_jdt_environment.py
```

2. **项目分析**：
```bash
python main.py --single /path/to/java/project --parse-method jdt
```

3. **深度调用树分析**：
```bash
python main.py --call-tree /api/endpoint --parse-method jdt --max-depth 6
```

### 详细配置

编辑 `config.yml`：

```yaml
java:
  java_home: "C:/Program Files/Java/jdk-11.0.16"
  jvm_args:
    - "-Xmx4g"  # 大项目需要更多内存
    - "-Xms1g"

parsing:
  method: "jdt"
  java_version: "11"

analysis:
  max_call_depth: 6
  analyze_interfaces: true
  analyze_inheritance: true
```

## 输出文件说明

### 1. 深度调用树报告 (*.md)

包含：
- 接口基本信息
- 统计数据（总调用数、最大深度、涉及类数）
- 可视化调用树
- 方法映射详情
- 多态和继承分析
- Import语句汇总
- 性能分析建议

### 2. 方法映射文件 (*.json)

结构化数据，包含每个方法调用的：
- 接口调用形式
- 实现调用形式
- Import语句
- 调用类型
- 位置信息

### 3. Import语句文件 (*.txt)

去重后的import语句列表，可直接复制到Java文件中。

## 实际应用示例

### 分析SheetMerge接口

```bash
# 1. 分析项目
python main.py --single test_projects/sc_pcc_business --parse-method jdt

# 2. 生成深度调用树
python main.py --call-tree /sheetmerge/merge --parse-method jdt --max-depth 6
```

**生成的方法映射示例**：

```
sheetMergeService.merge() -> SheetMergeServiceImpl.merge()
import com.unicom.microserv.cs.pcc.core.sheetmerge.service.SheetMergeServiceImpl;

MapUtils.getString() -> MapUtils.getString()
import org.apache.commons.collections.MapUtils;

StringUtils.isNullOrBlank() -> StringUtils.isNullOrBlank()
import com.hollycrm.hollybeacons.system.util.StringUtils;
```

### 处理复杂继承关系

对于继承和多态场景：

```java
// 接口
public interface UserService {
    User findById(Long id);
}

// 实现类
public class UserServiceImpl implements UserService {
    public User findById(Long id) { ... }
}

// 控制器中的调用
@Autowired
private UserService userService;

public void someMethod() {
    userService.findById(1L);  // 系统会映射到 UserServiceImpl.findById()
}
```

## 性能优化

### 大型项目配置

```yaml
java:
  jvm_args:
    - "-Xmx8g"      # 8GB堆内存
    - "-Xms2g"      # 2GB初始内存
    - "-XX:+UseG1GC"  # G1垃圾收集器

performance:
  max_threads: 8        # 8个并发线程
  max_file_size: 50     # 50MB文件大小限制
  parse_timeout: 120    # 120秒超时
```

### 分析策略

1. **分模块分析**：对大型项目按模块分别分析
2. **深度控制**：根据需要调整max_depth参数
3. **缓存利用**：启用缓存避免重复解析
4. **内存监控**：监控JVM内存使用情况

## 故障排除

### 常见问题

1. **内存不足**：
   - 增加JVM堆内存：`-Xmx4g`
   - 减少并发线程数
   - 降低分析深度

2. **解析失败**：
   - 检查Java版本兼容性
   - 确认项目编译无误
   - 查看详细错误日志

3. **映射不准确**：
   - 检查Spring注解配置
   - 验证包导入语句
   - 确认类继承关系

### 调试模式

```yaml
logging:
  level: "DEBUG"
  console: true
  file: "./logs/jdt_debug.log"
```

```bash
python main.py --call-tree /api/endpoint --parse-method jdt --verbose
```

## 测试和验证

### 运行测试

```bash
# 环境测试
python test_jdt_environment.py

# 功能测试
python test_jdt_deep_analysis.py

# 使用示例
python example_jdt_usage.py
```

### 验证结果

1. 检查生成的调用树是否完整
2. 验证方法映射的准确性
3. 确认import语句的正确性
4. 测试多态和继承处理

## 最佳实践

1. **项目准备**：确保项目能够正常编译
2. **内存配置**：根据项目大小合理配置JVM内存
3. **深度设置**：从较小深度开始，逐步增加
4. **结果验证**：对关键调用链进行人工验证
5. **性能监控**：关注分析时间和资源消耗

## 与其他解析方法对比

| 特性 | JDT | javalang | 正则表达式 |
|------|-----|----------|------------|
| 解析精度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 多态支持 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| 继承处理 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| 性能 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 配置复杂度 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 方法映射 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |

---

通过JDT深度调用链分析，您可以获得最精确的Java代码分析结果，为代码迁移、重构和优化提供可靠的数据支持。