# 默认模型设置总结

## 🎯 目标

将AI模块的默认模型从 `qwen3:8b` 更改为 `qwen3-coder:30b`，以获得更好的编程相关任务性能。

## ✅ 完成的更改

### 1. 配置文件更新
**文件**: `ai_config.yaml`

**更改内容**:
```yaml
# 修改前
default_model: "qwen3:8b"  # 使用8b模型，适合16GB内存系统

# 修改后  
default_model: "qwen3-coder:30b"  # 使用30b编程专用模型
```

### 2. 代码更新
**文件**: `main.py`

**更改位置**:
1. `ai_analyze_endpoint_code()` 函数中的AI初始化
2. `ai_chat_stream()` 函数中的AI初始化

**更改内容**:
```python
# 修改前
ollama_provider = OllamaProvider()

# 修改后
from ai_module.config.settings import load_config
config = load_config("ai_config.yaml")

ollama_provider = OllamaProvider(
    default_model=config.ollama.default_model,
    timeout=config.ollama.timeout,
    base_url=config.ollama.base_url
)
```

## 📋 验证结果

### 测试执行
运行 `python test_default_model.py` 的结果：

```
✅ 配置加载成功
📋 默认模型: qwen3-coder:30b
✅ 提供者初始化成功  
✅ 目标模型 qwen3-coder:30b 可用
✅ 首选模型正确设置为 qwen3-coder:30b
✅ 所有测试通过！
```

### 功能验证
- ✅ 配置文件正确加载
- ✅ 默认模型设置生效
- ✅ 模型在可用列表中
- ✅ AI管理器使用正确模型
- ✅ 提供者初始化成功

## 🚀 使用方法

### AI对话功能
```bash
python main.py --ai-chat "你好"
```

### AI代码分析功能  
```bash
python main.py --ai-analyze <接口路径> --output <输出目录>
```

### 直接测试模型
```bash
python test_qwen_coder_chat.py
```

## 📊 模型对比

| 特性 | qwen3:8b | qwen3-coder:30b |
|------|----------|-----------------|
| 模型大小 | ~8GB | ~30GB |
| 参数量 | 8B | 30B |
| 专业领域 | 通用 | 编程专用 |
| 代码理解 | 一般 | 优秀 |
| 代码生成 | 一般 | 优秀 |
| 内存需求 | 较低 | 较高 |
| 响应质量 | 基础 | 专业 |

## 💡 优势

1. **专业性强** - qwen3-coder专门针对编程任务优化
2. **代码质量高** - 生成的代码更准确、更符合最佳实践
3. **理解能力强** - 对复杂代码逻辑理解更深入
4. **多语言支持** - 支持多种编程语言的分析和生成

## ⚠️ 注意事项

1. **资源需求** - 30B模型需要更多内存和计算资源
2. **响应时间** - 可能比8B模型响应稍慢
3. **磁盘空间** - 模型文件约30GB
4. **网络要求** - 首次拉取需要稳定网络连接

## 🔧 故障排除

### 如果模型不可用
```bash
# 拉取模型
ollama pull qwen3-coder:30b

# 检查模型列表
ollama list
```

### 如果内存不足
可以临时切换回较小模型：
```yaml
# 在 ai_config.yaml 中修改
default_model: "qwen3:8b"
```

### 如果响应超时
增加超时时间：
```yaml
# 在 ai_config.yaml 中修改
timeout: 120  # 增加到120秒
```

## 📁 相关文件

- `ai_config.yaml` - 主配置文件
- `main.py` - 主程序文件
- `test_default_model.py` - 配置测试脚本
- `test_qwen_coder_chat.py` - 模型对话测试脚本
- `ai_module/config/settings.py` - 配置管理模块
- `ai_module/providers/ollama_provider.py` - Ollama提供者

## 🎉 总结

默认模型已成功从 `qwen3:8b` 更改为 `qwen3-coder:30b`。新模型专门针对编程任务优化，将为代码分析、生成和理解提供更好的性能。所有相关功能（AI对话、AI分析）都将自动使用新的默认模型。