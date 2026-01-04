#!/usr/bin/env python3
"""
JDT深度调用链分析使用示例
演示如何使用新的深度调用树分析和方法映射功能
"""

import os
import sys
from pathlib import Path

def example_analyze_sheetmerge_endpoint():
    """示例：分析SheetMerge接口的深度调用链"""
    print("📋 示例：分析 /sheetmerge/merge 接口")
    print("=" * 50)
    
    project_path = "test_projects/sc_pcc_business"
    
    if not os.path.exists(project_path):
        print(f"❌ 项目路径不存在: {project_path}")
        print("请确保测试项目存在")
        return
    
    try:
        from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer
        
        # 1. 初始化分析器
        print("🏗️ 初始化JDT深度分析器...")
        analyzer = JDTDeepCallChainAnalyzer(project_path)
        
        # 2. 分析目标接口
        controller_file = f"{project_path}/src/main/java/com/unicom/microserv/cs/pcc/core/sheetmerge/controller/SheetMergeController.java"
        method_name = "merge"
        
        print(f"🔍 分析接口方法: {method_name}")
        print(f"📁 文件路径: {Path(controller_file).name}")
        
        # 3. 执行深度调用树分析
        call_tree = analyzer.analyze_deep_call_tree(
            controller_file,
            method_name,
            max_depth=6  # 设置较深的分析深度
        )
        
        if not call_tree:
            print("❌ 调用树分析失败")
            return
        
        # 4. 显示分析结果
        print("\n📊 分析结果:")
        print(f"  - 根方法: {call_tree.class_name}.{call_tree.method_name}()")
        print(f"  - 参数: {call_tree.parameters}")
        print(f"  - 返回类型: {call_tree.return_type}")
        print(f"  - 直接子调用: {len(call_tree.children)}")
        
        # 5. 显示方法映射
        if analyzer.method_mappings:
            print(f"\n📋 方法映射 ({len(analyzer.method_mappings)} 个):")
            for i, mapping in enumerate(analyzer.method_mappings, 1):
                print(f"  {i}. 接口调用: {mapping.interface_call}")
                print(f"     实现调用: {mapping.implementation_call}")
                print(f"     调用类型: {mapping.call_type}")
                print(f"     Import: {mapping.import_statement}")
                print(f"     位置: {Path(mapping.file_path).name}:{mapping.line_number}")
                print()
                
                if i >= 5:  # 只显示前5个
                    print(f"     ... 还有 {len(analyzer.method_mappings) - 5} 个映射")
                    break
        
        # 6. 生成详细报告
        print("📝 生成详细报告...")
        output_dir = "./example_output"
        os.makedirs(output_dir, exist_ok=True)
        
        report_file = analyzer.generate_call_tree_report(
            call_tree,
            "POST /sheetmerge/merge",
            output_dir
        )
        
        print(f"✅ 报告已生成: {report_file}")
        
        # 7. 显示生成的文件
        output_path = Path(output_dir)
        generated_files = list(output_path.glob("*merge*"))
        
        print(f"\n📁 生成的文件:")
        for file in generated_files:
            size_kb = file.stat().st_size / 1024
            print(f"  - {file.name} ({size_kb:.1f}KB)")
        
        # 8. 显示关键发现
        print(f"\n🔍 关键发现:")
        
        # 统计调用类型
        call_types = {}
        for mapping in analyzer.method_mappings:
            call_type = mapping.call_type
            call_types[call_type] = call_types.get(call_type, 0) + 1
        
        for call_type, count in call_types.items():
            print(f"  - {call_type} 调用: {count} 个")
        
        # 统计涉及的包
        packages = set()
        for mapping in analyzer.method_mappings:
            if "." in mapping.import_statement:
                package = ".".join(mapping.import_statement.split(".")[1:-1])
                packages.add(package)
        
        print(f"  - 涉及包: {len(packages)} 个")
        for package in sorted(packages)[:3]:
            print(f"    -> {package}")
        if len(packages) > 3:
            print(f"    -> ... 还有 {len(packages) - 3} 个包")
        
        analyzer.shutdown()
        
        print(f"\n🎉 示例分析完成！")
        print(f"📋 查看详细报告: {report_file}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()

def example_compare_parsing_methods():
    """示例：比较不同解析方法的结果"""
    print("\n📋 示例：比较解析方法")
    print("=" * 30)
    
    # 这里可以添加比较不同解析方法的代码
    print("💡 提示：可以使用以下命令比较不同解析方法:")
    print("  python main.py --call-tree /sheetmerge/merge --parse-method regex")
    print("  python main.py --call-tree /sheetmerge/merge --parse-method ast")
    print("  python main.py --call-tree /sheetmerge/merge --parse-method jdt")

def example_batch_analysis():
    """示例：批量分析多个接口"""
    print("\n📋 示例：批量分析")
    print("=" * 20)
    
    print("💡 提示：对于批量分析，建议:")
    print("1. 先运行项目分析: python main.py --single /path/to/project")
    print("2. 然后分析各个接口: python main.py --call-tree /api/endpoint --parse-method jdt")
    print("3. 使用脚本自动化批量处理")

def main():
    """主函数"""
    print("🚀 JDT深度调用链分析使用示例")
    print("=" * 50)
    
    examples = [
        ("分析SheetMerge接口", example_analyze_sheetmerge_endpoint),
        ("比较解析方法", example_compare_parsing_methods),
        ("批量分析提示", example_batch_analysis)
    ]
    
    for example_name, example_func in examples:
        print(f"\n📋 {example_name}:")
        try:
            example_func()
        except Exception as e:
            print(f"❌ 示例执行失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 示例演示完成")
    print("\n💡 更多用法:")
    print("  - 查看配置: cat config.yml")
    print("  - 测试环境: python test_jdt_environment.py")
    print("  - 深度测试: python test_jdt_deep_analysis.py")
    print("  - 完整分析: python main.py --single /path/to/project --parse-method jdt")

if __name__ == "__main__":
    main()