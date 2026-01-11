"""
AI Validators - 验证工具函数

提供各种验证功能，确保输入数据的有效性。
"""

import re
from typing import Dict, Any, List
from urllib.parse import urlparse


def validate_model_name(model_name: str) -> bool:
    """验证模型名称格式
    
    Args:
        model_name: 模型名称
        
    Returns:
        bool: 是否有效
    """
    if not model_name or not isinstance(model_name, str):
        return False
    
    # 模型名称应该只包含字母、数字、连字符、下划线和冒号
    pattern = r'^[a-zA-Z0-9\-_:\.]+$'
    return bool(re.match(pattern, model_name))


def validate_provider_config(provider_name: str, config: Dict[str, Any]) -> bool:
    """验证AI提供者配置
    
    Args:
        provider_name: 提供者名称
        config: 配置字典
        
    Returns:
        bool: 配置是否有效
    """
    if not provider_name or not isinstance(provider_name, str):
        return False
    
    if not isinstance(config, dict):
        return False
    
    # 根据提供者类型进行特定验证
    if provider_name.lower() == "ollama":
        return _validate_ollama_config(config)
    elif provider_name.lower() == "openai":
        return _validate_openai_config(config)
    elif provider_name.lower() == "claude":
        return _validate_claude_config(config)
    
    # 对于未知提供者，进行基本验证
    return True


def _validate_ollama_config(config: Dict[str, Any]) -> bool:
    """验证Ollama配置"""
    # 验证base_url
    base_url = config.get("base_url", "")
    if not base_url:
        return False
    
    try:
        parsed_url = urlparse(base_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return False
    except Exception:
        return False
    
    # 验证timeout
    timeout = config.get("timeout", 30)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        return False
    
    # 验证temperature（如果存在）
    temperature = config.get("temperature")
    if temperature is not None:
        if not isinstance(temperature, (int, float)) or not (0.0 <= temperature <= 2.0):
            return False
    
    # 验证max_tokens（如果存在）
    max_tokens = config.get("max_tokens")
    if max_tokens is not None:
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            return False
    
    return True


def _validate_openai_config(config: Dict[str, Any]) -> bool:
    """验证OpenAI配置"""
    # 验证API密钥
    api_key = config.get("api_key", "")
    if not api_key or not isinstance(api_key, str):
        return False
    
    # 验证base_url（如果存在）
    base_url = config.get("base_url")
    if base_url is not None:
        try:
            parsed_url = urlparse(base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
        except Exception:
            return False
    
    return True


def _validate_claude_config(config: Dict[str, Any]) -> bool:
    """验证Claude配置"""
    # 验证API密钥
    api_key = config.get("api_key", "")
    if not api_key or not isinstance(api_key, str):
        return False
    
    return True


def validate_message_content(content: str, max_length: int = 100000) -> bool:
    """验证消息内容
    
    Args:
        content: 消息内容
        max_length: 最大长度限制
        
    Returns:
        bool: 内容是否有效
    """
    if not isinstance(content, str):
        return False
    
    if len(content) == 0 or len(content) > max_length:
        return False
    
    # 检查是否包含有害内容（基础检查）
    harmful_patterns = [
        r'<script[^>]*>.*?</script>',  # 脚本标签
        r'javascript:',               # JavaScript协议
        r'data:text/html',           # HTML数据URI
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False
    
    return True


def validate_system_prompt(prompt: str) -> bool:
    """验证系统提示词
    
    Args:
        prompt: 系统提示词
        
    Returns:
        bool: 提示词是否有效
    """
    if not isinstance(prompt, str):
        return False
    
    # 系统提示词可以为空
    if len(prompt) == 0:
        return True
    
    # 长度限制
    if len(prompt) > 10000:
        return False
    
    return validate_message_content(prompt)


def validate_chat_parameters(**kwargs) -> Dict[str, Any]:
    """验证聊天参数
    
    Args:
        **kwargs: 聊天参数
        
    Returns:
        Dict[str, Any]: 验证后的参数字典
    """
    validated_params = {}
    
    # 验证temperature
    temperature = kwargs.get("temperature")
    if temperature is not None:
        if isinstance(temperature, (int, float)) and 0.0 <= temperature <= 2.0:
            validated_params["temperature"] = float(temperature)
    
    # 验证max_tokens
    max_tokens = kwargs.get("max_tokens")
    if max_tokens is not None:
        if isinstance(max_tokens, int) and max_tokens > 0:
            validated_params["max_tokens"] = max_tokens
    
    # 验证top_p
    top_p = kwargs.get("top_p")
    if top_p is not None:
        if isinstance(top_p, (int, float)) and 0.0 <= top_p <= 1.0:
            validated_params["top_p"] = float(top_p)
    
    # 验证top_k
    top_k = kwargs.get("top_k")
    if top_k is not None:
        if isinstance(top_k, int) and top_k > 0:
            validated_params["top_k"] = top_k
    
    # 验证stop序列
    stop = kwargs.get("stop")
    if stop is not None:
        if isinstance(stop, str):
            validated_params["stop"] = [stop]
        elif isinstance(stop, list) and all(isinstance(s, str) for s in stop):
            validated_params["stop"] = stop[:4]  # 限制最多4个stop序列
    
    return validated_params


def validate_url(url: str) -> bool:
    """验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        bool: URL是否有效
    """
    if not isinstance(url, str) or not url:
        return False
    
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    if not isinstance(filename, str):
        return "untitled"
    
    # 移除路径分隔符和其他不安全字符
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
    cleaned = re.sub(unsafe_chars, '_', filename)
    
    # 移除首尾空白和点号
    cleaned = cleaned.strip(' .')
    
    # 确保不为空
    if not cleaned:
        cleaned = "untitled"
    
    # 限制长度
    if len(cleaned) > 255:
        cleaned = cleaned[:255]
    
    return cleaned