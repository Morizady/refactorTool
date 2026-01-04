# JDT Java代码解析器功能说明

## 新增功能

本项目现已集成Eclipse JDT (Java Development Tools)，提供更精确的Java代码分析能力。

### 主要改进

1. **精确的AST解析**: 使用Eclipse JDT提供与IDE相同级别的代码分析精度
2. **完整的Java语法支持**: 支持Java 8-17的所有语法特性
3. **更好的错误处理**: 能够处理语法错误和不完整的代码
4. **丰富的元数据**: 提供详细的类型信息、注解、修饰符等
5. **高性能**: 利用JVM的优化能力，处理大型项目更高效

### 解析方法对比

| 特性 | JDT | javalang | 正则表达式 |
|------|-----|----------|------------|
| 解析精度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 性能 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Java版本支持 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 错误容忍性 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 配置复杂度 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 快速开始

### 1. 环境配置

```bash
# 自动配置环境
python setup_jdt.py

# 测试环境
python test_jdt_environment.py
```

### 2. 基本使用

```bash
# 使用JDT分析项目
python main.py --single /path/to/java/project --parse-method jdt

# 生成调用链树
python main.py --call-tree /api/user/login --parse-method jdt --max-depth 5

# 查看接口详情
python main.py --show-endpoint /api/user/list --parse-method jdt
```

### 3. 配置文件

编辑 `config.yml` 设置Java环境：

```yaml
java:
  java_home: "C:/Program Files/Java/jdk-11.0.16"  # 您的Java路径
  jvm_args:
    - "-Xmx2g"
    - "-Xms512m"
  jdt_lib_dir: "./lib/jdt"

parsing:
  method: "jdt"  # 使用JDT解析
  java_version: "11"
```

## 新增的分析能力

### 1. 精确的方法调用分析

JDT能够准确识别：
- 方法重载
- 泛型方法调用
- Lambda表达式
- 方法引用
- 链式调用

### 2. 完整的类型信息

提供详细的类型信息：
- 完全限定类名
- 泛型参数
- 注解信息
- 修饰符

### 3. 接口实现分析

准确分析：
- 接口继承关系
- 抽象类实现
- 多重继承
- 内部类关系

### 4. Spring框架支持

增强的Spring Boot分析：
- 精确的@Autowired依赖注入分析
- Controller和Service层映射
- 注解驱动的配置分析

## 性能优化

### 内存配置

对于大型项目，建议调整JVM内存：

```yaml
java:
  jvm_args:
    - "-Xmx4g"      # 4GB堆内存
    - "-Xms1g"      # 1GB初始内存
    - "-XX:+UseG1GC"  # G1垃圾收集器
```

### 并发处理

配置并发参数：

```yaml
performance:
  max_threads: 8        # 并发线程数
  max_file_size: 20     # 最大文件大小(MB)
  parse_timeout: 60     # 解析超时(秒)
```

## 故障排除

### 常见问题

1. **"未找到JAVA_HOME"**
   - 确保安装了Java 8+
   - 设置JAVA_HOME环境变量
   - 在config.yml中指定java_home

2. **"JPype初始化失败"**
   - 重新安装JPype: `pip install JPype1`
   - 检查Java版本兼容性

3. **"内存不足"**
   - 增加JVM堆内存: `-Xmx4g`
   - 减少并发线程数

### 调试模式

启用详细日志：

```yaml
logging:
  level: "DEBUG"
  console: true
  file: "./logs/jdt_debug.log"
```

## 向后兼容

原有的解析方法仍然可用：

```bash
# 使用javalang AST解析
python main.py --single /path/to/project --parse-method ast

# 使用正则表达式解析
python main.py --single /path/to/project --parse-method regex
```

## 最佳实践

1. **首选JDT**: 对于生产环境分析，推荐使用JDT方法
2. **合理配置内存**: 根据项目大小调整JVM内存
3. **启用缓存**: 对于重复分析，启用结果缓存
4. **分批处理**: 对于超大项目，考虑分模块分析

---

通过集成Eclipse JDT，本工具现在能够提供企业级的Java代码分析能力，为代码迁移和重构提供更可靠的支持。