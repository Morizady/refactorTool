"""
AI Manager - AI服务管理器

统一管理多个AI服务提供者，提供简化的API接口。
支持提供者注册、自动选择、负载均衡等功能。
"""

import logging
from typing import Dict, List, Optional, Any, Generator, AsyncGenerator
from .interfaces import AIProvider, ChatMessage, ChatResponse, MessageRole, AICapability

logger = logging.getLogger(__name__)


class AIManager:
    """AI服务管理器
    
    统一管理和调度多个AI服务提供者，提供简化的使用接口。
    """
    
    def __init__(self):
        self._providers: Dict[str, AIProvider] = {}
        self._default_provider: Optional[str] = None
        self._conversation_history: List[ChatMessage] = []
        self._max_history_length = 50  # 最大对话历史长度
    
    def register_provider(self, provider: AIProvider, set_as_default: bool = False, config: Dict[str, Any] = None) -> bool:
        """注册AI服务提供者
        
        Args:
            provider: AI服务提供者实例
            set_as_default: 是否设置为默认提供者
            config: 提供者配置信息
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 如果提供了配置，更新提供者配置
            if config and hasattr(provider, 'default_model'):
                default_model = config.get('default_model')
                if default_model:
                    provider.default_model = default_model
                    logger.info(f"设置提供者 {provider.name} 的默认模型为: {default_model}")
            
            # 初始化提供者
            if not provider.initialize():
                logger.error(f"Failed to initialize provider: {provider.name}")
                return False
            
            # 检查服务可用性
            if not provider.is_available():
                logger.warning(f"Provider {provider.name} is not available")
                return False
            
            # 注册提供者
            self._providers[provider.name] = provider
            
            # 设置默认提供者
            if set_as_default or self._default_provider is None:
                self._default_provider = provider.name
            
            logger.info(f"Successfully registered AI provider: {provider.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering provider {provider.name}: {e}")
            return False
    
    def get_provider(self, name: str = None) -> Optional[AIProvider]:
        """获取AI服务提供者
        
        Args:
            name: 提供者名称，如果为None则返回默认提供者
            
        Returns:
            Optional[AIProvider]: AI服务提供者实例
        """
        if name is None:
            name = self._default_provider
        
        if name is None:
            logger.error("No default provider set and no provider name specified")
            return None
        
        return self._providers.get(name)
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有注册的提供者信息
        
        Returns:
            List[Dict[str, Any]]: 提供者信息列表
        """
        return [
            {
                **provider.get_provider_info(),
                "is_default": name == self._default_provider
            }
            for name, provider in self._providers.items()
        ]
    
    def get_available_models(self, provider_name: str = None) -> List[str]:
        """获取可用模型列表
        
        Args:
            provider_name: 提供者名称
            
        Returns:
            List[str]: 可用模型列表
        """
        provider = self.get_provider(provider_name)
        if provider is None:
            return []
        
        try:
            return provider.get_available_models()
        except Exception as e:
            logger.error(f"Error getting available models from {provider.name}: {e}")
            return []
    
    def chat(self, 
             message: str, 
             provider_name: str = None,
             model: str = None,
             system_prompt: str = None,
             use_history: bool = True,
             **kwargs) -> Optional[ChatResponse]:
        """发送聊天消息
        
        Args:
            message: 用户消息内容
            provider_name: 指定的提供者名称
            model: 指定的模型名称
            system_prompt: 系统提示词
            use_history: 是否使用对话历史
            **kwargs: 其他参数
            
        Returns:
            Optional[ChatResponse]: AI响应
        """
        provider = self.get_provider(provider_name)
        if provider is None:
            logger.error("No available AI provider")
            return None
        
        try:
            # 构建消息列表
            messages = []
            
            # 添加系统提示词
            if system_prompt:
                messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=system_prompt
                ))
            
            # 添加对话历史
            if use_history and self._conversation_history:
                messages.extend(self._conversation_history)
            
            # 添加当前用户消息
            user_message = ChatMessage(
                role=MessageRole.USER,
                content=message
            )
            messages.append(user_message)
            
            # 调用AI服务
            response = provider.chat(messages, model=model, **kwargs)
            
            # 更新对话历史
            if use_history:
                self._add_to_history(user_message)
                self._add_to_history(ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                ))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return None
    
    async def chat_async(self, 
                         message: str, 
                         provider_name: str = None,
                         model: str = None,
                         system_prompt: str = None,
                         use_history: bool = True,
                         **kwargs) -> Optional[ChatResponse]:
        """异步发送聊天消息
        
        Args:
            message: 用户消息内容
            provider_name: 指定的提供者名称
            model: 指定的模型名称
            system_prompt: 系统提示词
            use_history: 是否使用对话历史
            **kwargs: 其他参数
            
        Returns:
            Optional[ChatResponse]: AI响应
        """
        provider = self.get_provider(provider_name)
        if provider is None:
            logger.error("No available AI provider")
            return None
        
        try:
            # 构建消息列表（与同步版本相同的逻辑）
            messages = []
            
            if system_prompt:
                messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=system_prompt
                ))
            
            if use_history and self._conversation_history:
                messages.extend(self._conversation_history)
            
            user_message = ChatMessage(
                role=MessageRole.USER,
                content=message
            )
            messages.append(user_message)
            
            # 调用异步AI服务
            response = await provider.chat_async(messages, model=model, **kwargs)
            
            # 更新对话历史
            if use_history:
                self._add_to_history(user_message)
                self._add_to_history(ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                ))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in async chat: {e}")
            return None
    
    def chat_stream(self, 
                   message: str, 
                   provider_name: str = None,
                   model: str = None,
                   system_prompt: str = None,
                   use_history: bool = True,
                   **kwargs) -> Optional[Generator[str, None, None]]:
        """流式聊天
        
        Args:
            message: 用户消息内容
            provider_name: 指定的提供者名称
            model: 指定的模型名称
            system_prompt: 系统提示词
            use_history: 是否使用对话历史
            **kwargs: 其他参数
            
        Returns:
            Optional[Generator[str, None, None]]: 流式响应生成器
        """
        provider = self.get_provider(provider_name)
        if provider is None:
            logger.error("No available AI provider")
            return None
        
        try:
            # 构建消息列表
            messages = []
            
            if system_prompt:
                messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=system_prompt
                ))
            
            if use_history and self._conversation_history:
                messages.extend(self._conversation_history)
            
            user_message = ChatMessage(
                role=MessageRole.USER,
                content=message
            )
            messages.append(user_message)
            
            # 更新历史（用户消息）
            if use_history:
                self._add_to_history(user_message)
            
            # 返回流式生成器
            return provider.chat_stream(messages, model=model, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in stream chat: {e}")
            return None
    
    def clear_history(self):
        """清空对话历史"""
        self._conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[ChatMessage]:
        """获取对话历史
        
        Returns:
            List[ChatMessage]: 对话历史列表
        """
        return self._conversation_history.copy()
    
    def _add_to_history(self, message: ChatMessage):
        """添加消息到历史记录"""
        self._conversation_history.append(message)
        
        # 限制历史长度
        if len(self._conversation_history) > self._max_history_length:
            self._conversation_history = self._conversation_history[-self._max_history_length:]
    
    def set_max_history_length(self, length: int):
        """设置最大历史长度
        
        Args:
            length: 最大历史长度
        """
        self._max_history_length = max(1, length)
        
        # 如果当前历史超过新的限制，进行截断
        if len(self._conversation_history) > self._max_history_length:
            self._conversation_history = self._conversation_history[-self._max_history_length:]
    
    def get_status(self) -> Dict[str, Any]:
        """获取AI管理器状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "providers_count": len(self._providers),
            "default_provider": self._default_provider,
            "history_length": len(self._conversation_history),
            "max_history_length": self._max_history_length,
            "providers": self.list_providers()
        }