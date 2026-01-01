import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

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
        
        # 3. 静态方法调用 Class.method() - 只匹配真正的类名（完全大写开头）
        static_pattern = r'\b([A-Z][A-Z_]*[A-Z]|[A-Z][a-z]*[A-Z]\w*)\.(\w+)\s*\(([^)]*)\)'
        static_matches = re.finditer(static_pattern, line_clean)
        for match in static_matches:
            # 确保是真正的类名，不是驼峰命名的变量名
            class_name = match.group(1)
            if class_name[0].isupper() and (len(class_name) == 1 or class_name[1].isupper() or not any(c.islower() for c in class_name[:3])):
                # 避免重复添加已经在枚举调用中处理的
                if not any(call.get("enum_class") == class_name and call["method"] == match.group(2) 
                          and call["line"] == line_number for call in calls):
                    calls.append({
                        "object": class_name,
                        "method": match.group(2),
                        "line": line_number,
                        "arguments": self._count_arguments_from_string(match.group(3)),
                        "type": "static"
                    })
                    

        
        # 4. 实例方法调用 object.method() - 使用简单模式匹配所有可能的调用
        # 先找到所有的 object.method( 模式，然后单独处理参数
        simple_instance_pattern = r'(\w+)\.(\w+)\s*\('
        simple_matches = re.finditer(simple_instance_pattern, line_clean)
        
        for match in simple_matches:
            obj_name = match.group(1)
            method_name = match.group(2)
            
            # 跳过已经在其他模式中处理的调用
            if any(call["object"] == obj_name and call["method"] == method_name 
                  and call["line"] == line_number for call in calls):
                continue
            
            # 找到完整的方法调用（包括参数）
            start_pos = match.end() - 1  # 从 '(' 开始
            paren_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(line_clean[start_pos:], start_pos):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_pos = i
                        break
            
            # 提取参数部分
            if end_pos > start_pos:
                args_part = line_clean[start_pos+1:end_pos]
                calls.append({
                    "object": obj_name,
                    "method": method_name,
                    "line": line_number,
                    "arguments": self._count_arguments_from_string(args_part),
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
            pattern = rf'@Autowired\s+(?:private\s+)?(\w+(?:Service|ServiceImpl))\s+{re.escape(variable_name)}\s*;'
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