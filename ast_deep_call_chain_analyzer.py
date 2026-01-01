import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

class ASTDeepCallChainAnalyzer:
    """基于AST的深度调用链分析器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analyzed_methods = set()  # 避免循环分析
        self.call_tree = {}
        self.interface_implementations = {}  # 接口实现映射
        self.class_hierarchy = {}  # 类继承关系
        self._build_class_hierarchy()
        
        # 导入javalang
        try:
            import javalang
            self.javalang = javalang
        except ImportError:
            raise ImportError("AST解析需要安装javalang: pip install javalang")
    
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
            if i % 50 == 0 or i == total_files:
                print(f"  📊 分析进度: {i}/{total_files} ({i/total_files*100:.1f}%)")
            self._analyze_class_structure_ast(file_path)
        
        interface_count = len(self.interface_implementations)
        class_count = len(self.class_hierarchy)
        print(f"✅ 类继承关系构建完成: {class_count} 个类, {interface_count} 个接口")
    
    def _analyze_class_structure_ast(self, file_path: str):
        """使用AST分析单个Java文件的类结构"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用javalang解析
            tree = self.javalang.parse.parse(content)
            
            # 查找类声明
            for path, node in tree.filter(self.javalang.tree.ClassDeclaration):
                class_name = node.name
                
                # 获取父类
                parent_class = None
                if node.extends:
                    parent_class = node.extends.name
                
                # 获取实现的接口
                interfaces = []
                if node.implements:
                    for impl in node.implements:
                        interfaces.append(impl.name)
                
                self.class_hierarchy[class_name] = {
                    'file': file_path,
                    'parent': parent_class,
                    'interfaces': interfaces
                }
                
                # 建立接口到实现类的映射
                for interface in interfaces:
                    if interface not in self.interface_implementations:
                        self.interface_implementations[interface] = []
                    self.interface_implementations[interface].append({
                        'class': class_name,
                        'file': file_path
                    })
            
            # 查找接口声明
            for path, node in tree.filter(self.javalang.tree.InterfaceDeclaration):
                interface_name = node.name
                if interface_name not in self.interface_implementations:
                    self.interface_implementations[interface_name] = []
                    
        except Exception as e:
            # AST解析失败时静默跳过
            pass
    
    def analyze_method_calls(self, file_path: str, method_name: str, depth: int = 0, max_depth: int = 4) -> Dict:
        """使用AST深度分析方法调用"""
        if depth > max_depth:
            return {"note": "达到最大深度限制"}
        
        method_key = f"{file_path}:{method_name}:{depth}"
        if method_key in self.analyzed_methods:
            return {"note": "已分析过，避免循环引用"}
        
        indent = "  " * depth
        print(f"{indent}🔍 AST分析方法: {method_name} (深度: {depth})")
        
        self.analyzed_methods.add(method_key)
        
        try:
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用javalang解析
            tree = self.javalang.parse.parse(content)
            
            # 查找目标方法
            target_method = None
            for path, node in tree.filter(self.javalang.tree.MethodDeclaration):
                if node.name == method_name:
                    target_method = node
                    break
            
            if not target_method:
                return {"error": f"未找到方法: {method_name}"}
            
            # 提取方法调用
            method_calls = self._extract_method_calls_ast(target_method)
            
            # 去重和过滤方法调用
            unique_calls = self._deduplicate_method_calls_ast(method_calls)
            print(f"{indent}  📋 找到 {len(method_calls)} 个方法调用，去重后 {len(unique_calls)} 个")
            
            # 递归分析每个调用
            detailed_calls = []
            for i, call in enumerate(unique_calls, 1):
                if len(unique_calls) > 5 and i % 5 == 0:
                    print(f"{indent}  📊 处理调用进度: {i}/{len(unique_calls)}")
                
                call_detail = {
                    "method": call["method"],
                    "object": call.get("object", ""),
                    "line": call.get("line", 0),
                    "arguments": call.get("arguments", 0),
                    "type": call.get("type", "instance")
                }
                
                # 查找方法实现
                implementations = self._find_method_implementations_ast(call, file_path)
                
                if implementations:
                    call_detail["implementations"] = []
                    
                    for impl in implementations:
                        impl_detail = {
                            "file": impl["file"],
                            "class": impl.get("class", ""),
                            "type": impl.get("type", "concrete")
                        }
                        
                        # 递归分析实现
                        if (impl["file"] and os.path.exists(impl["file"]) and 
                            depth < max_depth and 
                            impl.get("type") not in ["standard_library", "enum_class"]):
                            
                            impl_detail["sub_calls"] = self.analyze_method_calls(
                                impl["file"], call["method"], depth + 1, max_depth
                            )
                        
                        call_detail["implementations"].append(impl_detail)
                
                detailed_calls.append(call_detail)
            
            print(f"{indent}✅ AST方法 {method_name} 分析完成")
            return {
                "file": file_path,
                "method": method_name,
                "calls": detailed_calls,
                "depth": depth,
                "parse_method": "ast"
            }
            
        except Exception as e:
            print(f"{indent}❌ AST分析失败: {str(e)}")
            return {"error": f"AST分析失败: {str(e)}"}
    
    def _extract_method_calls_ast(self, method_node) -> List[Dict]:
        """使用AST提取方法调用"""
        calls = []
        
        # 遍历方法体中的所有方法调用
        for path, node in method_node.filter(self.javalang.tree.MethodInvocation):
            call_info = {
                "method": node.member,
                "object": self._get_qualifier_name_ast(node.qualifier),
                "arguments": len(node.arguments) if node.arguments else 0,
                "line": node.position.line if node.position else 0,
                "type": self._determine_call_type_ast(node)
            }
            calls.append(call_info)
        
        # 查找构造函数调用
        for path, node in method_node.filter(self.javalang.tree.ClassCreator):
            call_info = {
                "method": "<init>",
                "object": node.type.name,
                "arguments": len(node.arguments) if node.arguments else 0,
                "line": node.position.line if node.position else 0,
                "type": "constructor"
            }
            calls.append(call_info)
        
        return calls
    
    def _get_qualifier_name_ast(self, qualifier) -> str:
        """获取限定符名称"""
        if qualifier is None:
            return ""
        
        if hasattr(qualifier, 'member'):
            # 链式调用 a.b.c
            return f"{self._get_qualifier_name_ast(qualifier.qualifier)}.{qualifier.member}"
        elif hasattr(qualifier, 'name'):
            # 简单名称
            return qualifier.name
        else:
            return str(qualifier)
    
    def _determine_call_type_ast(self, node) -> str:
        """确定调用类型"""
        if node.qualifier is None:
            return "direct"
        
        qualifier_name = self._get_qualifier_name_ast(node.qualifier)
        
        # 判断是否是静态调用（类名开头大写）
        if qualifier_name and qualifier_name[0].isupper():
            return "static"
        else:
            return "instance"
    
    def _deduplicate_method_calls_ast(self, method_calls: List[Dict]) -> List[Dict]:
        """去重方法调用"""
        unique_calls = []
        seen_calls = set()
        
        for call in method_calls:
            obj = call.get("object", "")
            method = call.get("method", "")
            line = call.get("line", 0)
            
            unique_key = f"{obj}.{method}@{line}"
            
            if unique_key not in seen_calls:
                seen_calls.add(unique_key)
                unique_calls.append(call)
        
        return unique_calls
    
    def _find_method_implementations_ast(self, call: Dict, current_file: str) -> List[Dict]:
        """查找方法的所有实现"""
        method_name = call["method"]
        object_name = call.get("object", "")
        call_type = call.get("type", "instance")
        
        implementations = []
        
        # 处理已知的Java标准库
        if self._is_java_standard_library(object_name):
            implementations.append({
                "file": None,
                "class": object_name,
                "type": "standard_library",
                "note": f"Java标准库: {object_name}.{method_name}"
            })
            return implementations
        
        # 查找项目中的实现
        if object_name:
            # Spring Service变量名到接口名的映射
            service_class_name = self._resolve_service_class_name_ast(object_name, current_file)
            
            # 查找直接的类实现
            class_file = self._find_file_by_name(f"{object_name}.java")
            if class_file:
                implementations.append({
                    "file": class_file,
                    "class": object_name,
                    "type": "concrete"
                })
            
            # 处理Service变量名映射
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
            
            # 通用Service接口处理
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
            
            # 查找接口的所有实现
            if object_name in self.interface_implementations:
                for impl in self.interface_implementations[object_name]:
                    implementations.append({
                        "file": impl["file"],
                        "class": impl["class"],
                        "type": "interface_implementation"
                    })
        
        # 在当前文件中查找本地方法
        if call_type == "direct":
            implementations.append({
                "file": current_file,
                "class": "current",
                "type": "local"
            })
        
        return implementations
    
    def _resolve_service_class_name_ast(self, variable_name: str, current_file: str) -> Optional[str]:
        """根据变量名解析Service类名 - AST版本"""
        # 常见的Spring Service变量名模式
        service_mappings = {
            "adminService": "UmsAdminService",
            "roleService": "UmsRoleService", 
            "userService": "UmsUserService",
            "menuService": "UmsMenuService",
            "resourceService": "UmsResourceService",
            "sheetMergeService": "SheetMergeService",  # 添加这个映射
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
