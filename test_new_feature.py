#!/usr/bin/env python3
"""
测试新增的接口查看功能
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🧪 测试: {description}")
    print(f"💻 命令: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout:
                # 只显示前500个字符避免输出过长
                output = result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
                print("输出:")
                print(output)
        else:
            print("❌ 执行失败")
            if result.stderr:
                print("错误:")
                print(result.stderr[:500])
    except subprocess.TimeoutExpired:
        print("⏰ 执行超时")
    except Exception as e:
        print(f"❌ 执行异常: {e}")

def main():
    """主测试函数"""
    print("🚀 开始测试新增的接口查看功能")
    
    # 检查分析文件是否存在
    analysis_file = "./migration_output/endpoint_analysis.json"
    if not os.path.exists(analysis_file):
        print(f"\n⚠️  分析文件不存在: {analysis_file}")
        print("需要先运行单项目分析生成数据...")
        
        # 运行单项目分析
        run_command(
            "python main.py --single test_projects/sky-take-out",
            "运行单项目分析生成数据"
        )
    
    # 测试帮助信息
    run_command(
        "python main.py --help",
        "查看帮助信息"
    )
    
    # 测试接口查看功能
    test_cases = [
        ("/admin/category/page", "查看分页查询接口"),
        ("/admin/employee/login", "查看登录接口"),
        ("upload", "模糊匹配查看上传接口"),
        ("nonexistent", "测试不存在的接口"),
    ]
    
    for endpoint, description in test_cases:
        run_command(
            f'python main.py --show-endpoint "{endpoint}"',
            description
        )
    
    print(f"\n{'='*60}")
    print("🎉 所有测试完成!")
    print("📖 查看详细使用说明: endpoint_viewer_usage.md")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()