#!/usr/bin/env python3
"""
AI提示词管理器

负责加载和管理不同类型的AI分析提示词配置。
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AIPromptManager:
    """AI提示词管理器"""
    
    def __init__(self, config_file: str = "ai_prompts.yaml"):
        """初始化提示词管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """加载配置文件
        
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(self.config_file):
                logger.error(f"配置文件不存在: {self.config_file}")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"成功加载提示词配置: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False
    
    def get_analysis_types(self) -> Dict[str, str]:
        """获取所有可用的分析类型
        
        Returns:
            Dict[str, str]: 分析类型及其描述
        """
        return self.config.get('analysis_types', {})
    
    def get_default_analysis_type(self) -> str:
        """获取默认分析类型
        
        Returns:
            str: 默认分析类型
        """
        return self.config.get('default_analysis_type', 'business_logic')
    
    def get_system_prompt(self, analysis_type: str = None) -> Optional[str]:
        """获取系统提示词
        
        Args:
            analysis_type: 分析类型，如果为None则使用默认类型
            
        Returns:
            Optional[str]: 系统提示词
        """
        if analysis_type is None:
            analysis_type = self.get_default_analysis_type()
        
        prompts = self.config.get('prompts', {})
        prompt_config = prompts.get(analysis_type, {})
        
        return prompt_config.get('system_prompt')
    
    def get_user_prompt_template(self, analysis_type: str = None) -> Optional[str]:
        """获取用户提示词模板
        
        Args:
            analysis_type: 分析类型，如果为None则使用默认类型
            
        Returns:
            Optional[str]: 用户提示词模板
        """
        if analysis_type is None:
            analysis_type = self.get_default_analysis_type()
        
        prompts = self.config.get('prompts', {})
        prompt_config = prompts.get(analysis_type, {})
        
        return prompt_config.get('user_prompt_template')
    
    def build_user_prompt(self, 
                         endpoint_path: str, 
                         code_file: str, 
                         code_content: str,
                         analysis_type: str = None) -> Optional[str]:
        """构建用户提示词
        
        Args:
            endpoint_path: 接口路径
            code_file: 代码文件路径
            code_content: 代码内容
            analysis_type: 分析类型
            
        Returns:
            Optional[str]: 构建的用户提示词
        """
        template = self.get_user_prompt_template(analysis_type)
        if not template:
            return None
        
        try:
            return template.format(
                endpoint_path=endpoint_path,
                code_file=code_file,
                code_content=code_content
            )
        except Exception as e:
            logger.error(f"构建用户提示词失败: {e}")
            return None
    
    def list_analysis_types(self) -> None:
        """列出所有可用的分析类型"""
        print("📋 可用的分析类型:")
        print("-" * 50)
        
        analysis_types = self.get_analysis_types()
        default_type = self.get_default_analysis_type()
        
        for type_name, description in analysis_types.items():
            marker = "✅" if type_name == default_type else "  "
            print(f"{marker} {type_name}: {description}")
        
        print(f"\n💡 默认分析类型: {default_type}")
    
    def validate_analysis_type(self, analysis_type: str) -> bool:
        """验证分析类型是否有效
        
        Args:
            analysis_type: 分析类型
            
        Returns:
            bool: 是否有效
        """
        return analysis_type in self.get_analysis_types()


def create_default_prompts_config(config_file: str = "ai_prompts.yaml") -> bool:
    """创建默认的提示词配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        bool: 是否创建成功
    """
    if os.path.exists(config_file):
        logger.info(f"配置文件已存在: {config_file}")
        return True
    
    # 这里可以创建默认配置，但由于我们已经有了配置文件，所以直接返回
    logger.info(f"请手动创建配置文件: {config_file}")
    return False


if __name__ == "__main__":
    # 测试提示词管理器
    print("🧪 测试AI提示词管理器...")
    
    manager = AIPromptManager()
    
    # 列出分析类型
    manager.list_analysis_types()
    
    # 测试获取提示词
    print(f"\n📋 测试获取业务逻辑分析提示词:")
    system_prompt = manager.get_system_prompt("business_logic")
    if system_prompt:
        print(f"✅ 系统提示词长度: {len(system_prompt)} 字符")
        print(f"📝 系统提示词预览: {system_prompt[:100]}...")
    
    user_template = manager.get_user_prompt_template("business_logic")
    if user_template:
        print(f"✅ 用户模板长度: {len(user_template)} 字符")
    
    # 测试构建用户提示词
    user_prompt = manager.build_user_prompt(
        endpoint_path="/test/api",
        code_file="test.java",
        code_content="public class Test { }",
        analysis_type="business_logic"
    )
    
    if user_prompt:
        print(f"✅ 用户提示词构建成功，长度: {len(user_prompt)} 字符")
    
    print("\n✅ 测试完成！")