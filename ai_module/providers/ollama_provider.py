"""
Ollama Provider - Ollama AI服务提供者

基于本地部署的Ollama服务的AI提供者实现。
支持同步、异步和流式调用。
"""

import json
import logging
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Generator, AsyncGenerator
from ..core.interfaces import AIProvider, ChatMessage, ChatResponse, MessageRole

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """Ollama AI服务提供者
    
    连接本地部署的Ollama服务，支持多种开源大语言模型。
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 timeout: int = 60,  # 增加默认超时时间
                 default_model: str = "",  # 不设置硬编码默认模型
                 **kwargs):
        """初始化Ollama提供者
        
        Args:
            base_url: Ollama服务地址
            timeout: 请求超时时间（秒）
            default_model: 默认使用的模型
            **kwargs: 其他配置参数
        """
        super().__init__("ollama", {
            "base_url": base_url,
            "timeout": timeout,
            "default_model": default_model,
            **kwargs
        })
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.default_model = default_model
        self.session = None
        self._available_models = []
    
    def initialize(self) -> bool:
        """初始化Ollama服务连接"""
        try:
            # 创建HTTP会话
            self.session = requests.Session()
            self.session.timeout = self.timeout
            
            # 测试连接
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            # 获取可用模型
            self._available_models = self._fetch_available_models()
            
            self._initialized = True
            logger.info(f"Ollama provider initialized successfully. Available models: {len(self._available_models)}")
            
            # 检查默认模型是否可用
            if self.default_model and self.default_model not in self._available_models:
                logger.warning(f"默认模型 {self.default_model} 不在可用模型列表中")
                logger.info(f"可用模型: {self._available_models}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            return False
    
    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        if not self._initialized:
            return False
        
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        if not self._available_models:
            self._available_models = self._fetch_available_models()
        return self._available_models.copy()
    
    def _fetch_available_models(self) -> List[str]:
        """从Ollama服务获取可用模型列表"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                model_name = model.get("name", "")
                if model_name:
                    models.append(model_name)
            
            return models
            
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []
    
    def _get_preferred_model(self, requested_model: str = None) -> str:
        """获取首选模型
        
        Args:
            requested_model: 请求的模型名称
            
        Returns:
            str: 选择的模型名称
        """
        # 1. 如果明确指定了模型，使用指定的模型
        if requested_model:
            return requested_model
        
        # 2. 如果配置了默认模型且可用，使用默认模型
        if self.default_model:
            available_models = self.get_available_models()
            if self.default_model in available_models:
                logger.info(f"使用默认模型: {self.default_model}")
                return self.default_model
            else:
                logger.warning(f"默认模型 {self.default_model} 不可用，将使用其他可用模型")
        
        # 3. 使用第一个可用模型
        available_models = self.get_available_models()
        if not available_models:
            raise RuntimeError("没有可用的模型")
        
        selected_model = available_models[0]
        logger.info(f"使用第一个可用模型: {selected_model}")
        return selected_model
    
    def _prepare_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """准备发送给Ollama的消息格式"""
        ollama_messages = []
        
        for msg in messages:
            ollama_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return ollama_messages
    
    def chat(self, 
             messages: List[ChatMessage], 
             model: str = None,
             **kwargs) -> ChatResponse:
        """同步聊天接口"""
        if not self._initialized:
            raise RuntimeError("Ollama provider not initialized")
        
        # 选择模型
        model = self._get_preferred_model(model)
        
        # 准备请求数据
        request_data = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "stream": False,
            **kwargs
        }
        
        try:
            # 发送请求
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=request_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            return ChatResponse(
                content=result.get("message", {}).get("content", ""),
                model=model,
                provider=self.name,
                usage={
                    "prompt_eval_count": result.get("prompt_eval_count", 0),
                    "eval_count": result.get("eval_count", 0),
                    "total_duration": result.get("total_duration", 0)
                },
                metadata=result
            )
            
        except Exception as e:
            logger.error(f"Error in Ollama chat: {e}")
            raise
    
    async def chat_async(self, 
                         messages: List[ChatMessage], 
                         model: str = None,
                         **kwargs) -> ChatResponse:
        """异步聊天接口"""
        if not self._initialized:
            raise RuntimeError("Ollama provider not initialized")
        
        # 选择模型
        model = self._get_preferred_model(model)
        
        # 准备请求数据
        request_data = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "stream": False,
            **kwargs
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    return ChatResponse(
                        content=result.get("message", {}).get("content", ""),
                        model=model,
                        provider=self.name,
                        usage={
                            "prompt_eval_count": result.get("prompt_eval_count", 0),
                            "eval_count": result.get("eval_count", 0),
                            "total_duration": result.get("total_duration", 0)
                        },
                        metadata=result
                    )
                    
        except Exception as e:
            logger.error(f"Error in Ollama async chat: {e}")
            raise
    
    def chat_stream(self, 
                   messages: List[ChatMessage], 
                   model: str = None,
                   **kwargs) -> Generator[str, None, None]:
        """流式聊天接口（同步）"""
        if not self._initialized:
            raise RuntimeError("Ollama provider not initialized")
        
        # 选择模型
        model = self._get_preferred_model(model)
        
        # 准备请求数据
        request_data = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "stream": True,
            **kwargs
        }
        
        try:
            # 发送流式请求
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=request_data,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 逐行解析流式响应
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error in Ollama stream chat: {e}")
            raise
    
    async def chat_stream_async(self, 
                               messages: List[ChatMessage], 
                               model: str = None,
                               **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天接口（异步）"""
        if not self._initialized:
            raise RuntimeError("Ollama provider not initialized")
        
        # 选择模型
        model = self._get_preferred_model(model)
        
        # 准备请求数据
        request_data = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "stream": True,
            **kwargs
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    
                    # 逐行解析异步流式响应
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Error in Ollama async stream chat: {e}")
            raise
    
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """获取模型详细信息
        
        Args:
            model: 模型名称
            
        Returns:
            Optional[Dict[str, Any]]: 模型信息
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model}
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting model info for {model}: {e}")
            return None
    
    def pull_model(self, model: str) -> bool:
        """拉取模型
        
        Args:
            model: 模型名称
            
        Returns:
            bool: 是否成功
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=300  # 拉取模型可能需要较长时间
            )
            response.raise_for_status()
            
            # 刷新可用模型列表
            self._available_models = self._fetch_available_models()
            
            logger.info(f"Successfully pulled model: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Error pulling model {model}: {e}")
            return False
    
    def __del__(self):
        """清理资源"""
        if self.session:
            self.session.close()