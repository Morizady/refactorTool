# AI Module - 智能分析模块

基于本地Ollama模型的AI功能模块，提供代码分析、智能问答等功能。采用可扩展架构设计，未来可集成RAG、MCP、智能体等高级功能。

## 🏗️ 架构设计

```
ai_module/
├── core/                   # 核心组件
│   ├── interfaces.py      # 抽象接口定义
│   └── manager.py         # AI服务管理器
├── providers/             # AI服务提供者
│   └── ollama_provider.py # Ollama提供者实现
├── config/                # 配置管理
│   └── settings.py        # 配置加载和验证
├── utils/                 # 工具函数
│   ├── helpers.py         # 辅助工具
│   └── validators.py      # 验证工具
└── README.md              # 说明文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests aiohttp pyyaml
```

### 2. 启动Ollama服务

确保本地已安装并启动Ollama服务：

```bash
# 安装Ollama（如果尚未安装）
curl -fsSL https://ollama.ai/install.sh | sh

# 启动Ollama服务
ollama serve

# 拉取一个模型（例如llama2）
ollama pull llama2
```

### 3. 基本使用

```python
from ai_module import AIManager, OllamaProvider

# 创建AI管理器
ai = AIManager()

# 创建并注册Ollama提供者
ollama = OllamaProvider(base_url="http://localhost:11434")
ai.register_provider(ollama, set_as_default=True)

# 发送聊天消息
response = ai.chat("请分析这段Java代码的功能")
print(response.content)
```

### 4. 代码分析示例

```python
from ai_module.utils import format_code_for_ai

# 格式化代码用于AI分析
java_code = """
public class UserController {
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        User user = userService.findById(id);
        return ResponseEntity.ok(user);
    }
}
"""

formatted_code = format_code_for_ai(
    code=java_code,
    language="java",
    context="Spring Boot REST控制器"
)

# 发送给AI分析
response = ai.chat(
    message=f"请分析以下代码：\n{formatted_code}",
    system_prompt="你是一个专业的Java代码分析师"
)
```

## 🔧 配置管理

### 配置文件示例 (ai_config.yaml)

```yaml
# 基础配置
default_provider: "ollama"
max_history_length: 50
log_level: "INFO"

# Ollama配置
ollama:
  base_url: "http://localhost:11434"
  timeout: 30
  default_model: ""
  temperature: 0.7
  max_tokens: 2048
```

### 加载配置

```python
from ai_module.config import load_config, create_default_config

# 创建默认配置文件
create_default_config("ai_config.yaml")

# 加载配置
config = load_config("ai_config.yaml")
```

## 🌊 高级功能

### 1. 流式聊天

```python
# 同步流式聊天
stream = ai.chat_stream("请详细解释什么是微服务架构？")
for chunk in stream:
    print(chunk, end="", flush=True)

# 异步流式聊天
async def async_stream_example():
    async for chunk in ai.chat_stream_async("解释设计模式"):
        print(chunk, end="", flush=True)
```

### 2. 对话历史管理

```python
# 启用对话历史
response = ai.chat("我的名字是张三", use_history=True)
response = ai.chat("我刚才说我叫什么？", use_history=True)

# 获取对话历史
history = ai.get_history()

# 清空历史
ai.clear_history()

# 设置历史长度限制
ai.set_max_history_length(20)
```

### 3. 多提供者管理

```python
# 注册多个提供者
ai.register_provider(ollama_provider, set_as_default=True)
# ai.register_provider(openai_provider)  # 未来支持

# 指定提供者
response = ai.chat("Hello", provider_name="ollama")

# 列出所有提供者
providers = ai.list_providers()
```

## 🔌 扩展接口

### 自定义AI提供者

```python
from ai_module.core.interfaces import AIProvider, ChatMessage, ChatResponse

class CustomProvider(AIProvider):
    def __init__(self):
        super().__init__("custom")
    
    def initialize(self) -> bool:
        # 初始化逻辑
        return True
    
    def is_available(self) -> bool:
        # 检查可用性
        return True
    
    def get_available_models(self) -> List[str]:
        # 返回可用模型
        return ["custom-model"]
    
    def chat(self, messages: List[ChatMessage], model: str = None, **kwargs) -> ChatResponse:
        # 实现聊天逻辑
        pass
    
    # 实现其他抽象方法...
```

## 🛠️ 工具函数

### 代码格式化

```python
from ai_module.utils import format_code_for_ai, extract_code_from_response

# 格式化代码
formatted = format_code_for_ai(code, "python", "Flask应用示例")

# 从AI响应中提取代码
code_blocks = extract_code_from_response(ai_response, "java")
```

### 数据验证

```python
from ai_module.utils import validate_model_name, validate_provider_config

# 验证模型名称
is_valid = validate_model_name("llama2:7b")

# 验证提供者配置
is_valid = validate_provider_config("ollama", {
    "base_url": "http://localhost:11434",
    "timeout": 30
})
```

## 🔮 未来扩展规划

### 1. RAG (检索增强生成)
```python
# 未来支持
from ai_module.rag import RAGManager

rag = RAGManager()
rag.add_documents(documents)
response = ai.chat_with_rag("基于文档回答问题")
```

### 2. MCP (模型上下文协议)
```python
# 未来支持
from ai_module.mcp import MCPClient

mcp = MCPClient()
tools = mcp.get_available_tools()
response = ai.chat_with_tools("使用工具完成任务", tools=tools)
```

### 3. 智能体系统
```python
# 未来支持
from ai_module.agents import Agent, AgentRouter

agent = Agent("code_analyzer")
router = AgentRouter()
response = router.route_to_agent("分析这段代码", context)
```

## 🧪 测试

运行测试脚本：

```bash
python test_ai_module.py
```

测试包括：
- 基本聊天功能
- 流式聊天
- 异步聊天
- 对话历史管理
- 错误处理

## 📝 日志配置

```python
from ai_module.utils import setup_logging

# 设置日志
logger = setup_logging(
    level="INFO",
    log_file="ai_module.log"
)
```

## ⚠️ 注意事项

1. **Ollama服务**: 确保Ollama服务正在运行且可访问
2. **模型管理**: 至少需要拉取一个模型才能使用
3. **内存使用**: 大型模型可能需要较多内存
4. **网络连接**: 首次拉取模型需要网络连接
5. **并发限制**: Ollama服务有并发请求限制

## 🤝 贡献指南

1. 遵循现有的代码风格和架构设计
2. 添加适当的类型注解和文档字符串
3. 编写相应的测试用例
4. 更新相关文档

## 📄 许可证

本项目采用MIT许可证。