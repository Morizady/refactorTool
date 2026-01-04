#!/usr/bin/env python3
"""
基于JDT的深度调用链分析器 - 增强版
使用Eclipse JDT提供更精确的Java代码分析
支持深度调用树分析和类方法映射生成
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import logging
import re

from jdt_parser import JDTParser, JavaClass, JavaMethod

logger = logging.getLogger(__name__)

@dataclass
class MethodMapping:
    """方法映射信息"""
    interface_call: str  # 接口调用形式，如 sheetMergeService.merge()
    implementation_call: str  # 实现调用形式，如 SheetMergeServiceImpl.merge()
    import_statement: str  # import语句
    call_type: str  # 调用类型：direct, interface, inheritance, polymorphic
    line_number: int  # 调用行号
    file_path: str  # 调用文件路径

@dataclass
class CallTreeNode:
    """调用树节点"""
    method_name: str
    class_name: str
    package_name: str
    file_path: str
    line_number: int
    call_type: str  # direct, interface, inheritance, polymorphic, static
    parameters: List[str]
    return_type: str
    children: List['CallTreeNode']
    method_mappings: List[MethodMapping]
    depth: int

class JDTDeepCallChainAnalyzer:
    """基于JDT的深度调用链分析器 - 增强版"""
    
    def __init__(self, project_root: str, config_path: str = "config.yml"):
        self.project_root = Path(project_root)
        self.jdt_parser = JDTParser(config_path)
        self.analyzed_methods = set()  # 避免循环分析
        self.java_classes = {}  # 缓存解析的类
        self.interface_implementations = {}  # 接口实现映射
        self.class_hierarchy = {}  # 类继承关系
        self.package_imports = {}  # 包导入映射
        self.method_mappings = []  # 方法映射记录
        self.call_tree_cache = {}  # 调用树缓存
        
        # 初始化JDT并解析项目
        self._initialize_project()
    
    def _initialize_project(self):
        """初始化项目分析"""
        logger.info("🚀 初始化JDT深度调用链分析器...")
        
        # 尝试使用JDT解析整个项目
        try:
            self.java_classes = self.jdt_parser.parse_project(str(self.project_root))
        except Exception as e:
            logger.warning(f"JDT解析失败，使用备用解析方案: {e}")
            # self.java_classes = self._fallback_parse_project()
        
        if not self.java_classes:
            logger.warning("未能解析任何Java类，尝试备用解析方案")
            # self.java_classes = self._fallback_parse_project()
        
        # 构建类继承关系和接口实现映射
        self._build_class_relationships()
        
        # 构建包导入映射
        self._build_package_imports()
        
        logger.info(f"✅ JDT项目初始化完成: {len(self.java_classes)} 个类")
    
    def _fallback_parse_project(self) -> Dict[str, JavaClass]:
        """备用项目解析方案 - 使用正则表达式"""
        logger.info("🔄 使用备用解析方案...")
        
        java_classes = {}
        
        # 查找所有Java文件
        for java_file in self.project_root.rglob("*.java"):
            try:
                java_class = self._fallback_parse_file(str(java_file))
                if java_class:
                    key = f"{java_class.package}.{java_class.name}" if java_class.package else java_class.name
                    java_classes[key] = java_class
            except Exception as e:
                logger.debug(f"备用解析失败 {java_file}: {e}")
        
        return java_classes
    
    def _fallback_parse_file(self, file_path: str) -> Optional[JavaClass]:
        """备用文件解析方案 - 使用正则表达式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取包名
            package_match = re.search(r'package\s+([\w.]+)\s*;', content)
            package_name = package_match.group(1) if package_match else ""
            
            # 提取类名
            class_match = re.search(r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)', content)
            if not class_match:
                # 尝试接口
                class_match = re.search(r'(?:public\s+)?interface\s+(\w+)', content)
                if not class_match:
                    return None
            
            class_name = class_match.group(1)
            is_interface = 'interface' in class_match.group(0)
            
            # 提取继承和实现
            extends = None
            implements = []
            
            extends_match = re.search(r'extends\s+(\w+)', content)
            if extends_match:
                extends = extends_match.group(1)
            
            implements_matches = re.findall(r'implements\s+([\w\s,]+)', content)
            if implements_matches:
                implements = [impl.strip() for impl in implements_matches[0].split(',')]
            
            # 提取方法
            methods = []
            # 改进的方法匹配模式
            method_patterns = [
                r'(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?(?:\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{',
                r'(?:public|private|protected)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{',  # 构造函数
            ]
            
            for pattern in method_patterns:
                for match in re.finditer(pattern, content):
                    method_name = match.group(1)
                    
                    # 跳过明显不是方法的匹配
                    if method_name in ['class', 'interface', 'enum', 'if', 'for', 'while', 'switch']:
                        continue
                    
                    line_number = content[:match.start()].count('\n') + 1
                    
                    # 提取方法调用
                    method_calls = self._extract_method_calls_from_content(content, match.start(), match.end())
                    
                    method = JavaMethod(
                        name=method_name,
                        class_name=class_name,
                        file_path=file_path,
                        line_number=line_number,
                        method_calls=method_calls
                    )
                    methods.append(method)
            
            return JavaClass(
                name=class_name,
                package=package_name,
                file_path=file_path,
                line_number=1,
                extends=extends,
                implements=implements,
                methods=methods,
                is_interface=is_interface
            )
            
        except Exception as e:
            logger.debug(f"备用解析文件失败 {file_path}: {e}")
            return None
    
    def _extract_method_calls_from_content(self, content: str, start: int, end: int) -> List[Dict]:
        """从内容中提取方法调用"""
        calls = []
        
        # 找到方法体的结束位置
        brace_count = 0
        method_start = start
        method_end = len(content)
        
        for i in range(start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    method_end = i
                    break
        
        method_content = content[method_start:method_end]
        
        # 提取方法调用
        call_pattern = r'(\w+)\.(\w+)\s*\('
        for match in re.finditer(call_pattern, method_content):
            object_name = match.group(1)
            method_name = match.group(2)
            line_number = content[:method_start + match.start()].count('\n') + 1
            
            calls.append({
                "method": method_name,
                "object": object_name,
                "line": line_number,
                "arguments": 0,  # 简化处理
                "type": "instance"
            })
        
        return calls
    
    def _build_class_relationships(self):
        """构建类继承关系和接口实现映射"""
        logger.info("🔍 构建类继承关系和接口映射...")
        
        for class_key, java_class in self.java_classes.items():
            # 构建类继承关系
            self.class_hierarchy[java_class.name] = {
                'file': java_class.file_path,
                'package': java_class.package,
                'parent': java_class.extends,
                'interfaces': java_class.implements,
                'is_interface': java_class.is_interface,
                'is_abstract': java_class.is_abstract,
                'full_name': f"{java_class.package}.{java_class.name}" if java_class.package else java_class.name
            }
            
            # 建立接口到实现类的映射
            for interface in java_class.implements:
                if interface not in self.interface_implementations:
                    self.interface_implementations[interface] = []
                self.interface_implementations[interface].append({
                    'class': java_class.name,
                    'file': java_class.file_path,
                    'package': java_class.package,
                    'full_name': f"{java_class.package}.{java_class.name}" if java_class.package else java_class.name
                })
        
        interface_count = len(self.interface_implementations)
        class_count = len(self.class_hierarchy)
        logger.info(f"✅ 关系构建完成: {class_count} 个类, {interface_count} 个接口")
    
    def _build_package_imports(self):
        """构建包导入映射"""
        logger.info("🔍 构建包导入映射...")
        
        for java_class in self.java_classes.values():
            file_path = java_class.file_path
            
            # 读取文件获取import语句
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                imports = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('import ') and not line.startswith('import static'):
                        import_stmt = line.replace('import ', '').replace(';', '').strip()
                        imports.append(import_stmt)
                
                self.package_imports[file_path] = imports
                
            except Exception as e:
                logger.warning(f"读取文件导入失败 {file_path}: {e}")
                self.package_imports[file_path] = []
        
        logger.info(f"✅ 包导入映射构建完成: {len(self.package_imports)} 个文件")
    
    def analyze_deep_call_tree(self, file_path: str, method_name: str, max_depth: int = 6) -> CallTreeNode:
        """分析深度调用树并生成方法映射"""
        logger.info(f"🌳 开始深度调用树分析: {method_name}")
        
        # 清空之前的映射记录
        self.method_mappings = []
        self.analyzed_methods = set()
        
        # 查找目标方法
        target_method = self._find_method_in_file(file_path, method_name)
        if not target_method:
            logger.error(f"未找到目标方法: {method_name} in {file_path}")
            return None
        
        # 获取目标类信息
        target_class = self._find_class_by_file(file_path)
        if not target_class:
            logger.error(f"未找到目标类: {file_path}")
            return None
        
        # 构建根节点
        root_node = CallTreeNode(
            method_name=target_method.name,
            class_name=target_class.name,
            package_name=target_class.package,
            file_path=file_path,
            line_number=target_method.line_number,
            call_type="root",
            parameters=target_method.parameters,
            return_type=target_method.return_type,
            children=[],
            method_mappings=[],
            depth=0
        )
        
        # 递归分析调用树
        self._analyze_call_tree_recursive(root_node, target_method, max_depth)
        
        logger.info(f"✅ 深度调用树分析完成，共生成 {len(self.method_mappings)} 个方法映射")
        return root_node
    
    def _analyze_call_tree_recursive(self, parent_node: CallTreeNode, method: JavaMethod, max_depth: int):
        """递归分析调用树"""
        if parent_node.depth >= max_depth:
            return
        
        method_key = f"{method.class_name}.{method.name}:{parent_node.depth}"
        if method_key in self.analyzed_methods:
            return
        
        self.analyzed_methods.add(method_key)
        
        indent = "  " * parent_node.depth
        logger.info(f"{indent}🔍 分析方法调用: {method.name} (深度: {parent_node.depth})")
        
        # 分析方法中的所有调用
        for call in method.method_calls:
            child_nodes = self._resolve_method_call(call, method.file_path, parent_node.depth + 1)
            
            for child_node in child_nodes:
                parent_node.children.append(child_node)
                
                # 生成方法映射
                mapping = self._generate_method_mapping(call, child_node, method.file_path)
                if mapping:
                    parent_node.method_mappings.append(mapping)
                    self.method_mappings.append(mapping)
                
                # 递归分析子方法
                child_method = self._find_method_by_signature(
                    child_node.class_name, 
                    child_node.method_name
                )
                if child_method:
                    self._analyze_call_tree_recursive(child_node, child_method, max_depth)
    
    def _resolve_method_call(self, call: Dict, current_file: str, depth: int) -> List[CallTreeNode]:
        """解析方法调用，处理多态和继承"""
        method_name = call["method"]
        object_name = call.get("object", "")
        call_type = call.get("type", "instance")
        line_number = call.get("line", 0)
        
        nodes = []
        
        # 处理直接调用
        if call_type == "direct" or not object_name:
            current_class = self._find_class_by_file(current_file)
            if current_class:
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=current_class.name,
                    package_name=current_class.package,
                    file_path=current_file,
                    line_number=line_number,
                    call_type="direct",
                    parameters=call.get("arguments", []),
                    return_type="",
                    children=[],
                    method_mappings=[],
                    depth=depth
                )
                nodes.append(node)
        
    def _resolve_method_call(self, call: Dict, current_file: str, depth: int) -> List[CallTreeNode]:
        """解析方法调用，处理多态和继承"""
        method_name = call["method"]
        object_name = call.get("object", "")
        call_type = call.get("type", "instance")
        line_number = call.get("line", 0)
        arguments = call.get("arguments", 0)
        
        nodes = []
        
        # 处理构造函数调用
        if call_type == "constructor":
            # 构造函数调用，object_name是类型名
            class_name = object_name
            node = CallTreeNode(
                method_name="<init>",
                class_name=class_name,
                package_name="",  # 需要从imports解析
                file_path="",
                line_number=line_number,
                call_type="constructor",
                parameters=[f"arg{i}" for i in range(arguments)],
                return_type=class_name,
                children=[],
                method_mappings=[],
                depth=depth
            )
            nodes.append(node)
            return nodes
        
        # 处理静态方法调用或实例方法调用
        if object_name:
            # 检查是否是已知的工具类静态方法
            if self._is_utility_class(object_name):
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=object_name,
                    package_name="",  # 工具类包名
                    file_path="",
                    line_number=line_number,
                    call_type="static",
                    parameters=[f"arg{i}" for i in range(arguments)],
                    return_type="",
                    children=[],
                    method_mappings=[],
                    depth=depth
                )
                nodes.append(node)
                return nodes
            
            # 处理实例方法调用
            # 解析变量类型
            variable_type = self._resolve_variable_type(object_name, current_file)
            
            if variable_type:
                # 查找所有可能的实现
                implementations = self._find_all_implementations(variable_type, method_name)
                
                for impl in implementations:
                    node = CallTreeNode(
                        method_name=method_name,
                        class_name=impl["class"],
                        package_name=impl["package"],
                        file_path=impl["file"],
                        line_number=line_number,
                        call_type=impl["call_type"],
                        parameters=[f"arg{i}" for i in range(arguments)],
                        return_type="",
                        children=[],
                        method_mappings=[],
                        depth=depth
                    )
                    nodes.append(node)
            else:
                # 无法解析变量类型，创建一个通用节点
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=object_name,
                    package_name="",
                    file_path="",
                    line_number=line_number,
                    call_type="unresolved",
                    parameters=[f"arg{i}" for i in range(arguments)],
                    return_type="",
                    children=[],
                    method_mappings=[],
                    depth=depth
                )
                nodes.append(node)
        else:
            # 直接方法调用（同类中的方法）
            current_class = self._find_class_by_file(current_file)
            if current_class:
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=current_class.name,
                    package_name=current_class.package,
                    file_path=current_file,
                    line_number=line_number,
                    call_type="direct",
                    parameters=[f"arg{i}" for i in range(arguments)],
                    return_type="",
                    children=[],
                    method_mappings=[],
                    depth=depth
                )
                nodes.append(node)
        
        return nodes
    
    def _is_utility_class(self, class_name: str) -> bool:
        """检查是否是工具类"""
        utility_classes = {
            "StringUtils", "MapUtils", "CollectionUtils", "NumberUtils",
            "DateUtils", "FileUtils", "IOUtils", "System", "Math",
            "Arrays", "Collections", "Objects", "Optional"
        }
        return class_name in utility_classes
    
    def _resolve_variable_type(self, variable_name: str, current_file: str) -> Optional[str]:
        """解析变量类型，支持字段注入和局部变量"""
        current_class = self._find_class_by_file(current_file)
        if not current_class:
            return None
        
        # 1. 检查字段声明
        for field in current_class.fields:
            if field.get("name") == variable_name:
                return field.get("type")
        
        # 2. Spring Service变量名映射
        service_type = self._resolve_service_class_name_jdt(variable_name, current_file)
        if service_type:
            return service_type
        
        # 3. 从import语句推断
        imports = self.package_imports.get(current_file, [])
        for import_stmt in imports:
            class_name = import_stmt.split('.')[-1]
            if variable_name.lower().startswith(class_name.lower().replace("impl", "")):
                return class_name
        
        return None
    
    def _find_all_implementations(self, type_name: str, method_name: str) -> List[Dict]:
        """查找类型的所有实现，处理接口、继承和多态"""
        implementations = []
        
        # 1. 直接类实现
        for java_class in self.java_classes.values():
            if java_class.name == type_name:
                if self._class_has_method(java_class, method_name):
                    implementations.append({
                        "class": java_class.name,
                        "package": java_class.package,
                        "file": java_class.file_path,
                        "call_type": "concrete"
                    })
        
        # 2. 接口实现
        if type_name in self.interface_implementations:
            for impl in self.interface_implementations[type_name]:
                impl_class = self._find_class_by_name(impl["class"])
                if impl_class and self._class_has_method(impl_class, method_name):
                    implementations.append({
                        "class": impl["class"],
                        "package": impl["package"],
                        "file": impl["file"],
                        "call_type": "interface"
                    })
        
        # 3. 继承实现
        for java_class in self.java_classes.values():
            if java_class.extends == type_name:
                if self._class_has_method(java_class, method_name):
                    implementations.append({
                        "class": java_class.name,
                        "package": java_class.package,
                        "file": java_class.file_path,
                        "call_type": "inheritance"
                    })
        
        # 4. Service接口到实现类的映射
        if type_name.endswith("Service"):
            impl_name = type_name + "Impl"
            impl_class = self._find_class_by_name(impl_name)
            if impl_class and self._class_has_method(impl_class, method_name):
                implementations.append({
                    "class": impl_class.name,
                    "package": impl_class.package,
                    "file": impl_class.file_path,
                    "call_type": "service_impl"
                })
        
        return implementations
    
    def _class_has_method(self, java_class: JavaClass, method_name: str) -> bool:
        """检查类是否有指定方法"""
        for method in java_class.methods:
            if method.name == method_name:
                return True
        return False
    
    def _find_class_by_name(self, class_name: str) -> Optional[JavaClass]:
        """根据类名查找Java类"""
        for java_class in self.java_classes.values():
            if java_class.name == class_name:
                return java_class
        return None
    
    def _find_method_by_signature(self, class_name: str, method_name: str) -> Optional[JavaMethod]:
        """根据类名和方法名查找方法"""
        java_class = self._find_class_by_name(class_name)
        if java_class:
            for method in java_class.methods:
                if method.name == method_name:
                    return method
        return None
    
    def _generate_method_mapping(self, call: Dict, node: CallTreeNode, current_file: str) -> Optional[MethodMapping]:
        """生成方法映射信息"""
        object_name = call.get("object", "")
        method_name = call["method"]
        
        if not object_name:
            return None
        
        # 构建接口调用形式
        interface_call = f"{object_name}.{method_name}()"
        
        # 构建实现调用形式
        implementation_call = f"{node.class_name}.{method_name}()"
        
        # 构建import语句
        import_statement = f"import {node.package_name}.{node.class_name};" if node.package_name else f"import {node.class_name};"
        
        return MethodMapping(
            interface_call=interface_call,
            implementation_call=implementation_call,
            import_statement=import_statement,
            call_type=node.call_type,
            line_number=call.get("line", 0),
            file_path=current_file
        )
    def generate_call_tree_report(self, call_tree: CallTreeNode, endpoint_path: str, output_dir: str = "./migration_output") -> str:
        """生成深度调用树报告"""
        if not call_tree:
            return ""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成Markdown报告
        md_content = self._build_call_tree_markdown(call_tree, endpoint_path)
        md_file = f"{output_dir}/deep_call_tree_{call_tree.method_name}_jdt.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 生成方法映射文件
        mapping_file = f"{output_dir}/method_mappings_{call_tree.method_name}_jdt.json"
        self._save_method_mappings(mapping_file)
        
        # 生成import语句文件
        import_file = f"{output_dir}/import_statements_{call_tree.method_name}_jdt.txt"
        self._save_import_statements(import_file)
        
        logger.info(f"✅ 报告生成完成:")
        logger.info(f"  - 调用树: {md_file}")
        logger.info(f"  - 方法映射: {mapping_file}")
        logger.info(f"  - Import语句: {import_file}")
        
        return md_file
    
    def _build_call_tree_markdown(self, call_tree: CallTreeNode, endpoint_path: str) -> str:
        """构建调用树Markdown内容"""
        lines = []
        
        # 标题
        lines.append(f"# {endpoint_path} 深度调用树分析 (JDT)")
        lines.append("")
        lines.append(f"**分析时间**: {self._get_current_time()}")
        lines.append(f"**解析方法**: Eclipse JDT")
        lines.append(f"**根方法**: {call_tree.class_name}.{call_tree.method_name}()")
        lines.append("")
        
        # 统计信息
        total_calls = self._count_total_calls(call_tree)
        max_depth = self._get_max_depth(call_tree)
        unique_classes = self._count_unique_classes(call_tree)
        
        lines.append("## 统计信息")
        lines.append("")
        lines.append(f"- **总调用数**: {total_calls}")
        lines.append(f"- **最大深度**: {max_depth}")
        lines.append(f"- **涉及类数**: {unique_classes}")
        lines.append(f"- **方法映射数**: {len(self.method_mappings)}")
        lines.append("")
        
        # 调用树可视化
        lines.append("## 深度调用树")
        lines.append("")
        lines.append("```")
        self._build_tree_visualization(call_tree, lines, "")
        lines.append("```")
        lines.append("")
        
        # 方法映射详情
        lines.append("## 方法映射详情")
        lines.append("")
        
        if self.method_mappings:
            lines.append("| 接口调用 | 实现调用 | 调用类型 | 文件位置 |")
            lines.append("|----------|----------|----------|----------|")
            
            for mapping in self.method_mappings[:20]:  # 限制显示数量
                lines.append(f"| `{mapping.interface_call}` | `{mapping.implementation_call}` | {mapping.call_type} | {Path(mapping.file_path).name}:{mapping.line_number} |")
            
            if len(self.method_mappings) > 20:
                lines.append(f"| ... | ... | ... | 还有 {len(self.method_mappings) - 20} 个映射 |")
        else:
            lines.append("无方法映射")
        
        lines.append("")
        
        # 多态和继承分析
        lines.append("## 多态和继承分析")
        lines.append("")
        self._build_polymorphism_analysis(call_tree, lines)
        
        # Import语句汇总
        lines.append("## Import语句汇总")
        lines.append("")
        unique_imports = set()
        for mapping in self.method_mappings:
            unique_imports.add(mapping.import_statement)
        
        if unique_imports:
            lines.append("```java")
            for import_stmt in sorted(unique_imports):
                lines.append(import_stmt)
            lines.append("```")
        else:
            lines.append("无需要的import语句")
        
        lines.append("")
        
        # 性能分析
        lines.append("## 性能分析")
        lines.append("")
        self._build_performance_analysis(call_tree, lines)
        
        return "\n".join(lines)
    
    def _build_tree_visualization(self, node: CallTreeNode, lines: List[str], prefix: str):
        """构建树形可视化"""
        # 构建当前节点显示
        node_display = f"{node.class_name}.{node.method_name}()"
        type_marker = ""
        
        if node.call_type == "interface":
            type_marker = " [接口]"
        elif node.call_type == "inheritance":
            type_marker = " [继承]"
        elif node.call_type == "service_impl":
            type_marker = " [Service实现]"
        elif node.call_type == "concrete":
            type_marker = " [具体类]"
        elif node.call_type == "direct":
            type_marker = " [直接调用]"
        
        lines.append(f"{prefix}├── {node_display}{type_marker}")
        
        # 递归处理子节点
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._build_tree_visualization(child, lines, child_prefix)
    
    def _build_polymorphism_analysis(self, call_tree: CallTreeNode, lines: List[str]):
        """构建多态和继承分析"""
        interface_calls = []
        inheritance_calls = []
        polymorphic_calls = []
        
        def collect_calls(node: CallTreeNode):
            if node.call_type == "interface":
                interface_calls.append(node)
            elif node.call_type == "inheritance":
                inheritance_calls.append(node)
            elif node.call_type in ["service_impl", "polymorphic"]:
                polymorphic_calls.append(node)
            
            for child in node.children:
                collect_calls(child)
        
        collect_calls(call_tree)
        
        if interface_calls:
            lines.append("### 接口调用")
            for call in interface_calls[:5]:
                lines.append(f"- **{call.method_name}**: {call.class_name} (实现接口)")
            if len(interface_calls) > 5:
                lines.append(f"- ... 还有 {len(interface_calls) - 5} 个接口调用")
            lines.append("")
        
        if inheritance_calls:
            lines.append("### 继承调用")
            for call in inheritance_calls[:5]:
                lines.append(f"- **{call.method_name}**: {call.class_name} (继承实现)")
            if len(inheritance_calls) > 5:
                lines.append(f"- ... 还有 {len(inheritance_calls) - 5} 个继承调用")
            lines.append("")
        
        if polymorphic_calls:
            lines.append("### 多态调用")
            for call in polymorphic_calls[:5]:
                lines.append(f"- **{call.method_name}**: {call.class_name} (多态实现)")
            if len(polymorphic_calls) > 5:
                lines.append(f"- ... 还有 {len(polymorphic_calls) - 5} 个多态调用")
            lines.append("")
    
    def _build_performance_analysis(self, call_tree: CallTreeNode, lines: List[str]):
        """构建性能分析"""
        total_calls = self._count_total_calls(call_tree)
        max_depth = self._get_max_depth(call_tree)
        
        if total_calls > 50:
            lines.append("⚠️ **高复杂度**: 调用链非常复杂，强烈建议重构")
        elif total_calls > 30:
            lines.append("⚡ **中高复杂度**: 调用链较深，建议考虑重构")
        elif total_calls > 15:
            lines.append("⚡ **中等复杂度**: 调用链适中，注意性能监控")
        else:
            lines.append("✅ **简单接口**: 调用链简洁，性能良好")
        
        lines.append("")
        lines.append("### 优化建议")
        lines.append("")
        
        if max_depth > 6:
            lines.append("1. **减少调用深度**: 考虑合并相似的服务层调用")
        
        interface_count = len([m for m in self.method_mappings if m.call_type == "interface"])
        if interface_count > 10:
            lines.append("2. **接口优化**: 考虑使用具体实现类减少接口调用开销")
        
        lines.append("3. **缓存策略**: 对重复调用的方法结果进行缓存")
        lines.append("4. **异步处理**: 对于耗时操作考虑异步处理")
        lines.append("5. **批量操作**: 减少数据库交互次数")
    
    def _save_method_mappings(self, file_path: str):
        """保存方法映射到JSON文件"""
        mappings_data = []
        for mapping in self.method_mappings:
            mappings_data.append({
                "interface_call": mapping.interface_call,
                "implementation_call": mapping.implementation_call,
                "import_statement": mapping.import_statement,
                "call_type": mapping.call_type,
                "line_number": mapping.line_number,
                "file_path": mapping.file_path
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(mappings_data, f, indent=2, ensure_ascii=False)
    
    def _save_import_statements(self, file_path: str):
        """保存import语句到文本文件"""
        unique_imports = set()
        for mapping in self.method_mappings:
            unique_imports.add(mapping.import_statement)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("// 深度调用树分析生成的Import语句\n")
            f.write("// 根据实际需要添加到对应的Java文件中\n\n")
            
            for import_stmt in sorted(unique_imports):
                f.write(import_stmt + "\n")
    
    def _count_total_calls(self, node: CallTreeNode) -> int:
        """计算总调用数"""
        count = 1
        for child in node.children:
            count += self._count_total_calls(child)
        return count
    
    def _get_max_depth(self, node: CallTreeNode) -> int:
        """获取最大深度"""
        if not node.children:
            return node.depth
        
        max_child_depth = max(self._get_max_depth(child) for child in node.children)
        return max_child_depth
    
    def _count_unique_classes(self, node: CallTreeNode) -> int:
        """计算涉及的唯一类数"""
        classes = set()
        
        def collect_classes(n: CallTreeNode):
            classes.add(n.class_name)
            for child in n.children:
                collect_classes(child)
        
        collect_classes(node)
        return len(classes)
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def analyze_method_calls(self, file_path: str, method_name: str, depth: int = 0, max_depth: int = 4) -> Dict:
        if depth > max_depth:
            return {"note": "达到最大深度限制"}
        
        method_key = f"{file_path}:{method_name}:{depth}"
        if method_key in self.analyzed_methods:
            return {"note": "已分析过，避免循环引用"}
        
        indent = "  " * depth
        logger.info(f"{indent}🔍 JDT分析方法: {method_name} (深度: {depth})")
        
        self.analyzed_methods.add(method_key)
        
        try:
            # 查找目标方法
            target_method = self._find_method_in_file(file_path, method_name)
            if not target_method:
                return {"error": f"未找到方法: {method_name} in {file_path}"}
            
            # 使用JDT提取的方法调用信息
            method_calls = target_method.method_calls
            
            # 去重和过滤方法调用
            unique_calls = self._deduplicate_method_calls(method_calls)
            logger.info(f"{indent}  📋 找到 {len(method_calls)} 个方法调用，去重后 {len(unique_calls)} 个")
            
            # 递归分析每个调用
            detailed_calls = []
            for i, call in enumerate(unique_calls, 1):
                if len(unique_calls) > 5 and i % 5 == 0:
                    logger.info(f"{indent}  📊 处理调用进度: {i}/{len(unique_calls)}")
                
                call_detail = {
                    "method": call["method"],
                    "object": call.get("object", ""),
                    "line": call.get("line", 0),
                    "arguments": call.get("arguments", 0),
                    "type": call.get("type", "instance")
                }
                
                # 查找方法实现
                implementations = self._find_method_implementations_jdt(call, file_path)
                
                if implementations:
                    call_detail["implementations"] = []
                    
                    for impl in implementations:
                        impl_detail = {
                            "file": impl["file"],
                            "class": impl.get("class", ""),
                            "type": impl.get("type", "concrete"),
                            "package": impl.get("package", "")
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
            
            logger.info(f"{indent}✅ JDT方法 {method_name} 分析完成")
            return {
                "file": file_path,
                "method": method_name,
                "calls": detailed_calls,
                "depth": depth,
                "parse_method": "jdt"
            }
            
        except Exception as e:
            logger.error(f"{indent}❌ JDT分析失败: {str(e)}")
            return {"error": f"JDT分析失败: {str(e)}"}
    
    def _find_method_in_file(self, file_path: str, method_name: str) -> Optional[JavaMethod]:
        """在指定文件中查找方法"""
        # 根据文件路径查找对应的Java类
        java_class = self._find_class_by_file(file_path)
        if java_class:
            for method in java_class.methods:
                if method.name == method_name:
                    return method
        return None
    
    def _deduplicate_method_calls(self, method_calls: List[Dict]) -> List[Dict]:
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
    
    def _find_method_implementations_jdt(self, call: Dict, current_file: str) -> List[Dict]:
        """使用JDT信息查找方法的所有实现"""
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
            # 直接查找类名匹配的实现
            for java_class in self.java_classes.values():
                if java_class.name == object_name:
                    # 检查是否有对应的方法
                    for method in java_class.methods:
                        if method.name == method_name:
                            implementations.append({
                                "file": java_class.file_path,
                                "class": java_class.name,
                                "package": java_class.package,
                                "type": "concrete"
                            })
                            break
            
            # Spring Service变量名到接口名的映射
            service_class_name = self._resolve_service_class_name_jdt(object_name, current_file)
            if service_class_name:
                # 查找Service接口和实现
                for java_class in self.java_classes.values():
                    if java_class.name == service_class_name:
                        implementations.append({
                            "file": java_class.file_path,
                            "class": java_class.name,
                            "package": java_class.package,
                            "type": "service_interface" if java_class.is_interface else "service_implementation"
                        })
                    elif java_class.name == service_class_name + "Impl":
                        implementations.append({
                            "file": java_class.file_path,
                            "class": java_class.name,
                            "package": java_class.package,
                            "type": "service_implementation"
                        })
            
            # 查找接口的所有实现
            if object_name in self.interface_implementations:
                for impl in self.interface_implementations[object_name]:
                    implementations.append({
                        "file": impl["file"],
                        "class": impl["class"],
                        "package": impl["package"],
                        "type": "interface_implementation"
                    })
        
        # 在当前文件中查找本地方法
        if call_type == "direct":
            current_class = self._find_class_by_file(current_file)
            if current_class:
                for method in current_class.methods:
                    if method.name == method_name:
                        implementations.append({
                            "file": current_file,
                            "class": current_class.name,
                            "package": current_class.package,
                            "type": "local"
                        })
                        break
        
        return implementations
    
    def _find_class_by_file(self, file_path: str) -> Optional[JavaClass]:
        """根据文件路径查找Java类"""
        # 标准化文件路径
        file_path = os.path.normpath(file_path)
        
        for java_class in self.java_classes.values():
            class_file_path = os.path.normpath(java_class.file_path)
            if class_file_path == file_path:
                return java_class
        
        # 如果直接匹配失败，尝试文件名匹配
        target_filename = os.path.basename(file_path)
        for java_class in self.java_classes.values():
            class_filename = os.path.basename(java_class.file_path)
            if class_filename == target_filename:
                return java_class
        
        return None
    
    def _resolve_service_class_name_jdt(self, variable_name: str, current_file: str) -> Optional[str]:
        """根据变量名解析Service类名 - JDT版本"""
        # 常见的Spring Service变量名模式
        service_mappings = {
            "adminService": "UmsAdminService",
            "roleService": "UmsRoleService", 
            "userService": "UmsUserService",
            "menuService": "UmsMenuService",
            "resourceService": "UmsResourceService",
            "sheetMergeService": "SheetMergeService",
        }
        
        # 直接映射
        if variable_name in service_mappings:
            return service_mappings[variable_name]
        
        # 模式匹配：xxxService -> XxxService
        if variable_name.endswith("Service"):
            # 将首字母大写
            class_name = variable_name[0].upper() + variable_name[1:]
            return class_name
        
        # 尝试从当前文件的Java类中解析@Autowired注解
        current_class = self._find_class_by_file(current_file)
        if current_class:
            # 查找字段声明中的类型信息
            for field in current_class.fields:
                if field.get("name") == variable_name:
                    return field.get("type")
        
        return None
    
    def _is_java_standard_library(self, class_name: str) -> bool:
        """判断是否是Java标准库类"""
        standard_classes = {
            'System', 'String', 'Integer', 'Long', 'Double', 'Float', 'Boolean',
            'Date', 'Calendar', 'HashMap', 'ArrayList', 'List', 'Map', 'Set',
            'Thread', 'Object', 'Class', 'Math', 'Random', 'StringBuilder',
            'StringBuffer', 'Collections', 'Arrays', 'Optional', 'Stream'
        }
        return class_name in standard_classes
    
    def get_class_hierarchy(self) -> Dict[str, Dict]:
        """获取类继承关系"""
        return self.class_hierarchy.copy()
    
    def get_interface_implementations(self) -> Dict[str, List]:
        """获取接口实现映射"""
        return self.interface_implementations.copy()
    
    def get_project_statistics(self) -> Dict:
        """获取项目统计信息"""
        stats = {
            "total_classes": len(self.java_classes),
            "interfaces": sum(1 for cls in self.java_classes.values() if cls.is_interface),
            "abstract_classes": sum(1 for cls in self.java_classes.values() if cls.is_abstract),
            "concrete_classes": sum(1 for cls in self.java_classes.values() if not cls.is_interface and not cls.is_abstract),
            "total_methods": sum(len(cls.methods) for cls in self.java_classes.values()),
            "packages": len(set(cls.package for cls in self.java_classes.values() if cls.package))
        }
        return stats
    
    def find_spring_endpoints(self) -> List[Dict]:
        """查找Spring Boot接口端点"""
        endpoints = []
        
        for java_class in self.java_classes.values():
            # 检查是否是Controller类
            is_controller = any(
                annotation in ["@RestController", "@Controller"] 
                for annotation in java_class.annotations
            )
            
            if not is_controller:
                continue
            
            # 获取类级别的RequestMapping
            base_path = ""
            for annotation in java_class.annotations:
                if annotation.startswith("@RequestMapping"):
                    # 解析路径
                    import re
                    path_match = re.search(r'["\']([^"\']+)["\']', annotation)
                    if path_match:
                        base_path = path_match.group(1)
            
            # 分析每个方法
            for method in java_class.methods:
                endpoint_info = self._extract_endpoint_info(method, base_path, java_class)
                if endpoint_info:
                    endpoints.append(endpoint_info)
        
        return endpoints
    
    def _extract_endpoint_info(self, method: JavaMethod, base_path: str, java_class: JavaClass) -> Optional[Dict]:
        """提取端点信息"""
        # 查找HTTP映射注解
        http_method = None
        endpoint_path = ""
        
        for annotation in method.annotations:
            if annotation.startswith("@GetMapping"):
                http_method = "GET"
            elif annotation.startswith("@PostMapping"):
                http_method = "POST"
            elif annotation.startswith("@PutMapping"):
                http_method = "PUT"
            elif annotation.startswith("@DeleteMapping"):
                http_method = "DELETE"
            elif annotation.startswith("@RequestMapping"):
                # 需要解析method和value
                http_method = "GET"  # 默认
            
            if http_method:
                # 解析路径
                import re
                path_match = re.search(r'["\']([^"\']+)["\']', annotation)
                if path_match:
                    endpoint_path = path_match.group(1)
                break
        
        if not http_method:
            return None
        
        # 构建完整路径
        full_path = base_path + endpoint_path if base_path else endpoint_path
        
        return {
            "name": f"{java_class.name}.{method.name}",
            "path": full_path,
            "method": http_method,
            "controller": java_class.name,
            "handler": method.name,
            "file_path": method.file_path,
            "line_number": method.line_number,
            "parameters": method.parameters,
            "return_type": method.return_type,
            "framework": "spring"
        }
    
    def shutdown(self):
        """关闭JDT环境"""
        if self.jdt_parser:
            self.jdt_parser.shutdown()


# 使用示例
def test_jdt_call_chain_analyzer():
    """测试JDT调用链分析器"""
    project_path = "test_projects/sc_pcc_business"
    
    if not os.path.exists(project_path):
        print(f"测试项目不存在: {project_path}")
        return
    
    analyzer = JDTDeepCallChainAnalyzer(project_path)
    
    # 获取项目统计
    stats = analyzer.get_project_statistics()
    print("项目统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 查找Spring端点
    endpoints = analyzer.find_spring_endpoints()
    print(f"\n找到 {len(endpoints)} 个Spring端点:")
    for endpoint in endpoints[:5]:  # 只显示前5个
        print(f"  {endpoint['method']} {endpoint['path']} -> {endpoint['handler']}")
    
    # 测试方法调用分析
    if endpoints:
        endpoint = endpoints[0]
        print(f"\n分析端点: {endpoint['name']}")
        call_analysis = analyzer.analyze_method_calls(
            endpoint['file_path'], 
            endpoint['handler'], 
            max_depth=3
        )
        print(f"调用分析结果: {len(call_analysis.get('calls', []))} 个调用")
    
    analyzer.shutdown()


if __name__ == "__main__":
    test_jdt_call_chain_analyzer()