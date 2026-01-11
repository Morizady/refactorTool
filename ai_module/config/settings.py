"""
AI Settings - AI模块配置管理

提供配置文件的加载、保存和验证功能。
"""

import os
import json
import yaml
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama配置"""
    base_url: str = "http://localhost:11434"
    timeout: int = 30
    default_model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class AISettings:
    """AI模块配置设置"""
    # 基础配置
    default_provider: str = "ollama"
    max_history_length: int = 50
    log_level: str = "INFO"
    
    # Ollama配置
    ollama: OllamaConfig = None
    
    # 未来扩展配置预留
    openai: Dict[str, Any] = None
    claude: Dict[str, Any] = None
    rag: Dict[str, Any] = None
    mcp: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.ollama is None:
            self.ollama = OllamaConfig()
        
        # 初始化其他配置为空字典
        if self.openai is None:
            self.openai = {}
        if self.claude is None:
            self.claude = {}
        if self.rag is None:
            self.rag = {}
        if self.mcp is None:
            self.mcp = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AISettings':
        """从字典创建配置对象"""
        # 处理Ollama配置
        ollama_data = data.get('ollama', {})
        if isinstance(ollama_data, dict):
            ollama_config = OllamaConfig(**ollama_data)
        else:
            ollama_config = OllamaConfig()
        
        # 创建配置对象
        return cls(
            default_provider=data.get('default_provider', 'ollama'),
            max_history_length=data.get('max_history_length', 50),
            log_level=data.get('log_level', 'INFO'),
            ollama=ollama_config,
            openai=data.get('openai', {}),
            claude=data.get('claude', {}),
            rag=data.get('rag', {}),
            mcp=data.get('mcp', {})
        )
    
    def validate(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证基础配置
            if self.max_history_length < 1:
                logger.error("max_history_length must be greater than 0")
                return False
            
            if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                logger.error(f"Invalid log_level: {self.log_level}")
                return False
            
            # 验证Ollama配置
            if self.ollama:
                if not self.ollama.base_url:
                    logger.error("Ollama base_url cannot be empty")
                    return False
                
                if self.ollama.timeout < 1:
                    logger.error("Ollama timeout must be greater than 0")
                    return False
                
                if not (0.0 <= self.ollama.temperature <= 2.0):
                    logger.error("Ollama temperature must be between 0.0 and 2.0")
                    return False
                
                if self.ollama.max_tokens < 1:
                    logger.error("Ollama max_tokens must be greater than 0")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return False


def load_config(config_path: str = "ai_config.yaml") -> AISettings:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        AISettings: 配置对象
    """
    try:
        if not os.path.exists(config_path):
            logger.info(f"Config file {config_path} not found, using default settings")
            return AISettings()
        
        # 根据文件扩展名选择解析方式
        _, ext = os.path.splitext(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if ext.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif ext.lower() == '.json':
                data = json.load(f)
            else:
                logger.error(f"Unsupported config file format: {ext}")
                return AISettings()
        
        if not data:
            logger.warning("Empty config file, using default settings")
            return AISettings()
        
        # 创建配置对象
        settings = AISettings.from_dict(data)
        
        # 验证配置
        if not settings.validate():
            logger.error("Invalid configuration, using default settings")
            return AISettings()
        
        logger.info(f"Successfully loaded configuration from {config_path}")
        return settings
        
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        return AISettings()


def save_config(settings: AISettings, config_path: str = "ai_config.yaml") -> bool:
    """保存配置文件
    
    Args:
        settings: 配置对象
        config_path: 配置文件路径
        
    Returns:
        bool: 是否保存成功
    """
    try:
        # 验证配置
        if not settings.validate():
            logger.error("Invalid configuration, cannot save")
            return False
        
        # 转换为字典
        data = settings.to_dict()
        
        # 根据文件扩展名选择保存方式
        _, ext = os.path.splitext(config_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path) if os.path.dirname(config_path) else '.', exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if ext.lower() in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
            elif ext.lower() == '.json':
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                logger.error(f"Unsupported config file format: {ext}")
                return False
        
        logger.info(f"Successfully saved configuration to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config file {config_path}: {e}")
        return False


def create_default_config(config_path: str = "ai_config.yaml") -> bool:
    """创建默认配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        bool: 是否创建成功
    """
    try:
        if os.path.exists(config_path):
            logger.info(f"Config file {config_path} already exists")
            return True
        
        # 创建默认配置
        default_settings = AISettings()
        
        # 保存配置文件
        return save_config(default_settings, config_path)
        
    except Exception as e:
        logger.error(f"Error creating default config: {e}")
        return False