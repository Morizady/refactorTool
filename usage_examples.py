#!/usr/bin/env python3
"""
使用示例脚本 - 展示如何使用接口分析工具
"""

import os
import subprocess
import sys

def print_header(title):
    """打印标题"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def run_example(description, command):
    """运行示例命令"""
    print(f"\n📋 {description}")
    print(f"💻 命令: {command}")
    print("-" * 40)
    
    # 询问用户是否要运行
    response = input("是否运行此示例? (y/n): ").lower().strip()
    if response == 'y' or response == 'yes':
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 运行成功!")
                if result.stdout:
                    print("输出:")
                    print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            else:
                print("❌ 运行失败!")
                if result.stderr:
                    print("错误:")
                    print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
        except Exception as e:
            print(f"❌ 执行错误: {e}")
    else:
        print("⏭️ 跳过此示例")

def main():
    """主函数"""
    print_header("接口分析工具使用示例")
    
    print("""
这个工具支持两种模式：
1. 单项目分析模式 - 分析一个项目的接口结构
2. 迁移分析模式 - 对比分析新旧两个项目的接口

让我们通过一些示例来了解如何使用这个工具。
    """)
    
    # 检查测试项目是否存在
    if not os.path.exists("test_projects"):
        print("❌ 测试项目目录不存在，请确保在正确的目录下运行此脚本")
        return
    
    print_header("单项目分析模式示例")
    
    # 示例1：基本单项目分析
    run_example(
        "基本单项目分析 - 分析新项目的接口结构",
        "python main_single.py --single test_projects/new_project"
    )
    
    # 示例2：详细单项目分析
    run_example(
        "详细单项目分析 - 显示完整的分析信息",
        "python main_single.py --single test_projects/new_project --verbose"
    )
    
    # 示例3：分析旧项目
    run_example(
        "分析旧项目 - 了解旧系统的接口结构",
        "python main_single.py --single test_projects/old_project --verbose"
    )
    
    print_header("迁移分析模式示例")
    
    # 示例4：基本迁移分析
    run_example(
        "基本迁移分析 - 对比新旧项目接口",
        "python main_single.py --migrate --old test_projects/old_project --new test_projects/new_project"
    )
    
    # 示例5：详细迁移分析
    run_example(
        "详细迁移分析 - 显示完整的匹配和分析信息",
        "python main_single.py --migrate --old test_projects/old_project --new test_projects/new_project --verbose"
    )
    
    print_header("输出文件说明")
    
    print("""
分析完成后，工具会在输出目录生成以下文件：

单项目模式：
📄 endpoints.json - 提取的接口信息
📄 endpoint_analysis.json - 详细分析结果
📄 analysis_report.md - 人类可读的分析报告

迁移模式：
📄 old_endpoints.json - 旧项目接口
📄 new_endpoints.json - 新项目接口
📄 matched_pairs.json - 匹配的接口对
📄 generated_code.json - AI生成的代码（如果启用）
    """)
    
    print_header("自定义使用")
    
    print("""
你也可以分析自己的项目：

单项目分析：
python main_single.py --single /path/to/your/project --verbose

迁移分析：
python main_single.py --migrate --old /path/to/old/project --new /path/to/new/project --verbose

自定义输出目录：
python main_single.py --single /path/to/project --output ./my_analysis

更多选项请查看帮助：
python main_single.py --help
    """)
    
    print_header("完成")
    print("感谢使用接口分析工具！")
    print("如有问题，请查看 README_SINGLE_PROJECT.md 文档")

if __name__ == "__main__":
    main()