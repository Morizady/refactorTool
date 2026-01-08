#!/usr/bin/env python3
"""
验证Maven配置
快速验证Maven仓库配置是否正确
"""

from config_loader import get_config
from maven_dependency_analyzer import MavenDependencyAnalyzer
from pathlib import Path

def verify_maven_config():
    """验证Maven配置"""
    print("🔍 验证Maven配置")
    print("=" * 40)
    
    # 加载配置
    config = get_config()
    
    # 显示配置信息
    repo_path = config.get_maven_repository_path()
    print(f"📁 配置的Maven仓库路径: {repo_path}")
    
    # 检查路径是否存在
    repo_path_obj = Path(repo_path)
    if repo_path_obj.exists():
        print("✅ Maven仓库路径存在")
        
        # 显示一些统计信息
        subdirs = [d for d in repo_path_obj.iterdir() if d.is_dir()]
        print(f"📊 仓库包含 {len(subdirs)} 个组织目录")
        
        # 显示前几个目录作为示例
        if subdirs:
            print("📋 示例目录:")
            for subdir in subdirs[:5]:
                print(f"  - {subdir.name}")
            if len(subdirs) > 5:
                print(f"  ... 还有 {len(subdirs) - 5} 个目录")
    else:
        print("❌ Maven仓库路径不存在")
        print("请检查config.yml中的maven.repository_path配置")
        return False
    
    # 测试Maven分析器
    print(f"\n🧪 测试Maven分析器")
    try:
        analyzer = MavenDependencyAnalyzer()
        print("✅ Maven分析器初始化成功")
        print(f"📁 使用的仓库路径: {analyzer.maven_repo_path}")
        return True
    except Exception as e:
        print(f"❌ Maven分析器初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = verify_maven_config()
    if success:
        print(f"\n🎉 Maven配置验证成功！")
        print(f"现在可以使用Maven依赖分析功能了。")
    else:
        print(f"\n⚠️ Maven配置验证失败！")
        print(f"请检查config.yml中的配置并确保Maven仓库路径正确。")