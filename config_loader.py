#!/usr/bin/env python3
"""
配置文件加载器
用于加载和管理项目配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_file: str = "config.yml"):
        """初始化配置加载器"""
        self.config_file = Path(config_file)
        self._config = None
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_file.exists():
            logger.warning(f"配置文件不存在: {self.config_file}")
            self._config = self._get_default_config()
            return self._config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self._config = self._get_default_config()
        
        return self._config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔的路径"""
        if self._config is None:
            self.load_config()
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_maven_repository_path(self) -> str:
        """获取Maven仓库路径"""
        repo_path = self.get('maven.repository_path')
        
        if repo_path:
            # 处理Windows路径中的反斜杠
            repo_path = repo_path.replace('\\', os.sep)
            return repo_path
        
        # 如果配置中没有指定，返回默认路径
        return self._get_default_maven_repo()
    
    def get_maven_settings_file(self) -> Optional[str]:
        """获取Maven设置文件路径"""
        settings_file = self.get('maven.settings_file')
        return settings_file if settings_file else None
    
    def is_maven_dependency_analysis_enabled(self) -> bool:
        """检查是否启用Maven依赖分析"""
        return self.get('maven.enable_dependency_analysis', True)
    
    def get_java_home(self) -> str:
        """获取Java Home路径"""
        java_home = self.get('java.java_home')
        if java_home:
            return java_home.replace('\\', os.sep)
        
        # 尝试从环境变量获取
        return os.getenv('JAVA_HOME', '')
    
    def get_jdt_lib_dir(self) -> str:
        """获取JDT库目录"""
        return self.get('java.jdt_lib_dir', './lib/jdt')
    
    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.get('output.dir', './migration_output')
    
    def get_max_call_depth(self) -> int:
        """获取最大调用链深度"""
        return self.get('analysis.max_call_depth', 6)
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.get('logging.level', 'INFO')
    
    def _get_default_maven_repo(self) -> str:
        """获取默认Maven仓库路径"""
        # 常见的Maven仓库位置
        possible_paths = [
            Path.home() / ".m2" / "repository",  # 默认位置
            Path("D:/Program Files/Apache/apache-maven-repository"),  # Windows常见位置
            Path("apache-maven-repository"),  # 项目目录下
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # 如果都找不到，返回默认路径
        return str(Path.home() / ".m2" / "repository")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'maven': {
                'repository_path': self._get_default_maven_repo(),
                'settings_file': '',
                'enable_dependency_analysis': True
            },
            'java': {
                'java_home': os.getenv('JAVA_HOME', ''),
                'jdt_lib_dir': './lib/jdt'
            },
            'analysis': {
                'max_call_depth': 6
            },
            'output': {
                'dir': './migration_output'
            },
            'logging': {
                'level': 'INFO'
            }
        }
    
    def save_config(self, config_data: Dict[str, Any] = None):
        """保存配置到文件"""
        if config_data is None:
            config_data = self._config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def update_config(self, key_path: str, value: Any):
        """更新配置值"""
        if self._config is None:
            self.load_config()
        
        keys = key_path.split('.')
        config = self._config
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        
        # 保存配置
        self.save_config()


# 全局配置实例
_config_loader = None

def get_config() -> ConfigLoader:
    """获取全局配置实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

def reload_config():
    """重新加载配置"""
    global _config_loader
    _config_loader = None
    return get_config()


def test_config_loader():
    """测试配置加载器"""
    print("🧪 测试配置加载器")
    print("=" * 40)
    
    config = get_config()
    
    print(f"Maven仓库路径: {config.get_maven_repository_path()}")
    print(f"Java Home: {config.get_java_home()}")
    print(f"JDT库目录: {config.get_jdt_lib_dir()}")
    print(f"输出目录: {config.get_output_dir()}")
    print(f"最大调用深度: {config.get_max_call_depth()}")
    print(f"日志级别: {config.get_log_level()}")
    print(f"Maven依赖分析: {'启用' if config.is_maven_dependency_analysis_enabled() else '禁用'}")
    
    # 测试获取不存在的配置
    print(f"不存在的配置: {config.get('non.existent.key', '默认值')}")


if __name__ == "__main__":
    test_config_loader()