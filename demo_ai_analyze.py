#!/usr/bin/env python3
"""
AI分析功能演示脚本
"""

import os
import sys
from pathlib import Path

def demo_ai_analyze():
    """演示AI分析功能的完整流程"""
    
    print("🎯 AI分析功能演示")
    print("=" * 60)
    
    # 检查是否有现有的调用树文件
    output_dir = "./migration_output"
    
    print(f"📁 检查输出目录: {output_dir}")
    if not os.path.exists(output_dir):
        print(f"📁 创建输出目录: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    # 列出现有的调用树文件
    call_tree_files = []
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            if file.startswith("deep_call_tree_") and file.endswith("_jdt.md"):
                call_tree_files.append(file)
    
    if call_tree_files:
        print(f"\n📋 发现 {len(call_tree_files)} 个调用树文件:")
        for i, file in enumerate(call_tree_files, 1):
            # 从文件名提取接口路径
            endpoint = file.replace("deep_call_tree_", "").replace("_jdt.md", "").replace("_", "/")
            print(f"  {i}. {endpoint} -> {file}")
        
        print(f"\n🤖 你可以使用以下命令进行AI分析:")
        for file in call_tree_files[:3]:  # 只显示前3个
            endpoint = file.replace("deep_call_tree_", "").replace("_jdt.md", "").replace("_", "/")
            print(f"  python main.py --ai-analyze {endpoint} --output {output_dir}")
    else:
        print(f"\n❌ 未找到调用树文件")
        print(f"📋 请先运行以下命令生成调用树:")
        print(f"  1. 分析项目: python main.py --single <项目路径> --output {output_dir}")
        print(f"  2. 生成调用树: python main.py --call-tree <接口路径> --output {output_dir}")
        print(f"  3. AI分析: python main.py --ai-analyze <接口路径> --output {output_dir}")
    
    print(f"\n📖 详细使用说明请查看: ai_analyze_usage.md")
    
    # 检查AI模块是否可用
    print(f"\n🔍 检查AI模块可用性...")
    try:
        from ai_module import AIManager
        from ai_module.providers.ollama_provider import OllamaProvider
        print("✅ AI模块导入成功")
        
        # 尝试初始化AI管理器
        ai_manager = AIManager()
        ollama_provider = OllamaProvider()
        
        if ai_manager.register_provider(ollama_provider, set_as_default=True):
            print("✅ AI服务可用")
        else:
            print("⚠️  AI服务不可用，请检查Ollama是否运行")
            
    except ImportError as e:
        print(f"❌ AI模块不可用: {e}")
        print("请确保ai_module已正确安装")
    except Exception as e:
        print(f"⚠️  AI服务检查失败: {e}")
    
    print(f"\n✅ 演示完成")

def show_help():
    """显示帮助信息"""
    print("🆘 AI分析功能帮助")
    print("=" * 60)
    
    print("📋 新增参数:")
    print("  --ai-analyze <接口路径>  AI分析模式：提取接口代码并使用AI进行分析")
    print("")
    
    print("📋 使用流程:")
    print("  1. python main.py --single <项目路径>")
    print("  2. python main.py --call-tree <接口路径>")
    print("  3. python main.py --ai-analyze <接口路径>")
    print("")
    
    print("📋 功能特点:")
    print("  ✅ 执行--extract-code的所有逻辑")
    print("  ✅ 显示提取文件的前20行")
    print("  ✅ 使用AI进行深度代码分析")
    print("  ✅ 生成详细的分析报告")
    print("")
    
    print("📋 输出文件:")
    print("  - java_code_<接口名>_jdt.md  (提取的Java代码)")
    print("  - ai_analysis_<接口名>.md   (AI分析报告)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_help()
    else:
        demo_ai_analyze()