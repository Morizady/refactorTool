#!/usr/bin/env python3
"""
调试方法查找问题
"""

import os
from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer

def debug_method_finding():
    """调试方法查找问题"""
    print("🔍 调试方法查找问题")
    print("=" * 50)
    
    # 初始化分析器
    project_path = "test_projects/sc_pcc_business"
    analyzer = JDTDeepCallChainAnalyzer(project_path)
    
    # 解析项目
    print(f"📁 解析项目: {project_path}")
    
    success = analyzer.initialize_project()
    if not success:
        print("❌ 项目初始化失败")
        return
    
    print(f"✅ 项目初始化成功，共解析 {len(analyzer.java_classes)} 个类")
    
    # 目标文件和方法
    target_file = "test_projects/sc_pcc_business/src/main/java/com/unicom/microserv/cs/pcc/core/sheetmerge/controller/SheetMergeController.java"
    target_method = "merge"
    
    print(f"\n🎯 目标文件: {target_file}")
    print(f"🎯 目标方法: {target_method}")
    
    # 检查文件是否存在于解析结果中
    print(f"\n📋 检查文件映射:")
    
    # 标准化路径
    normalized_target = os.path.normpath(target_file)
    print(f"   标准化目标路径: {normalized_target}")
    
    found_class = None
    for class_key, java_class in analyzer.java_classes.items():
        normalized_class_path = os.path.normpath(java_class.file_path)
        if normalized_class_path == normalized_target:
            found_class = java_class
            print(f"✅ 找到匹配的类: {class_key}")
            print(f"   类名: {java_class.name}")
            print(f"   包名: {java_class.package}")
            print(f"   文件路径: {java_class.file_path}")
            print(f"   方法数量: {len(java_class.methods)}")
            break
    
    if not found_class:
        print("❌ 未找到匹配的类")
        print("\n📋 所有解析的类文件路径:")
        for i, (class_key, java_class) in enumerate(analyzer.java_classes.items()):
            if i < 10:  # 只显示前10个
                print(f"   {i+1}. {class_key} -> {java_class.file_path}")
            elif i == 10:
                print(f"   ... 还有 {len(analyzer.java_classes) - 10} 个类")
                break
        return
    
    # 检查方法
    print(f"\n🔍 检查方法:")
    target_method_obj = None
    for method in found_class.methods:
        print(f"   - {method.name}({', '.join(method.parameters)})")
        if method.name == target_method:
            target_method_obj = method
    
    if not target_method_obj:
        print(f"❌ 未找到目标方法: {target_method}")
        return
    
    print(f"✅ 找到目标方法: {target_method_obj.name}")
    print(f"   参数: {target_method_obj.parameters}")
    print(f"   返回类型: {target_method_obj.return_type}")
    print(f"   方法调用数: {len(target_method_obj.method_calls)}")
    
    # 显示方法调用
    if target_method_obj.method_calls:
        print(f"\n📞 方法调用详情:")
        for i, call in enumerate(target_method_obj.method_calls, 1):
            print(f"   {i}. {call.get('object', '')}.{call['method']}()")
            print(f"      - 参数数量: {call.get('arguments', 0)}")
            print(f"      - 调用类型: {call.get('type', 'unknown')}")
    
    # 测试_find_method_in_file方法
    print(f"\n🧪 测试_find_method_in_file方法:")
    found_method = analyzer._find_method_in_file(target_file, target_method)
    if found_method:
        print(f"✅ _find_method_in_file找到方法: {found_method.name}")
        print(f"   方法调用数: {len(found_method.method_calls)}")
    else:
        print(f"❌ _find_method_in_file未找到方法")
    
    # 测试_find_class_by_file方法
    print(f"\n🧪 测试_find_class_by_file方法:")
    found_class_test = analyzer._find_class_by_file(target_file)
    if found_class_test:
        print(f"✅ _find_class_by_file找到类: {found_class_test.name}")
        print(f"   文件路径: {found_class_test.file_path}")
    else:
        print(f"❌ _find_class_by_file未找到类")
    
    analyzer.shutdown()

if __name__ == "__main__":
    debug_method_finding()