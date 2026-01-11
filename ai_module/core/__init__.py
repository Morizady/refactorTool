"""
AI Module Core - 核心组件

包含AI模块的核心抽象接口、数据模型和管理器。
"""

from .interfaces import AIProvider, ChatMessage, ChatResponse
from .manager import AIManager

__all__ = [
    "AIProvider",
    "ChatMessage", 
    "ChatResponse",
    "AIManager"
]