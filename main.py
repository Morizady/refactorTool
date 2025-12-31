#!/usr/bin/env python3
"""
新旧系统接口映射与迁移工具 - 支持单项目分析
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse

from endpoint_extractor import EndpointExtractor
from equivalence_matcher import EquivalenceMatcher
from call_chain_analyzer import CallChainAnalyzer
from sql_mapper_analyzer import SQLMapperAnalyzer
from ai_generator import AIGenerator

class DeepCallChainAnalyzer:
    """深度调用链分析器 - 增强版"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analyzed_methods = set()  # 避免循环分析
        self.call_tree = {}
        self.interface_implementations = {}  # 接口实现映射
        self.class_hierarchy = {}  # 类继承关系
        self._build_class_hierarchy()
        
    def _build_class_hierarchy(self):
        """构建类继承关系和接口实现映射"""
        print("🔍 构建类继承关系...")
        
        java_files = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        
        total_files = len(java_files)
        print(f"📁 找到 {total_files} 个Java文件，开始分析...")
        
        for i, file_path in enumerate(java_files, 1):
            if i % 50 == 0 or i == total_files:  # 每50个文件或最后一个文件打印进度
                print(f"  📊 分析进度: {i}/{total_files} ({i/total_files*100:.1f}%)")
            self._analyze_class_structure(file_path)
        
        interface_count = len(self.interface_implementations)
        class_count = len(self.class_hierarchy)
        print(f"✅ 类继承关系构建完成: {class_count} 个类, {interface_count} 个接口")
    
    def _analyze_class_structure(self, file_path: str):
        """分析单个Java文件的类结构"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            
            # 查找类定义和接口实现
            class_pattern = r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
            interface_pattern = r'(?:public\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?'
            
            class_matches = re.finditer(class_pattern, content)
            for match in class_matches:
                class_name = match.group(1)
                parent_class = match.group(2)
                interfaces = match.group(3)
                
                self.class_hierarchy[class_name] = {
                    'file': file_path,
                    'parent': parent_class,
                    'interfaces': []
                }
                
                if interfaces:
                    interface_list = [i.strip() for i in interfaces.split(',')]
                    self.class_hierarchy[class_name]['interfaces'] = interface_list
                    
                    # 建立接口到实现类的映射
                    for interface in interface_list:
                        if interface not in self.interface_implementations:
                            self.interface_implementations[interface] = []
                        self.interface_implementations[interface].append({
                            'class': class_name,
                            'file': file_path
                        })
            
            # 查找接口定义
            interface_matches = re.finditer(interface_pattern, content)
            for match in interface_matches:
                interface_name = match.group(1)
                parent_interfaces = match.group(2)
                
                if interface_name not in self.interface_implementations:
                    self.interface_implementations[interface_name] = []
                    
        except Exception as e:
            pass  # 忽略解析错误
    
    def analyze_method_calls(self, file_path: str, method_name: str, depth: int = 0, max_depth: int = 4) -> Dict:
        """深度分析方法调用 - 增强版"""
        if depth > max_depth:
            return {"note": "达到最大深度限制"}
        
        # 使用更精确的循环检测标识符
        method_key = f"{file_path}:{method_name}:{depth}"
        if method_key in self.analyzed_methods:
            return {"note": "已分析过，避免循环引用"}
        
        # 打印当前分析进度
        indent = "  " * depth
        print(f"{indent}🔍 分析方法: {method_name} (深度: {depth})")
        
        self.analyzed_methods.add(method_key)
        
        try:
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找方法定义并提取方法调用
            method_calls = self._extract_method_calls_from_content(content, method_name)
            
            # 去重和过滤方法调用
            unique_calls = self._deduplicate_method_calls(method_calls)
            print(f"{indent}  📋 找到 {len(method_calls)} 个方法调用，去重后 {len(unique_calls)} 个")
            
            # 递归分析每个调用
            detailed_calls = []
            for i, call in enumerate(unique_calls, 1):
                if len(unique_calls) > 5 and i % 5 == 0:  # 每5个调用打印一次进度
                    print(f"{indent}  📊 处理调用进度: {i}/{len(unique_calls)}")
                
                call_detail = {
                    "method": call["method"],
                    "object": call.get("object", ""),
                    "line": call.get("line", 0),
                    "arguments": call.get("arguments", 0),
                    "type": call.get("type", "instance")
                }
                
                # 查找方法实现
                implementations = self._find_method_implementations(call, file_path)
                
                if implementations:
                    call_detail["implementations"] = []
                    
                    # 对每个实现进行递归分析
                    for impl in implementations:
                        impl_detail = {
                            "file": impl["file"],
                            "class": impl.get("class", ""),
                            "type": impl.get("type", "concrete")
                        }
                        
                        # 递归分析实现（避免对标准库和已知类型进行深度分析）
                        if (impl["file"] and os.path.exists(impl["file"]) and 
                            depth < max_depth and 
                            impl.get("type") not in ["standard_library", "enum_class"]):
                            
                            impl_detail["sub_calls"] = self.analyze_method_calls(
                                impl["file"], call["method"], depth + 1, max_depth
                            )
                        
                        call_detail["implementations"].append(impl_detail)
                else:
                    # 如果没找到实现，尝试原有的查找方式
                    target_file = self._find_method_implementation_legacy(call, file_path)
                    if target_file and depth < max_depth:
                        call_detail["implementation"] = target_file
                        call_detail["sub_calls"] = self.analyze_method_calls(
                            target_file, call["method"], depth + 1, max_depth
                        )
                
                detailed_calls.append(call_detail)
            
            print(f"{indent}✅ 方法 {method_name} 分析完成")
            return {
                "file": file_path,
                "method": method_name,
                "calls": detailed_calls,
                "depth": depth
            }
            
        except Exception as e:
            print(f"{indent}❌ 分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def _extract_method_calls_from_content(self, content: str, method_name: str) -> List[Dict]:
        """从内容中提取方法调用 - 增强版"""
        calls = []
        lines = content.split('\n')
        
        # 查找方法定义
        method_start = -1
        method_end = -1
        brace_count = 0
        in_method = False
        
        for i, line in enumerate(lines):
            # 更精确的方法定义匹配
            if self._is_method_definition(line, method_name):
                method_start = i
                in_method = True
                brace_count = 0
                # 计算方法定义行的大括号
                brace_count += line.count('{') - line.count('}')
                continue
            
            if in_method:
                # 计算大括号
                brace_count += line.count('{') - line.count('}')
                
                # 提取方法调用（排除方法定义行）
                method_calls = self._parse_method_calls_in_line_enhanced(line, i + 1)
                calls.extend(method_calls)
                
                # 如果大括号平衡，说明方法结束
                if brace_count == 0 and i > method_start:
                    method_end = i
                    break
        
        return calls
    
    def _is_method_definition(self, line: str, method_name: str) -> bool:
        """判断是否是方法定义行"""
        import re
        
        # 更精确的方法定义模式
        # 必须以访问修饰符开头，且方法名前有返回类型
        patterns = [
            # public/private/protected + 可选static + 返回类型 + 方法名 + (
            rf'^\s*(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]*>)?\s+)+{re.escape(method_name)}\s*\(',
            # @注解后的方法定义
            rf'^\s*(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]*>)?\s+)*{re.escape(method_name)}\s*\(',
        ]
        
        # 排除明显不是方法定义的情况
        exclude_patterns = [
            r'^\s*\w+\.',  # 以对象.开头的调用
            r'^\s*return\s+',  # return语句
            r'^\s*if\s*\(',  # if语句
            r'^\s*while\s*\(',  # while语句
            r'^\s*for\s*\(',  # for语句
        ]
        
        # 先检查排除模式
        for exclude_pattern in exclude_patterns:
            if re.search(exclude_pattern, line):
                return False
        
        # 再检查方法定义模式
        for pattern in patterns:
            if re.search(pattern, line):
                return True
        
        return False
        return False
    
    def _parse_method_calls_in_line_enhanced(self, line: str, line_number: int) -> List[Dict]:
        """解析单行中的方法调用 - 增强版"""
        calls = []
        import re
        
        # 去除注释
        line_clean = re.sub(r'//.*$', '', line)
        line_clean = re.sub(r'/\*.*?\*/', '', line_clean)
        
        # 1. 枚举常量调用 EnumClass.CONSTANT.method()
        enum_pattern = r'([A-Z]\w*)\.([A-Z_]+)\.(\w+)\s*\(([^)]*)\)'
        enum_matches = re.finditer(enum_pattern, line_clean)
        for match in enum_matches:
            enum_class = match.group(1)
            enum_constant = match.group(2)
            method = match.group(3)
            args = match.group(4)
            
            # 添加枚举常量调用
            calls.append({
                "object": enum_constant,  # 使用常量名作为对象
                "method": method,
                "line": line_number,
                "arguments": self._count_arguments_from_string(args),
                "type": "enum_constant",
                "enum_class": enum_class  # 保存枚举类信息
            })
        
        # 2. 链式调用 object.method1().method2()
        chain_pattern = r'(\w+)(?:\.(\w+)\s*\([^)]*\))+(?:\.(\w+)\s*\([^)]*\))*'
        chain_matches = re.finditer(chain_pattern, line_clean)
        for match in chain_matches:
            # 解析链式调用中的每个方法
            chain_part = match.group(0)
            method_calls_in_chain = re.findall(r'\.(\w+)\s*\(([^)]*)\)', chain_part)
            
            base_object = match.group(1)
            for i, (method, args) in enumerate(method_calls_in_chain):
                calls.append({
                    "object": base_object if i == 0 else "chained",
                    "method": method,
                    "line": line_number,
                    "arguments": self._count_arguments_from_string(args),
                    "type": "chain"
                })
        
        # 3. 静态方法调用 Class.method()
        static_pattern = r'([A-Z]\w*)\.(\w+)\s*\(([^)]*)\)'
        static_matches = re.finditer(static_pattern, line_clean)
        for match in static_matches:
            # 避免重复添加已经在枚举调用中处理的
            if not any(call.get("enum_class") == match.group(1) and call["method"] == match.group(2) 
                      and call["line"] == line_number for call in calls):
                calls.append({
                    "object": match.group(1),
                    "method": match.group(2),
                    "line": line_number,
                    "arguments": self._count_arguments_from_string(match.group(3)),
                    "type": "static"
                })
        
        # 4. 实例方法调用 object.method()
        instance_pattern = r'(\w+)\.(\w+)\s*\(([^)]*)\)'
        instance_matches = re.finditer(instance_pattern, line_clean)
        for match in instance_matches:
            # 避免重复添加已经在链式调用中处理的
            if not any(call["object"] == match.group(1) and call["method"] == match.group(2) 
                      and call["line"] == line_number for call in calls):
                calls.append({
                    "object": match.group(1),
                    "method": match.group(2),
                    "line": line_number,
                    "arguments": self._count_arguments_from_string(match.group(3)),
                    "type": "instance"
                })
        
        # 5. 构造函数调用 new Class()
        constructor_pattern = r'new\s+([A-Z]\w*)\s*\(([^)]*)\)'
        constructor_matches = re.finditer(constructor_pattern, line_clean)
        for match in constructor_matches:
            calls.append({
                "object": match.group(1),
                "method": "<init>",
                "line": line_number,
                "arguments": self._count_arguments_from_string(match.group(2)),
                "type": "constructor"
            })
        
        # 6. 直接方法调用 method()
        direct_pattern = r'(?<!\w)(\w+)\s*\(([^)]*)\)'
        direct_matches = re.finditer(direct_pattern, line_clean)
        for match in direct_matches:
            method_name = match.group(1)
            # 排除关键字、已匹配的方法和构造函数
            if (method_name not in ['if', 'for', 'while', 'switch', 'catch', 'new', 'return'] and
                not any(call["method"] == method_name and call["line"] == line_number for call in calls)):
                calls.append({
                    "method": method_name,
                    "line": line_number,
                    "arguments": self._count_arguments_from_string(match.group(2)),
                    "type": "direct"
                })
        
        return calls
    
    def _deduplicate_method_calls(self, method_calls: List[Dict]) -> List[Dict]:
        """去重方法调用，避免同一个调用被重复识别"""
        # 第一步：预处理，统一构造函数的表示
        processed_calls = []
        
        for call in method_calls:
            obj = call.get("object", "")
            method = call.get("method", "")
            call_type = call.get("type", "instance")
            line = call.get("line", 0)
            
            # 统一所有构造函数调用的表示
            is_constructor = False
            
            if method == "<init>":
                # new ClassName() -> ClassName.<init>()
                is_constructor = True
                target_class = obj
            elif call_type == "direct" and obj and method == obj:
                # ClassName.ClassName() 形式
                is_constructor = True
                target_class = obj
            elif call_type == "direct" and not obj and method and method[0].isupper():
                # ServiceResult() 形式（无对象名的构造函数调用）
                is_constructor = True
                target_class = method
            
            if is_constructor:
                # 统一为 ClassName.ClassName() [构造] 的形式
                call["object"] = target_class
                call["method"] = target_class
                call["type"] = "constructor"
            
            processed_calls.append(call)
        
        # 第二步：基于唯一键去重
        unique_calls = []
        seen_calls = {}
        
        for call in processed_calls:
            obj = call.get("object", "")
            method = call.get("method", "")
            line = call.get("line", 0)
            call_type = call.get("type", "instance")
            
            # 创建唯一键：对象.方法@行号
            unique_key = f"{obj}.{method}@{line}"
            
            if unique_key in seen_calls:
                existing_call = seen_calls[unique_key]
                
                # 定义类型优先级
                type_priority = {
                    "static": 4,
                    "enum_constant": 4,
                    "constructor": 3,
                    "instance": 2,
                    "chain": 2,
                    "direct": 1
                }
                
                current_priority = type_priority.get(call_type, 0)
                existing_priority = type_priority.get(existing_call.get("type"), 0)
                
                if current_priority > existing_priority:
                    # 替换为优先级更高的调用
                    unique_calls = [c for c in unique_calls if c != existing_call]
                    seen_calls[unique_key] = call
                    unique_calls.append(call)
            else:
                seen_calls[unique_key] = call
                unique_calls.append(call)
        
        return unique_calls

    def _count_arguments_from_string(self, args_str: str) -> int:
        """从参数字符串计算参数数量"""
        if not args_str.strip():
            return 0
        
        # 简单的参数计数，考虑嵌套括号
        paren_level = 0
        comma_count = 0
        
        for char in args_str:
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == ',' and paren_level == 0:
                comma_count += 1
        
        return comma_count + 1 if args_str.strip() else 0
    
        seen_calls = set()
        
        for call in method_calls:
            # 创建唯一标识符
            obj = call.get("object", "")
            method = call.get("method", "")
            line = call.get("line", 0)
            call_type = call.get("type", "instance")
            
            # 对于构造函数调用，统一处理
            if method == "<init>":
                method = obj  # 将构造函数调用统一为类名
                call["method"] = method
                call["type"] = "constructor"
            
            # 创建唯一键：对象.方法@行号
            unique_key = f"{obj}.{method}@{line}"
            
            if unique_key not in seen_calls:
                seen_calls.add(unique_key)
                
                # 优先保留更具体的调用类型
                existing_call = None
                for existing in unique_calls:
                    if (existing.get("object") == obj and 
                        existing.get("method") == method and 
                        existing.get("line") == line):
                        existing_call = existing
                        break
                
                if existing_call:
                    # 如果已存在，选择更具体的类型
                    type_priority = {
                        "static": 3,
                        "instance": 2, 
                        "chain": 2,
                        "constructor": 2,
                        "direct": 1,
                        "enum_constant": 3
                    }
                    
                    current_priority = type_priority.get(call_type, 0)
                    existing_priority = type_priority.get(existing_call.get("type"), 0)
                    
                    if current_priority > existing_priority:
                        # 替换为更具体的调用
                        unique_calls.remove(existing_call)
                        unique_calls.append(call)
                else:
                    unique_calls.append(call)
        
        return unique_calls
    
        """从参数字符串计算参数数量"""
        if not args_str.strip():
            return 0
        
        # 简单的参数计数，考虑嵌套括号
        paren_level = 0
        comma_count = 0
        
        for char in args_str:
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == ',' and paren_level == 0:
                comma_count += 1
        
        return comma_count + 1 if args_str.strip() else 0
    
    def _find_method_implementations(self, call: Dict, current_file: str) -> List[Dict]:
        """查找方法的所有实现 - 支持接口和继承"""
        method_name = call["method"]
        object_name = call.get("object", "")
        call_type = call.get("type", "instance")
        enum_class = call.get("enum_class", "")  # 获取枚举类信息
        
        implementations = []
        
        # 1. 处理枚举常量调用 (如 ResultCode.UNAUTHORIZED.getCode())
        if call_type == "enum_constant" and enum_class:
            # 查找枚举类文件
            enum_file = self._find_file_by_name(f"{enum_class}.java")
            if enum_file:
                implementations.append({
                    "file": enum_file,
                    "class": enum_class,
                    "type": "enum_class",
                    "note": f"枚举类: {enum_class}.{object_name}.{method_name}()"
                })
            else:
                # 尝试在项目中查找枚举类
                project_enum_files = self._find_project_class_files(enum_class)
                for file_path, class_name in project_enum_files:
                    implementations.append({
                        "file": file_path,
                        "class": class_name,
                        "type": "enum_class",
                        "note": f"枚举类: {class_name}.{object_name}.{method_name}()"
                    })
            return implementations
        
        # 2. 处理已知的Java标准库
        if self._is_java_standard_library(object_name):
            implementations.append({
                "file": None,
                "class": object_name,
                "type": "standard_library",
                "note": f"Java标准库: {object_name}.{method_name}"
            })
            return implementations
        
        # 3. 查找项目中的实现
        if object_name:
            # 2.1 Spring Service变量名到接口名的映射
            service_class_name = self._resolve_service_class_name(object_name, current_file)
            
            # 2.2 查找直接的类实现
            class_file = self._find_file_by_name(f"{object_name}.java")
            if class_file:
                implementations.append({
                    "file": class_file,
                    "class": object_name,
                    "type": "concrete"
                })
            
            # 2.3 处理常见的项目内部类（如CommonResult、ResultCode等）
            project_class_files = self._find_project_class_files(object_name)
            for file_path, class_name in project_class_files:
                implementations.append({
                    "file": file_path,
                    "class": class_name,
                    "type": "project_class"
                })
            
            # 2.4 如果是Service变量，查找对应的Service接口和实现
            if service_class_name:
                # 查找Service接口
                service_interface_file = self._find_file_by_name(f"{service_class_name}.java")
                if service_interface_file:
                    implementations.append({
                        "file": service_interface_file,
                        "class": service_class_name,
                        "type": "service_interface"
                    })
                
                # 查找ServiceImpl实现类
                impl_class_name = service_class_name + "Impl"
                impl_file = self._find_file_by_name(f"{impl_class_name}.java")
                if impl_file:
                    implementations.append({
                        "file": impl_file,
                        "class": impl_class_name,
                        "type": "service_implementation"
                    })
            
            # 2.5 通用Service接口处理
            if object_name.endswith("Service"):
                # 查找对应的ServiceImpl实现类
                impl_class_name = object_name + "Impl"
                impl_file = self._find_file_by_name(f"{impl_class_name}.java")
                if impl_file:
                    implementations.append({
                        "file": impl_file,
                        "class": impl_class_name,
                        "type": "service_implementation"
                    })
            
            # 2.6 查找接口的所有实现
            if object_name in self.interface_implementations:
                for impl in self.interface_implementations[object_name]:
                    implementations.append({
                        "file": impl["file"],
                        "class": impl["class"],
                        "type": "interface_implementation"
                    })
            
            # 2.7 查找继承关系中的实现
            for class_name, info in self.class_hierarchy.items():
                if info.get("parent") == object_name:
                    implementations.append({
                        "file": info["file"],
                        "class": class_name,
                        "type": "inheritance"
                    })
            
            # 2.8 模糊匹配：查找包含object_name的类
            if not implementations:
                # 尝试查找类似的类名
                similar_files = self._find_similar_class_files(object_name)
                for file_path, class_name in similar_files:
                    implementations.append({
                        "file": file_path,
                        "class": class_name,
                        "type": "similar_match"
                    })
        
        # 3. 在当前文件中查找本地方法
        if call_type == "direct":
            implementations.append({
                "file": current_file,
                "class": "current",
                "type": "local"
            })
        
        return implementations
    
    def _resolve_service_class_name(self, variable_name: str, current_file: str) -> Optional[str]:
        """根据变量名解析Service类名"""
        # 常见的Spring Service变量名模式
        service_mappings = {
            "adminService": "UmsAdminService",
            "roleService": "UmsRoleService", 
            "userService": "UmsUserService",
            "menuService": "UmsMenuService",
            "resourceService": "UmsResourceService",
        }
        
        # 直接映射
        if variable_name in service_mappings:
            return service_mappings[variable_name]
        
        # 模式匹配：xxxService -> XxxService
        if variable_name.endswith("Service"):
            # 将首字母大写
            class_name = variable_name[0].upper() + variable_name[1:]
            return class_name
        
        # 尝试从当前文件中解析@Autowired注解
        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找@Autowired private XxxService xxxService;
            import re
            pattern = rf'@Autowired\s+(?:private\s+)?(\w+Service)\s+{re.escape(variable_name)}\s*;'
            match = re.search(pattern, content)
            if match:
                return match.group(1)
                
        except Exception:
            pass
        
        return None
    
    def _find_method_implementation_legacy(self, call: Dict, current_file: str) -> Optional[str]:
        """原有的方法实现查找逻辑（向后兼容）"""
        method_name = call["method"]
        object_name = call.get("object", "")
        
        # 常见的Java工具类和方法映射
        known_implementations = {
            "System": {
                "currentTimeMillis": None,  # Java标准库
                "out": None
            },
            "JwtUtil": {
                "createJWT": self._find_file_by_name("JwtUtil.java")
            },
            "Jwts": {
                "builder": None,  # 第三方库
                "parser": None
            },
            "SignatureAlgorithm": {
                "HS256": None
            },
            "Date": {
                "<init>": None
            },
            "HashMap": {
                "<init>": None
            }
        }
        
        # 查找已知实现
        if object_name in known_implementations:
            impl = known_implementations[object_name].get(method_name)
            if impl:
                return impl
        
        # 在项目中查找实现
        if object_name:
            class_file = self._find_file_by_name(f"{object_name}.java")
            if class_file:
                return class_file
        
        return None
    
    def _is_java_standard_library(self, class_name: str) -> bool:
        """判断是否是Java标准库类"""
        standard_classes = {
            'System', 'String', 'Integer', 'Long', 'Double', 'Float', 'Boolean',
            'Date', 'Calendar', 'HashMap', 'ArrayList', 'List', 'Map', 'Set',
            'Thread', 'Object', 'Class', 'Math', 'Random'
        }
        return class_name in standard_classes
    
    def _find_file_by_name(self, filename: str) -> Optional[str]:
        """在项目中查找指定文件名的文件"""
        for root, dirs, files in os.walk(self.project_root):
            if filename in files:
                return os.path.join(root, filename)
        return None
    
    def _find_similar_class_files(self, class_name: str) -> List[tuple]:
        """查找相似的类文件，返回(文件路径, 类名)列表"""
        similar_files = []
        
        # 常见的命名模式
        patterns = [
            f"{class_name}Impl.java",      # ServiceImpl模式
            f"{class_name}Implementation.java",  # ServiceImplementation模式
            f"Default{class_name}.java",   # DefaultService模式
            f"{class_name}Bean.java",      # ServiceBean模式
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.java'):
                    # 检查是否匹配任何模式
                    for pattern in patterns:
                        if file == pattern:
                            file_path = os.path.join(root, file)
                            class_name_from_file = file[:-5]  # 去掉.java后缀
                            similar_files.append((file_path, class_name_from_file))
                            break
                    
                    # 检查文件名是否包含目标类名
                    if class_name.lower() in file.lower() and file != f"{class_name}.java":
                        file_path = os.path.join(root, file)
                        class_name_from_file = file[:-5]  # 去掉.java后缀
                        similar_files.append((file_path, class_name_from_file))
        
        return similar_files
    
    def _find_project_class_files(self, class_name: str) -> List[tuple]:
        """查找项目中的类文件，返回(文件路径, 类名)列表"""
        project_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file == f"{class_name}.java":
                    file_path = os.path.join(root, file)
                    project_files.append((file_path, class_name))
        
        return project_files

def generate_call_tree(endpoint_path: str, output_dir: str = "./migration_output"):
    """生成指定接口的深度调用链树"""
    print(f"🚀 开始生成调用链树: {endpoint_path}")
    
    analysis_file = f"{output_dir}/endpoint_analysis.json"
    
    if not os.path.exists(analysis_file):
        print(f"❌ 分析文件不存在: {analysis_file}")
        print("请先运行单项目分析生成分析数据：")
        print("python main.py --single /path/to/project")
        return
    
    # 加载分析数据
    print("📂 正在加载分析数据...")
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        print(f"✅ 成功加载 {len(analysis_data)} 个接口的分析数据")
    except Exception as e:
        print(f"❌ 读取分析文件失败: {e}")
        return
    
    # 查找匹配的接口
    print(f"🔍 正在查找匹配的接口: {endpoint_path}")
    matching_endpoints = []
    for endpoint_data in analysis_data:
        endpoint = endpoint_data['endpoint']
        if endpoint_path in endpoint['path'] or endpoint_path == endpoint['path']:
            matching_endpoints.append(endpoint_data)
    
    if not matching_endpoints:
        print(f"❌ 未找到匹配的接口: {endpoint_path}")
        return
    
    print(f"✅ 找到 {len(matching_endpoints)} 个匹配的接口")
    
    # 选择接口
    if len(matching_endpoints) > 1:
        print(f"🔍 找到 {len(matching_endpoints)} 个匹配的接口:")
        for i, endpoint_data in enumerate(matching_endpoints, 1):
            endpoint = endpoint_data['endpoint']
            print(f"{i}. {endpoint['method']} {endpoint['path']} - {endpoint['name']}")
        
        try:
            choice = int(input("\n请选择要分析的接口 (输入序号): ")) - 1
            if 0 <= choice < len(matching_endpoints):
                selected_endpoint = matching_endpoints[choice]
            else:
                print("❌ 无效的选择")
                return
        except ValueError:
            print("❌ 请输入有效的数字")
            return
    else:
        selected_endpoint = matching_endpoints[0]
    
    # 生成调用树
    print("🌳 开始生成深度调用链树...")
    _generate_call_tree_md(selected_endpoint, output_dir)

def _generate_call_tree_md(endpoint_data: Dict, output_dir: str):
    """生成调用树的Markdown文件"""
    endpoint = endpoint_data['endpoint']
    call_chain = endpoint_data['call_chain']
    
    # 确定项目根目录
    file_path = endpoint['file_path']
    project_root = None
    
    print("📁 正在确定项目根目录...")
    # 尝试找到项目根目录
    path_parts = file_path.split(os.sep)
    for i, part in enumerate(path_parts):
        if part in ['src', 'main', 'java']:
            project_root = os.sep.join(path_parts[:i-2]) if i >= 2 else os.sep.join(path_parts[:i])
            break
    
    if not project_root:
        project_root = os.path.dirname(file_path)
    
    print(f"� 开始深度分:析接口: {endpoint['name']}")
    print(f"📁 项目根目录: {project_root}")
    
    # 创建深度分析器
    print("🏗️  正在初始化深度分析器...")
    analyzer = DeepCallChainAnalyzer(project_root)
    
    # 分析主方法
    print(f"🚀 开始分析主方法: {endpoint['handler']}")
    print("=" * 60)
    main_analysis = analyzer.analyze_method_calls(
        file_path, 
        endpoint['handler'],
        max_depth=4  # 增加深度
    )
    print("=" * 60)
    
    # 生成Markdown内容
    print("📝 正在生成Markdown内容...")
    md_content = _build_call_tree_markdown(endpoint, call_chain, main_analysis)
    
    # 保存到文件
    output_file = f"{output_dir}/call_tree_{endpoint['handler']}.md"
    print(f"💾 正在保存到文件: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 调用树已生成: {output_file}")
    
    # 显示统计信息
    total_calls = _count_total_calls_enhanced(main_analysis.get('calls', []))
    max_depth = _get_max_depth_enhanced(main_analysis.get('calls', []))
    interface_count = _count_interface_implementations(main_analysis.get('calls', []))
    
    print(f"📊 分析统计:")
    print(f"  - 总调用数: {total_calls}")
    print(f"  - 最大深度: {max_depth}")
    print(f"  - 接口实现数: {interface_count}")
    print(f"  - 已分析方法数: {len(analyzer.analyzed_methods)}")

def _build_call_tree_markdown(endpoint: Dict, call_chain: Dict, deep_analysis: Dict) -> str:
    """构建调用树的Markdown内容 - 增强版"""
    lines = []
    
    # 标题
    lines.append(f"# {endpoint['name']} 深度调用链分析")
    lines.append("")
    
    # 基本信息
    lines.append("## 接口基本信息")
    lines.append("")
    lines.append(f"- **接口名称**: {endpoint['name']}")
    lines.append(f"- **请求路径**: {endpoint['method']} {endpoint['path']}")
    lines.append(f"- **控制器**: {endpoint['controller']}")
    lines.append(f"- **处理方法**: {endpoint['handler']}")
    lines.append(f"- **源文件**: {endpoint['file_path']}")
    lines.append(f"- **行号**: {endpoint['line_number']}")
    lines.append("")
    
    # 浅层调用链（原有数据）
    lines.append("## 浅层调用链")
    lines.append("")
    method_calls = call_chain.get('method_calls', [])
    if method_calls:
        lines.append("```")
        for i, call in enumerate(method_calls, 1):
            obj = call.get('object', '')
            method = call.get('method', '')
            args = call.get('arguments', 0)
            line = call.get('position', 0)
            if obj:
                lines.append(f"{i:2d}. {obj}.{method}() - {args}个参数 (行:{line})")
            else:
                lines.append(f"{i:2d}. {method}() - {args}个参数 (行:{line})")
        lines.append("```")
    else:
        lines.append("无方法调用")
    lines.append("")
    
    # 深度调用树
    lines.append("## 深度调用树")
    lines.append("")
    
    if "error" in deep_analysis:
        lines.append(f"❌ 分析失败: {deep_analysis['error']}")
    else:
        lines.append("```")
        lines.append(f"📁 {endpoint['handler']}() - 主方法")
        _build_tree_recursive_enhanced(deep_analysis.get('calls', []), lines, "  ", set(), endpoint['handler'])
        lines.append("```")
    
    lines.append("")
    
    # 接口实现分析
    lines.append("## 接口实现分析")
    lines.append("")
    _build_implementation_analysis(deep_analysis.get('calls', []), lines)
    
    # 调用链详细说明
    lines.append("## 调用链详细说明")
    lines.append("")
    _build_detailed_explanation_enhanced(deep_analysis.get('calls', []), lines, 1)
    
    # 性能分析建议
    lines.append("## 性能分析建议")
    lines.append("")
    total_calls = _count_total_calls_enhanced(deep_analysis.get('calls', []))
    max_depth = _get_max_depth_enhanced(deep_analysis.get('calls', []))
    
    if total_calls > 30:
        lines.append("⚠️ **高复杂度接口**: 调用链非常复杂，强烈建议重构")
    elif total_calls > 20:
        lines.append("⚡ **中高复杂度**: 调用链较深，建议考虑重构")
    elif total_calls > 10:
        lines.append("⚡ **中等复杂度**: 调用链适中，注意性能监控")
    else:
        lines.append("✅ **简单接口**: 调用链简洁，性能良好")
    
    lines.append(f"- 总调用数: {total_calls}")
    lines.append(f"- 最大深度: {max_depth}")
    lines.append(f"- 接口实现数: {_count_interface_implementations(deep_analysis.get('calls', []))}")
    lines.append("")
    
    # 优化建议
    lines.append("### 优化建议")
    lines.append("")
    lines.append("1. **减少不必要的方法调用**: 合并相似的操作")
    lines.append("2. **缓存重复计算**: 对于重复的计算结果进行缓存")
    lines.append("3. **异步处理**: 对于耗时操作考虑异步处理")
    lines.append("4. **批量操作**: 减少数据库交互次数")
    lines.append("5. **接口优化**: 考虑使用具体实现类而非接口调用")
    lines.append("")
    
    return "\n".join(lines)

def _build_tree_recursive_enhanced(calls: List[Dict], lines: List[str], indent: str, visited_methods: set = None, current_method: str = ""):
    """递归构建调用树 - 增强版，避免重复显示"""
    if visited_methods is None:
        visited_methods = set()
    
    for call in calls:
        method = call.get('method', 'unknown')
        obj = call.get('object', '')
        line_num = call.get('line', 0)
        args = call.get('arguments', 0)
        call_type = call.get('type', 'instance')
        
        # 构建调用显示
        if obj:
            call_display = f"{obj}.{method}()"
        else:
            call_display = f"{method}()"
        
        # 创建方法标识符用于避免重复显示
        method_id = f"{obj}.{method}" if obj else method
        
        # 跳过递归调用自己的情况
        if method == current_method and call_type == "direct":
            lines.append(f"{indent}├── {call_display} [递归调用] - {args}个参数 (行:{line_num})")
            continue
        
        # 添加类型标识
        type_marker = ""
        if call_type == "static":
            type_marker = " [静态]"
        elif call_type == "constructor":
            type_marker = " [构造]"
        elif call_type == "chain":
            type_marker = " [链式]"
        elif call_type == "enum_constant":
            type_marker = " [枚举]"
        
        lines.append(f"{indent}├── {call_display}{type_marker} - {args}个参数 (行:{line_num})")
        
        # 检查是否已经显示过这个方法（避免循环显示）
        full_method_id = f"{method_id}@{line_num}"
        if full_method_id in visited_methods:
            lines.append(f"{indent}  └── [已分析过，避免重复显示]")
            continue
        
        visited_methods.add(full_method_id)
        
        # 处理多个实现
        implementations = call.get('implementations', [])
        if implementations:
            # 过滤掉标准库和枚举类的实现，避免过度展开
            filtered_impls = [impl for impl in implementations 
                            if impl.get('type') not in ['standard_library', 'enum_class']]
            
            if not filtered_impls:
                # 如果只有标准库实现，简单显示
                std_impls = [impl for impl in implementations 
                           if impl.get('type') in ['standard_library', 'enum_class']]
                if std_impls:
                    impl = std_impls[0]
                    impl_class = impl.get('class', 'unknown')
                    impl_type = impl.get('type', 'concrete')
                    type_desc = '标准库' if impl_type == 'standard_library' else '枚举类'
                    lines.append(f"{indent}  └── {impl_class} ({type_desc})")
                continue
            
            # 只显示最相关的实现（通常是第一个）
            impl = filtered_impls[0]
            impl_type = impl.get('type', 'concrete')
            impl_class = impl.get('class', 'unknown')
            
            type_desc = {
                'concrete': '具体实现',
                'interface_implementation': '接口实现',
                'inheritance': '继承实现',
                'local': '本地方法',
                'service_implementation': 'Service实现',
                'service_interface': 'Service接口',
                'project_class': '项目类',
                'similar_match': '相似匹配'
            }.get(impl_type, '未知类型')
            
            # 对于本地方法，不显示实现详情，直接展开子调用
            if impl_type == 'local':
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    # 过滤掉与当前方法相同的调用，避免无限递归显示
                    filtered_sub_calls = [sc for sc in sub_calls['calls'] 
                                        if sc.get('method') != method or sc.get('object') != obj]
                    if filtered_sub_calls:
                        _build_tree_recursive_enhanced(filtered_sub_calls, lines, indent + "  ", visited_methods.copy(), method)
                elif isinstance(sub_calls, dict) and 'note' in sub_calls:
                    lines.append(f"{indent}  └── {sub_calls['note']}")
            else:
                lines.append(f"{indent}  └── {impl_class} ({type_desc})")
                
                # 递归处理子调用
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    _build_tree_recursive_enhanced(sub_calls['calls'], lines, indent + "    ", visited_methods.copy(), method)
                elif isinstance(sub_calls, dict) and 'note' in sub_calls:
                    lines.append(f"{indent}    └── {sub_calls['note']}")
        else:
            # 处理单个实现（向后兼容）
            sub_calls = call.get('sub_calls', {})
            if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                # 过滤掉与当前方法相同的调用
                filtered_sub_calls = [sc for sc in sub_calls['calls'] 
                                    if sc.get('method') != method or sc.get('object') != obj]
                if filtered_sub_calls:
                    _build_tree_recursive_enhanced(filtered_sub_calls, lines, indent + "  ", visited_methods.copy(), method)
            elif isinstance(sub_calls, dict) and 'note' in sub_calls:
                lines.append(f"{indent}  └── {sub_calls['note']}")
        
        # 从已访问集合中移除，允许在不同分支中重新显示
        visited_methods.discard(full_method_id)

def _build_implementation_analysis(calls: List[Dict], lines: List[str]):
    """构建接口实现分析"""
    interface_calls = []
    concrete_calls = []
    
    def collect_implementations(call_list, depth=0):
        for call in call_list:
            implementations = call.get('implementations', [])
            if implementations:
                for impl in implementations:
                    if impl.get('type') == 'interface_implementation':
                        interface_calls.append({
                            'method': call.get('method', 'unknown'),
                            'object': call.get('object', ''),
                            'implementation': impl,
                            'depth': depth
                        })
                    elif impl.get('type') == 'concrete':
                        concrete_calls.append({
                            'method': call.get('method', 'unknown'),
                            'object': call.get('object', ''),
                            'implementation': impl,
                            'depth': depth
                        })
                    
                    # 递归收集
                    sub_calls = impl.get('sub_calls', {})
                    if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                        collect_implementations(sub_calls['calls'], depth + 1)
    
    collect_implementations(calls)
    
    if interface_calls:
        lines.append("### 接口调用")
        lines.append("")
        for call in interface_calls[:5]:  # 最多显示5个
            method = call['method']
            obj = call['object']
            impl_class = call['implementation'].get('class', 'unknown')
            lines.append(f"- **{obj}.{method}()** → {impl_class} (深度: {call['depth']})")
        
        if len(interface_calls) > 5:
            lines.append(f"- ... 还有 {len(interface_calls) - 5} 个接口调用")
        lines.append("")
    
    if concrete_calls:
        lines.append("### 具体类调用")
        lines.append("")
        for call in concrete_calls[:5]:  # 最多显示5个
            method = call['method']
            obj = call['object']
            impl_class = call['implementation'].get('class', 'unknown')
            lines.append(f"- **{obj}.{method}()** → {impl_class} (深度: {call['depth']})")
        
        if len(concrete_calls) > 5:
            lines.append(f"- ... 还有 {len(concrete_calls) - 5} 个具体类调用")
        lines.append("")

def _build_detailed_explanation_enhanced(calls: List[Dict], lines: List[str], level: int):
    """构建详细说明 - 增强版"""
    for i, call in enumerate(calls, 1):
        method = call.get('method', 'unknown')
        obj = call.get('object', '')
        call_type = call.get('type', 'instance')
        
        lines.append(f"### {level}.{i} {obj}.{method}() 调用" if obj else f"### {level}.{i} {method}() 调用")
        lines.append("")
        
        lines.append(f"- **调用类型**: {call_type}")
        lines.append(f"- **参数数量**: {call.get('arguments', 0)}")
        lines.append(f"- **调用行号**: {call.get('line', 0)}")
        
        # 实现信息
        implementations = call.get('implementations', [])
        if implementations:
            lines.append(f"- **实现数量**: {len(implementations)}")
            lines.append("")
            lines.append("**实现详情**:")
            
            for j, impl in enumerate(implementations, 1):
                impl_type = impl.get('type', 'concrete')
                impl_class = impl.get('class', 'unknown')
                impl_file = impl.get('file', '')
                
                lines.append(f"  {j}. **{impl_class}** ({impl_type})")
                if impl_file:
                    lines.append(f"     - 文件: {impl_file}")
                
                # 子调用统计
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    sub_count = len(sub_calls['calls'])
                    lines.append(f"     - 子调用: {sub_count} 个")
        else:
            # 向后兼容
            impl = call.get('implementation', '')
            if impl:
                lines.append(f"- **实现位置**: {impl}")
        
        lines.append("")

def _count_total_calls_enhanced(calls: List[Dict]) -> int:
    """计算总调用数 - 增强版"""
    total = len(calls)
    for call in calls:
        implementations = call.get('implementations', [])
        if implementations:
            for impl in implementations:
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    total += _count_total_calls_enhanced(sub_calls['calls'])
        else:
            # 向后兼容
            sub_calls = call.get('sub_calls', {})
            if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                total += _count_total_calls_enhanced(sub_calls['calls'])
    return total

def _get_max_depth_enhanced(calls: List[Dict], current_depth: int = 1) -> int:
    """获取最大深度 - 增强版"""
    max_depth = current_depth
    for call in calls:
        implementations = call.get('implementations', [])
        if implementations:
            for impl in implementations:
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    depth = _get_max_depth_enhanced(sub_calls['calls'], current_depth + 1)
                    max_depth = max(max_depth, depth)
        else:
            # 向后兼容
            sub_calls = call.get('sub_calls', {})
            if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                depth = _get_max_depth_enhanced(sub_calls['calls'], current_depth + 1)
                max_depth = max(max_depth, depth)
    return max_depth

def _count_interface_implementations(calls: List[Dict]) -> int:
    """统计接口实现数量"""
    count = 0
    
    def count_recursive(call_list):
        nonlocal count
        for call in call_list:
            implementations = call.get('implementations', [])
            for impl in implementations:
                if impl.get('type') == 'interface_implementation':
                    count += 1
                
                sub_calls = impl.get('sub_calls', {})
                if isinstance(sub_calls, dict) and 'calls' in sub_calls:
                    count_recursive(sub_calls['calls'])
    
    count_recursive(calls)
    return count

def show_endpoint_details(endpoint_path: str, output_dir: str = "./migration_output"):
    """显示特定接口的代码和调用链"""
    analysis_file = f"{output_dir}/endpoint_analysis.json"
    
    if not os.path.exists(analysis_file):
        print(f"❌ 分析文件不存在: {analysis_file}")
        print("请先运行单项目分析生成分析数据：")
        print("python main.py --single /path/to/project")
        return
    
    # 加载分析数据
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取分析文件失败: {e}")
        return
    
    # 查找匹配的接口
    matching_endpoints = []
    for endpoint_data in analysis_data:
        endpoint = endpoint_data['endpoint']
        if endpoint_path in endpoint['path'] or endpoint_path == endpoint['path']:
            matching_endpoints.append(endpoint_data)
    
    if not matching_endpoints:
        print(f"❌ 未找到匹配的接口: {endpoint_path}")
        print("\n可用的接口路径:")
        for endpoint_data in analysis_data[:10]:  # 显示前10个作为示例
            endpoint = endpoint_data['endpoint']
            print(f"  - {endpoint['method']} {endpoint['path']}")
        if len(analysis_data) > 10:
            print(f"  ... 还有 {len(analysis_data) - 10} 个接口")
        return
    
    # 显示匹配的接口
    if len(matching_endpoints) > 1:
        print(f"🔍 找到 {len(matching_endpoints)} 个匹配的接口:")
        for i, endpoint_data in enumerate(matching_endpoints, 1):
            endpoint = endpoint_data['endpoint']
            print(f"{i}. {endpoint['method']} {endpoint['path']} - {endpoint['name']}")
        
        try:
            choice = int(input("\n请选择要查看的接口 (输入序号): ")) - 1
            if 0 <= choice < len(matching_endpoints):
                selected_endpoint = matching_endpoints[choice]
            else:
                print("❌ 无效的选择")
                return
        except ValueError:
            print("❌ 请输入有效的数字")
            return
    else:
        selected_endpoint = matching_endpoints[0]
    
    # 显示接口详细信息
    _display_endpoint_details(selected_endpoint)

def _display_endpoint_details(endpoint_data: Dict):
    """显示接口的详细信息"""
    endpoint = endpoint_data['endpoint']
    call_chain = endpoint_data['call_chain']
    sql_mappings = endpoint_data.get('sql_mappings', [])
    complexity_score = endpoint_data['complexity_score']
    
    print(f"\n{'='*80}")
    print(f"🔍 接口详细信息")
    print(f"{'='*80}")
    
    # 基本信息
    print(f"📋 基本信息:")
    print(f"  接口名称: {endpoint['name']}")
    print(f"  请求路径: {endpoint['method']} {endpoint['path']}")
    print(f"  控制器: {endpoint['controller']}")
    print(f"  处理方法: {endpoint['handler']}")
    print(f"  源文件: {endpoint['file_path']}")
    print(f"  行号: {endpoint['line_number']}")
    print(f"  复杂度: {complexity_score}")
    print(f"  框架: {endpoint['framework']}")
    print()
    
    # 调用链分析
    print(f"🔗 调用链分析:")
    method_calls = call_chain.get('method_calls', [])
    if method_calls:
        print(f"  方法调用 ({len(method_calls)}个):")
        for i, call in enumerate(method_calls, 1):
            obj = call.get('object', 'unknown')
            method = call.get('method', 'unknown')
            args = call.get('arguments', 0)
            position = call.get('position', 0)
            print(f"    {i:2d}. {obj}.{method}() - {args}个参数 (行:{position})")
    else:
        print("  无复杂方法调用")
    print()
    
    # 相关文件
    files = call_chain.get('files', [])
    if files:
        print(f"📁 相关文件 ({len(files)}个):")
        # 按类型分组显示
        service_files = [f for f in files if 'service' in f.get('path', '').lower()]
        dto_files = [f for f in files if 'dto' in f.get('path', '').lower()]
        vo_files = [f for f in files if 'vo' in f.get('path', '').lower()]
        mapper_files = [f for f in files if 'mapper' in f.get('path', '').lower()]
        
        if service_files:
            print("  Service层:")
            for file in service_files[:3]:  # 最多显示3个
                file_name = Path(file['path']).name
                print(f"    - {file_name}")
        
        if dto_files:
            print("  DTO对象:")
            for file in dto_files[:3]:
                file_name = Path(file['path']).name
                print(f"    - {file_name}")
        
        if vo_files:
            print("  VO对象:")
            for file in vo_files[:3]:
                file_name = Path(file['path']).name
                print(f"    - {file_name}")
        
        if mapper_files:
            print("  Mapper层:")
            for file in mapper_files[:3]:
                file_name = Path(file['path']).name
                print(f"    - {file_name}")
    print()
    
    # SQL映射信息
    if sql_mappings:
        print(f"🗄️  SQL映射信息:")
        for mapping in sql_mappings[:3]:  # 最多显示3个
            file_path = mapping.get('file_path', '')
            file_name = Path(file_path).name if file_path else 'unknown'
            methods = mapping.get('methods', [])
            print(f"  {file_name}:")
            for method in methods[:2]:  # 每个文件最多显示2个方法
                method_id = method.get('id', 'unknown')
                sql_type = method.get('type', 'unknown')
                sql = method.get('sql', '')[:60] + '...' if len(method.get('sql', '')) > 60 else method.get('sql', '')
                print(f"    - {method_id} ({sql_type}): {sql}")
    print()
    
    # 尝试读取并显示源代码
    _display_source_code(endpoint)

def _display_source_code(endpoint: Dict):
    """显示源代码"""
    file_path = endpoint['file_path']
    line_number = endpoint['line_number']
    handler_name = endpoint['handler']
    
    print(f"📝 源代码片段:")
    
    try:
        # 尝试读取源文件
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找方法定义
            method_start = -1
            method_end = -1
            brace_count = 0
            in_method = False
            
            # 从指定行号开始向前查找方法定义
            for i in range(max(0, line_number - 10), min(len(lines), line_number + 50)):
                line = lines[i].strip()
                
                # 查找方法定义
                if handler_name in lines[i] and ('public' in lines[i] or 'private' in lines[i] or 'protected' in lines[i]):
                    method_start = i
                    in_method = True
                    brace_count = 0
                
                if in_method:
                    # 计算大括号
                    brace_count += line.count('{') - line.count('}')
                    
                    # 如果大括号平衡，说明方法结束
                    if brace_count == 0 and method_start != -1 and i > method_start:
                        method_end = i
                        break
            
            # 显示方法代码
            if method_start != -1:
                print(f"  文件: {Path(file_path).name}")
                print(f"  方法: {handler_name} (行 {method_start + 1}-{method_end + 1 if method_end != -1 else '?'})")
                print("  " + "-" * 60)
                
                end_line = method_end if method_end != -1 else min(method_start + 20, len(lines))
                for i in range(method_start, end_line + 1):
                    if i < len(lines):
                        line_num = i + 1
                        code_line = lines[i].rstrip()
                        # 高亮当前行
                        marker = ">>>" if line_num == line_number else "   "
                        print(f"  {marker} {line_num:3d}: {code_line}")
            else:
                print(f"  ❌ 无法找到方法 {handler_name} 的定义")
        else:
            print(f"  ❌ 源文件不存在: {file_path}")
    
    except Exception as e:
        print(f"  ❌ 读取源文件失败: {e}")
    
    print(f"\n{'='*80}")
    print("✅ 接口分析完成")
    print(f"{'='*80}\n")

@dataclass
class Config:
    """配置类"""
    old_project_path: Optional[str] = None
    new_project_path: Optional[str] = None
    single_project_path: Optional[str] = None  # 新增：单项目模式
    output_dir: str = "./migration_output"
    ai_model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    context_window: int = 4000
    verbose: bool = False
    analyze_only: bool = False  # 仅分析模式
    single_mode: bool = False   # 新增：单项目模式标志

class MigrationTool:
    """迁移工具主类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.endpoint_extractor = EndpointExtractor()
        self.equivalence_matcher = EquivalenceMatcher()
        self.call_chain_analyzer = CallChainAnalyzer()
        self.sql_mapper_analyzer = SQLMapperAnalyzer()
        
        # 仅在配置了API密钥时初始化AI生成器
        if not config.analyze_only and (config.api_key or os.getenv("OPENAI_API_KEY")):
            self.ai_generator = AIGenerator(
                model=config.ai_model,
                api_key=config.api_key or os.getenv("OPENAI_API_KEY")
            )
        else:
            self.ai_generator = None
            if not config.single_mode:
                print("⚠️  AI功能已禁用，仅执行分析")
        
        # 创建输出目录
        os.makedirs(config.output_dir, exist_ok=True)
        
    def run(self):
        """运行完整的迁移流程"""
        if self.config.single_mode:
            self.run_single_project_analysis()
        else:
            self.run_migration_analysis()
    
    def run_single_project_analysis(self):
        """运行单项目分析"""
        print("🚀 开始分析项目接口...")
        
        # 提取接口
        print("📋 提取项目接口...")
        endpoints = self.endpoint_extractor.extract_from_project(
            self.config.single_project_path
        )
        
        print(f"✅ 提取完成: 共找到 {len(endpoints)} 个接口")
        
        # 显示解析的接口结构
        if self.config.verbose:
            self.display_endpoints("项目接口结构", endpoints)
        
        # 分析每个接口的调用链
        print("🔍 分析接口调用链和依赖...")
        endpoint_analysis = []
        
        total_endpoints = len(endpoints)
        for i, (name, endpoint) in enumerate(endpoints.items(), 1):
            print(f"  📊 分析进度: {i}/{total_endpoints} ({i/total_endpoints*100:.1f}%) - {endpoint.name}")
            
            # 分析调用链
            call_chain = self.call_chain_analyzer.analyze_call_chain(
                endpoint, self.config.single_project_path
            )
            
            # 分析SQL映射
            sql_mappings = self.sql_mapper_analyzer.find_related_mappers(
                call_chain, self.config.single_project_path
            )
            
            analysis = {
                "endpoint": endpoint,
                "call_chain": call_chain,
                "sql_mappings": sql_mappings,
                "complexity_score": self._calculate_complexity_score(call_chain, sql_mappings)
            }
            
            endpoint_analysis.append(analysis)
        
        print("✅ 接口分析完成")
        
        # 显示分析结果
        if self.config.verbose:
            self.display_single_project_analysis(endpoint_analysis)
        
        # 保存结果
        print("💾 保存分析结果...")
        self.save_single_project_results(endpoints, endpoint_analysis)
        
        print(f"🎉 单项目分析完成! 结果已保存到: {self.config.output_dir}")
        print(f"📋 可以使用以下命令查看接口详情:")
        print(f"   python main.py --show-endpoint <接口路径> --output {self.config.output_dir}")
        print(f"📋 可以使用以下命令生成调用链树:")
        print(f"   python main.py --call-tree <接口路径> --output {self.config.output_dir}")
    
    def run_migration_analysis(self):
        """运行迁移分析（原有逻辑）"""
        print("🚀 开始分析新旧项目接口...")
        
        # 1. 提取接口
        print("📋 步骤1: 提取旧项目接口...")
        old_endpoints = self.endpoint_extractor.extract_from_project(
            self.config.old_project_path
        )
        
        print(f"📋 步骤2: 提取新项目接口...")
        new_endpoints = self.endpoint_extractor.extract_from_project(
            self.config.new_project_path
        )
        
        print(f"✅ 提取完成: 旧接口 {len(old_endpoints)} 个, 新接口 {len(new_endpoints)} 个")
        
        # 显示解析的接口结构
        if self.config.verbose:
            self.display_endpoints("旧项目接口结构", old_endpoints)
            self.display_endpoints("新项目接口结构", new_endpoints)
        
        # 2. 匹配等价接口
        print("🔄 步骤3: 匹配等价接口...")
        matched_pairs = self.equivalence_matcher.match_endpoints(
            old_endpoints, new_endpoints
        )
        
        print(f"✅ 匹配完成: 找到 {len(matched_pairs)} 对等价接口")
        
        # 显示匹配的接口对
        if self.config.verbose and matched_pairs:
            self.display_matched_pairs(matched_pairs)
        
        # 3. 分析调用链和SQL映射
        print("🔍 步骤4: 分析调用链和依赖...")
        migration_plan = self.analyze_migration_plan(matched_pairs)
        
        # 显示调用链信息
        if self.config.verbose and migration_plan:
            self.display_call_chains(migration_plan)
        
        # 4. 仅在启用AI功能时生成迁移代码
        if self.ai_generator:
            print("🤖 步骤5: 生成迁移代码...")
            generated_code = self.generate_migration_code(migration_plan)
        else:
            generated_code = {}
            print("⏭️  跳过代码生成步骤（未启用AI功能）")
        
        # 5. 保存结果
        print("💾 步骤6: 保存结果...")
        self.save_results(old_endpoints, new_endpoints, matched_pairs, generated_code)
        
        print(f"🎉 {'分析' if self.config.analyze_only else '迁移'}完成! 结果已保存到: {self.config.output_dir}")
    
    def display_endpoints(self, title: str, endpoints: Dict):
        """显示解析的接口结构"""
        print(f"\n=== {title} ===")
        for i, (name, endpoint) in enumerate(endpoints.items(), 1):
            print(f"{i}. {name}:")
            print(f"  路径: {endpoint.path}")
            print(f"  方法: {endpoint.method}")
            print(f"  控制器: {endpoint.controller}")
            print(f"  处理器: {endpoint.handler}")
            print(f"  文件: {endpoint.file_path}")
            print(f"  行号: {endpoint.line_number}")
            print("-" * 40)
    
    def display_matched_pairs(self, matched_pairs: List):
        """显示匹配的接口对"""
        print("\n=== 等价接口匹配结果 ===")
        for i, (old_ep, new_ep) in enumerate(matched_pairs, 1):
            print(f"{i}. 匹配对:")
            print(f"  旧接口: {old_ep.name} ({old_ep.method} {old_ep.path})")
            print(f"  新接口: {new_ep.name} ({new_ep.method} {new_ep.path})")
            print(f"  相似度: {getattr(old_ep, 'match_score', {}).get('total_score', 0):.2f}")
            print("-" * 60)
    
    def display_single_project_analysis(self, endpoint_analysis: List[Dict]):
        """显示单项目分析结果"""
        print("\n=== 单项目接口分析结果 ===")
        
        # 统计信息
        total_endpoints = len(endpoint_analysis)
        complex_endpoints = sum(1 for analysis in endpoint_analysis if analysis["complexity_score"] > 5)
        
        print(f"总接口数: {total_endpoints}")
        print(f"复杂接口数: {complex_endpoints}")
        print(f"简单接口数: {total_endpoints - complex_endpoints}")
        
        # 按复杂度排序显示
        sorted_analysis = sorted(endpoint_analysis, key=lambda x: x["complexity_score"], reverse=True)
        
        for i, analysis in enumerate(sorted_analysis, 1):
            endpoint = analysis["endpoint"]
            call_chain = analysis["call_chain"]
            complexity = analysis["complexity_score"]
            
            print(f"\n{i}. 接口: {endpoint.name}")
            print(f"   路径: {endpoint.method} {endpoint.path}")
            print(f"   文件: {endpoint.file_path}:{endpoint.line_number}")
            print(f"   复杂度: {complexity}")
            
            if call_chain.get("method_calls"):
                print(f"   方法调用: {len(call_chain['method_calls'])} 个")
                if self.config.verbose:
                    for j, call in enumerate(call_chain["method_calls"][:3], 1):  # 只显示前3个
                        print(f"     {j}. {call.get('object', '')}.{call.get('method', '')}()")
            
            if call_chain.get("sql_statements"):
                print(f"   SQL语句: {len(call_chain['sql_statements'])} 个")
            
            if analysis.get("sql_mappings"):
                print(f"   SQL映射: {len(analysis['sql_mappings'])} 个")
            
            print("-" * 60)
    
    def display_call_chains(self, migration_plan: List[Dict]):
        """显示接口调用链信息"""
        print("\n=== 接口调用链分析 ===")
        for i, plan in enumerate(migration_plan, 1):
            old_ep = plan["old_endpoint"]
            print(f"{i}. 接口: {old_ep.name} ({old_ep.method} {old_ep.path})")
            
            call_chain = plan["call_chain"]
            if call_chain.get("method_calls"):
                print("  方法调用链:")
                for j, call in enumerate(call_chain["method_calls"], 1):
                    print(f"    {j}. {call.get('object', '')}.{call.get('method', '')}()")
            
            if call_chain.get("service_calls"):
                print("  服务调用:")
                for j, service in enumerate(call_chain["service_calls"], 1):
                    print(f"    {j}. {service}")
            
            if call_chain.get("dao_calls"):
                print("  DAO调用:")
                for j, dao in enumerate(call_chain["dao_calls"], 1):
                    print(f"    {j}. {dao}")
            
            if call_chain.get("sql_statements"):
                print("  SQL语句:")
                for j, sql in enumerate(call_chain["sql_statements"], 1):
                    print(f"    {j}. {sql[:100]}...")  # 只显示前100个字符
            
            print("-" * 60)
    
    def _calculate_complexity_score(self, call_chain: Dict, sql_mappings: List) -> int:
        """计算接口复杂度得分"""
        score = 0
        
        # 方法调用数量
        method_calls = len(call_chain.get("method_calls", []))
        score += method_calls * 1
        
        # SQL语句数量
        sql_statements = len(call_chain.get("sql_statements", []))
        score += sql_statements * 2
        
        # SQL映射文件数量
        score += len(sql_mappings) * 3
        
        # 相关文件数量
        related_files = len(call_chain.get("files", []))
        score += related_files * 1
        
        return score
    
    def analyze_migration_plan(self, matched_pairs: List) -> List[Dict]:
        """分析迁移计划"""
        migration_plan = []
        
        total_pairs = len(matched_pairs)
        print(f"🔍 开始分析 {total_pairs} 对匹配接口的迁移计划...")
        
        for i, (old_endpoint, new_endpoint) in enumerate(matched_pairs, 1):
            print(f"  📊 分析进度: {i}/{total_pairs} ({i/total_pairs*100:.1f}%) - {old_endpoint.name}")
            
            # 分析调用链
            call_chain = self.call_chain_analyzer.analyze_call_chain(
                old_endpoint, self.config.old_project_path
            )
            
            # 分析SQL映射
            sql_mappings = self.sql_mapper_analyzer.find_related_mappers(
                call_chain, self.config.old_project_path
            )
            
            # 收集需要迁移的代码上下文
            migration_context = self.collect_migration_context(
                old_endpoint, call_chain, sql_mappings
            )
            
            migration_plan.append({
                "old_endpoint": old_endpoint,
                "new_endpoint": new_endpoint,
                "call_chain": call_chain,
                "sql_mappings": sql_mappings,
                "migration_context": migration_context,
                "estimated_tokens": len(str(migration_context)) // 4  # 粗略估算
            })
        
        print("✅ 迁移计划分析完成")
        return migration_plan
    
    def collect_migration_context(self, old_endpoint, call_chain, sql_mappings):
        """收集迁移需要的代码上下文"""
        context = {
            "old_endpoint": old_endpoint.__dict__ if hasattr(old_endpoint, '__dict__') else old_endpoint,
            "call_chain": call_chain,
            "sql_mappings": sql_mappings,
            "related_files": set()
        }
        
        # 收集所有相关文件内容
        project_root = Path(self.config.old_project_path)
        
        for file_info in call_chain.get("files", []):
            file_path = project_root / file_info["path"]
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    context["related_files"].add({
                        "path": str(file_path.relative_to(project_root)),
                        "content": content[:5000]  # 限制大小
                    })
                except:
                    continue
        
        return context
    
    def generate_migration_code(self, migration_plan: List[Dict]) -> Dict:
        """生成迁移代码"""
        generated_code = {}
        
        total_plans = len(migration_plan)
        print(f"🤖 开始生成 {total_plans} 个接口的迁移代码...")
        
        for i, plan in enumerate(migration_plan, 1):
            endpoint_name = plan["old_endpoint"].get("name", f"endpoint_{i}")
            print(f"  📊 生成进度: {i}/{total_plans} ({i/total_plans*100:.1f}%) - {endpoint_name}")
            
            if plan["estimated_tokens"] > self.config.context_window:
                print(f"    ⚠️  警告: 接口上下文过大 ({plan['estimated_tokens']} tokens)，跳过生成")
                continue
                
            try:
                generated = self.ai_generator.generate_migration_code(plan)
                generated_code[endpoint_name] = generated
                print(f"    ✅ 生成成功")
            except Exception as e:
                print(f"    ❌ 生成失败: {e}")
        
        print("✅ 迁移代码生成完成")        
        return generated_code
    
    def save_single_project_results(self, endpoints: Dict, endpoint_analysis: List[Dict]):
        """保存单项目分析结果"""
        # 保存接口信息
        with open(f"{self.config.output_dir}/endpoints.json", "w", encoding='utf-8') as f:
            json.dump([e.__dict__ for e in endpoints.values()], f, indent=2, ensure_ascii=False)
        
        # 保存分析结果
        analysis_data = []
        for analysis in endpoint_analysis:
            endpoint_dict = analysis["endpoint"].__dict__
            analysis_dict = {
                "endpoint": endpoint_dict,
                "call_chain": analysis["call_chain"],
                "sql_mappings": analysis["sql_mappings"],
                "complexity_score": analysis["complexity_score"]
            }
            analysis_data.append(analysis_dict)
        
        with open(f"{self.config.output_dir}/endpoint_analysis.json", "w", encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        # 生成分析报告
        self._generate_analysis_report(endpoints, endpoint_analysis)
    
    def _generate_analysis_report(self, endpoints: Dict, endpoint_analysis: List[Dict]):
        """生成分析报告"""
        report_lines = []
        report_lines.append("# 项目接口分析报告\n")
        
        # 统计信息
        total_endpoints = len(endpoint_analysis)
        complex_endpoints = sum(1 for analysis in endpoint_analysis if analysis["complexity_score"] > 5)
        frameworks = set(ep.framework for ep in endpoints.values())
        
        report_lines.append("## 统计概览\n")
        report_lines.append(f"- 总接口数: {total_endpoints}")
        report_lines.append(f"- 复杂接口数: {complex_endpoints}")
        report_lines.append(f"- 简单接口数: {total_endpoints - complex_endpoints}")
        report_lines.append(f"- 使用框架: {', '.join(frameworks)}")
        report_lines.append("")
        
        # 接口列表
        report_lines.append("## 接口详情\n")
        sorted_analysis = sorted(endpoint_analysis, key=lambda x: x["complexity_score"], reverse=True)
        
        for i, analysis in enumerate(sorted_analysis, 1):
            endpoint = analysis["endpoint"]
            complexity = analysis["complexity_score"]
            
            report_lines.append(f"### {i}. {endpoint.name}")
            report_lines.append(f"- **路径**: {endpoint.method} {endpoint.path}")
            report_lines.append(f"- **文件**: {endpoint.file_path}:{endpoint.line_number}")
            report_lines.append(f"- **复杂度**: {complexity}")
            report_lines.append(f"- **框架**: {endpoint.framework}")
            
            call_chain = analysis["call_chain"]
            if call_chain.get("method_calls"):
                report_lines.append(f"- **方法调用**: {len(call_chain['method_calls'])} 个")
            if call_chain.get("sql_statements"):
                report_lines.append(f"- **SQL语句**: {len(call_chain['sql_statements'])} 个")
            if analysis.get("sql_mappings"):
                report_lines.append(f"- **SQL映射**: {len(analysis['sql_mappings'])} 个")
            
            report_lines.append("")
        
        # 保存报告
        with open(f"{self.config.output_dir}/analysis_report.md", "w", encoding='utf-8') as f:
            f.write("\n".join(report_lines))
    
    def save_results(self, *args):
        """保存所有结果到文件"""
        # 保存旧接口
        with open(f"{self.config.output_dir}/old_endpoints.json", "w", encoding='utf-8') as f:
            json.dump([e.__dict__ for e in args[0].values()], f, indent=2, ensure_ascii=False)
        
        # 保存新接口
        with open(f"{self.config.output_dir}/new_endpoints.json", "w", encoding='utf-8') as f:
            json.dump([e.__dict__ for e in args[1].values()], f, indent=2, ensure_ascii=False)
        
        # 保存匹配结果
        matched_data = []
        for old, new in args[2]:
            matched_data.append({
                "old": old.__dict__,
                "new": new.__dict__
            })
        with open(f"{self.config.output_dir}/matched_pairs.json", "w", encoding='utf-8') as f:
            json.dump(matched_data, f, indent=2, ensure_ascii=False)
        
        # 保存生成的代码
        with open(f"{self.config.output_dir}/generated_code.json", "w", encoding='utf-8') as f:
            json.dump(args[3], f, indent=2, ensure_ascii=False)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='新旧系统接口迁移工具')
    
    # 创建互斥组：要么是迁移模式，要么是单项目模式，要么是接口查看模式，要么是调用树生成模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--migrate', action='store_true', help='迁移模式：分析新旧两个项目')
    mode_group.add_argument('--single', metavar='PROJECT_PATH', help='单项目模式：只分析一个项目')
    mode_group.add_argument('--show-endpoint', metavar='ENDPOINT_PATH', help='显示特定接口的代码和调用链，如：/admin/category/page')
    mode_group.add_argument('--call-tree', metavar='ENDPOINT_PATH', help='生成特定接口的深度调用链树，如：/user/user/login')
    
    # 迁移模式参数
    parser.add_argument('--old', help='旧项目路径（迁移模式必需）')
    parser.add_argument('--new', help='新项目路径（迁移模式必需）')
    
    # 通用参数
    parser.add_argument('--output', default='./migration_output', help='输出目录')
    parser.add_argument('--model', default='gpt-3.5-turbo', help='AI模型名称')
    parser.add_argument('--api-key', help='AI API密钥，或设置 OPENAI_API_KEY 环境变量')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细分析信息')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析项目结构，不生成迁移代码')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.migrate:
        if not args.old or not args.new:
            parser.error("迁移模式需要同时指定 --old 和 --new 参数")
        
        config = Config(
            old_project_path=args.old,
            new_project_path=args.new,
            output_dir=args.output,
            ai_model=args.model,
            api_key=args.api_key,
            verbose=args.verbose,
            analyze_only=args.analyze_only or not (args.api_key or os.getenv("OPENAI_API_KEY")),
            single_mode=False
        )
    elif args.single:  # 单项目模式
        config = Config(
            single_project_path=args.single,
            output_dir=args.output,
            ai_model=args.model,
            api_key=args.api_key,
            verbose=args.verbose,
            analyze_only=True,  # 单项目模式默认只分析
            single_mode=True
        )
    elif args.show_endpoint:  # 接口查看模式
        # 直接调用接口查看功能，不需要创建MigrationTool
        show_endpoint_details(args.show_endpoint, args.output)
        return
    else:  # 调用树生成模式
        # 直接调用调用树生成功能
        generate_call_tree(args.call_tree, args.output)
        return
    
    # 运行工具
    tool = MigrationTool(config)
    tool.run()

if __name__ == "__main__":
    main()