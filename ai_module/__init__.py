"""
AI Module - 智能分析模块

提供基于本地Ollama模型的AI功能，支持代码分析、智能问答等功能。
设计为可扩展架构，未来可集成RAG、MCP、智能体等高级功能。

主要组件:
- core: 核心抽象接口和基础类
- providers: AI服务提供者实现（Ollama等）
- config: 配置管理
- utils: 工具函数

使用示例:
    from ai_module import AIManager
    
    ai = AIManager()
    response = ai.chat("请分析这段代码的功能")
"""

from .core.manager import AIManager
from .core.interfaces import AIProvider, ChatMessage, ChatResponse
from .providers.ollama_provider import OllamaProvider

__version__ = "1.0.0"
__author__ = "RefactorTool Team"

__all__ = [
    "AIManager",
    "AIProvider", 
    "ChatMessage",
    "ChatResponse",
    "OllamaProvider"
]