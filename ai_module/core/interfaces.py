"""
AI Module Interfaces - 核心接口定义

定义AI模块的核心抽象接口和数据模型，为未来扩展提供统一的接口规范。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator
from enum import Enum
import time


class MessageRole(Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user" 
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    """聊天消息数据模型"""
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """从字典创建消息对象"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {})
        )


@dataclass
class ChatResponse:
    """AI响应数据模型"""
    content: str
    model: str
    provider: str
    timestamp: float = field(default_factory=time.time)
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "timestamp": self.timestamp,
            "usage": self.usage,
            "metadata": self.metadata
        }


class AIProvider(ABC):
    """AI服务提供者抽象基类
    
    定义了AI服务提供者的标准接口，支持同步和异步调用。
    未来可扩展支持不同的AI服务（OpenAI、Claude、本地模型等）。
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化AI服务提供者
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查AI服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表
        
        Returns:
            List[str]: 可用模型名称列表
        """
        pass
    
    @abstractmethod
    def chat(self, 
             messages: List[ChatMessage], 
             model: str = None,
             **kwargs) -> ChatResponse:
        """同步聊天接口
        
        Args:
            messages: 消息历史列表
            model: 使用的模型名称
            **kwargs: 其他参数（temperature、max_tokens等）
            
        Returns:
            ChatResponse: AI响应
        """
        pass
    
    @abstractmethod
    async def chat_async(self, 
                         messages: List[ChatMessage], 
                         model: str = None,
                         **kwargs) -> ChatResponse:
        """异步聊天接口
        
        Args:
            messages: 消息历史列表
            model: 使用的模型名称
            **kwargs: 其他参数
            
        Returns:
            ChatResponse: AI响应
        """
        pass
    
    @abstractmethod
    def chat_stream(self, 
                   messages: List[ChatMessage], 
                   model: str = None,
                   **kwargs) -> Generator[str, None, None]:
        """流式聊天接口（同步）
        
        Args:
            messages: 消息历史列表
            model: 使用的模型名称
            **kwargs: 其他参数
            
        Yields:
            str: 流式响应内容片段
        """
        pass
    
    @abstractmethod
    async def chat_stream_async(self, 
                               messages: List[ChatMessage], 
                               model: str = None,
                               **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天接口（异步）
        
        Args:
            messages: 消息历史列表
            model: 使用的模型名称
            **kwargs: 其他参数
            
        Yields:
            str: 流式响应内容片段
        """
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供者信息
        
        Returns:
            Dict[str, Any]: 提供者信息
        """
        return {
            "name": self.name,
            "initialized": self._initialized,
            "available": self.is_available(),
            "config": self.config
        }


class AICapability(Enum):
    """AI能力枚举 - 为未来扩展预留"""
    CHAT = "chat"                    # 基础聊天
    CODE_ANALYSIS = "code_analysis"  # 代码分析
    RAG = "rag"                     # 检索增强生成
    AGENT = "agent"                 # 智能体
    MCP = "mcp"                     # 模型上下文协议
    EMBEDDING = "embedding"         # 向量嵌入
    FUNCTION_CALLING = "function_calling"  # 函数调用


@dataclass
class AICapabilityInfo:
    """AI能力信息 - 为未来扩展预留"""
    capability: AICapability
    supported: bool
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)