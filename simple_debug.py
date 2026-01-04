#!/usr/bin/env python3
"""
简单调试脚本
"""

import os
from jdt_parser import JDTParser

def simple_debug():
    """简单调试"""
    print("🔍 简单调试")
    print("=" * 30)
    
    parser = JDTParser()
    
    # 目标文件
    target_file = "test_projects/sc_pcc_business/src/main/java/com/unicom/microserv/cs/pcc/core/sheetmerge/controller/SheetMergeController.java"
    
    print(f"📁 解析文件: {os.path.basename(target_file)}")
    
    # 解析文件
    java_class = parser.parse_java_file(target_file)
    
    if not java_class:
        print("❌ 解析失败")
        parser.shutdown()
        return
    
    print(f"✅ 解析成功: {java_class.name}")
    print(f"   包名: {java_class.package}")
    print(f"   方法数量: {len(java_class.methods)}")
    
    # 查找merge方法
    merge_method = None
    for method in java_class.methods:
        print(f"   - {method.name}({', '.join(method.parameters)})")
        if method.name == "merge":
            merge_method = method
    
    if merge_method:
        print(f"\n🎯 merge方法详情:")
        print(f"   方法调用数: {len(merge_method.method_calls)}")
        
        if merge_method.method_calls:
            print(f"   方法调用:")
            for i, call in enumerate(merge_method.method_calls, 1):
                obj = call.get('object', '')
                method_name = call.get('method', '')
                print(f"     {i}. {obj}.{method_name}()")
        else:
            print("   ⚠️ 没有方法调用")
    else:
        print("❌ 未找到merge方法")
    
    parser.shutdown()

if __name__ == "__main__":
    simple_debug()