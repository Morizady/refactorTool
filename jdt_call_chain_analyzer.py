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
    resolved_type: str = ""  # JDT解析出的实际类型

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
    
    def __init__(self, project_root: str, config_path: str = "config.yml", ignore_methods_file: str = "igonre_method.txt", show_getters_setters: bool = True, show_constructors: bool = True):
        self.project_root = Path(project_root)
        self.jdt_parser = JDTParser(config_path)
        self.analyzed_methods = set()  # 避免循环分析
        self.java_classes = {}  # 缓存解析的类
        self.interface_implementations = {}  # 接口实现映射
        self.class_hierarchy = {}  # 类继承关系
        self.package_imports = {}  # 包导入映射
        self.method_mappings = []  # 方法映射记录
        self.call_tree_cache = {}  # 调用树缓存
        self.ignore_methods = set()  # 忽略的方法名列表
        self.show_getters_setters = show_getters_setters  # 是否显示getter/setter方法
        self.show_constructors = show_constructors  # 是否显示构造函数
        
        # 加载忽略方法列表
        self._load_ignore_methods(ignore_methods_file)
        
        # 初始化JDT并解析项目
        self._initialize_project()
    
    def _is_simple_getter_or_setter(self, method_name: str, class_name: str, current_file: str) -> bool:
        """
        判断方法是否是简单的getter或setter方法
        简单getter/setter的特征：方法内部没有其他方法调用（只是return field或field = value）
        """
        if not method_name:
            return False
        
        # 首先检查方法名是否符合getter/setter模式
        is_getter_pattern = False
        is_setter_pattern = False
        
        if len(method_name) > 3:
            if method_name.startswith('get') and method_name[3].isupper():
                is_getter_pattern = True
            if method_name.startswith('set') and method_name[3].isupper():
                is_setter_pattern = True
        if len(method_name) > 2:
            if method_name.startswith('is') and method_name[2].isupper():
                is_getter_pattern = True
        
        # 如果方法名不符合getter/setter模式，直接返回False
        if not is_getter_pattern and not is_setter_pattern:
            return False
        
        # 查找该方法，检查是否有子调用
        java_class = self._find_class_by_name(class_name, current_file)
        if not java_class:
            # 如果找不到类（外部类），假设是简单getter/setter
            return True
        
        for method in java_class.methods:
            if method.name == method_name:
                # 如果方法内部没有方法调用，则认为是简单getter/setter
                if not method.method_calls or len(method.method_calls) == 0:
                    return True
                # 如果只有很少的调用（比如日志），也可能是getter/setter
                # 但为了安全起见，只要有调用就认为不是简单getter/setter
                return False
        
        # 如果找不到方法定义（可能是继承的），假设是简单getter/setter
        return True
    
    def _filter_chain_calls(self, children: list) -> list:
        """
        过滤链式调用，只保留最长的调用链
        例如：wapper.eq().eq().orderBy().last() 和 wapper.eq().eq().orderBy() 和 wapper.eq().eq() 和 wapper.eq()
        只保留最长的 wapper.eq().eq().orderBy().last()
        """
        if not children:
            return children
        
        # 分离链式调用和非链式调用
        chain_calls = []  # [(child_node, mapping, full_call_str)]
        non_chain_calls = []
        
        for child_node, mapping in children:
            # 构建完整的调用字符串
            full_call = f"{child_node.class_name}.{child_node.method_name}()"
            
            # 检查是否是链式调用（class_name中包含点号或括号）
            if child_node.call_type == "chain_call" or '.' in child_node.class_name or '(' in child_node.class_name:
                chain_calls.append((child_node, mapping, full_call))
            else:
                non_chain_calls.append((child_node, mapping))
        
        # 对链式调用进行去重，只保留最长的
        filtered_chain_calls = []
        
        # 按调用字符串长度降序排序
        chain_calls.sort(key=lambda x: len(x[2]), reverse=True)
        
        # 记录已经被包含的较短调用
        covered_calls = set()
        
        for child_node, mapping, full_call in chain_calls:
            # 检查这个调用是否是某个更长调用的子串
            is_substring = False
            for covered in covered_calls:
                # 检查当前调用是否是已覆盖调用的前缀部分
                # 例如 "wapper.eq().eq()" 是 "wapper.eq().eq().orderBy()" 的前缀
                if self._is_chain_prefix(full_call, covered):
                    is_substring = True
                    break
            
            if not is_substring:
                filtered_chain_calls.append((child_node, mapping))
                covered_calls.add(full_call)
        
        # 合并结果
        return non_chain_calls + filtered_chain_calls
    
    def _is_chain_prefix(self, shorter: str, longer: str) -> bool:
        """
        检查shorter是否是longer的链式调用前缀
        例如：wapper.eq() 是 wapper.eq().eq() 的前缀
        """
        if shorter == longer:
            return False
        
        # 移除末尾的()进行比较
        shorter_base = shorter.rstrip('()')
        longer_base = longer.rstrip('()')
        
        # 检查shorter_base是否是longer_base的前缀，且后面跟着.或()
        if longer_base.startswith(shorter_base):
            remaining = longer_base[len(shorter_base):]
            # 剩余部分应该以.开头（表示链式调用继续）
            if remaining.startswith('.') or remaining.startswith('()'):
                return True
        
        return False
    
    def _load_ignore_methods(self, ignore_methods_file: str):
        """加载忽略方法列表"""
        try:
            if os.path.exists(ignore_methods_file):
                with open(ignore_methods_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        method_name = line.strip()
                        if method_name and not method_name.startswith('#'):
                            self.ignore_methods.add(method_name)
                logger.info(f"✅ 加载忽略方法列表: {len(self.ignore_methods)} 个方法")
                
                # 显示一些加载的忽略规则（调试用）
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("📋 忽略方法列表:")
                    for method in sorted(self.ignore_methods):
                        logger.debug(f"  - {method}")
            else:
                logger.info(f"⚠️ 忽略方法文件不存在: {ignore_methods_file}")
        except Exception as e:
            logger.warning(f"加载忽略方法列表失败: {e}")
    
    def _should_ignore_method(self, method_name: str, class_name: str = "", current_file: str = "", call_type: str = "") -> bool:
        """
        检查方法是否应该被忽略
        
        Args:
            method_name: 方法名
            class_name: 类名（用于判断是否是简单getter/setter）
            current_file: 当前文件路径（用于查找类定义）
            call_type: 调用类型（用于判断是否是构造函数）
        """
        # 检查是否在忽略列表中（支持方法名和类名.方法名两种格式）
        if method_name in self.ignore_methods:
            logger.debug(f"🚫 忽略方法（方法名匹配）: {method_name}")
            return True
        
        # 检查类名.方法名格式
        if class_name:
            full_method_name = f"{class_name}.{method_name}"
            if full_method_name in self.ignore_methods:
                logger.debug(f"🚫 忽略方法（完整匹配）: {full_method_name}")
                return True
            
            # 也检查简单类名.方法名格式（去掉包名）
            simple_class_name = class_name.split('.')[-1] if '.' in class_name else class_name
            simple_full_method_name = f"{simple_class_name}.{method_name}"
            if simple_full_method_name in self.ignore_methods:
                logger.debug(f"🚫 忽略方法（简单类名匹配）: {simple_full_method_name}")
                return True
        
        # 如果配置不显示构造函数，检查是否是构造函数调用
        if not self.show_constructors and (call_type == "constructor" or method_name == "<init>"):
            logger.debug(f"🚫 忽略构造函数: {method_name}")
            return True
        # 如果配置不显示getter/setter，检查是否是简单的getter/setter方法
        if not self.show_getters_setters and self._is_simple_getter_or_setter(method_name, class_name, current_file):
            logger.debug(f"🚫 忽略getter/setter: {method_name}")
            return True
        
        # 调试信息：显示未被忽略的方法
        if method_name == "execute" and class_name:
            logger.debug(f"🔍 检查方法: {class_name}.{method_name} - 未被忽略")
            logger.debug(f"  - 忽略列表包含: {sorted([m for m in self.ignore_methods if 'execute' in m])}")
        
        return False
    
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
        
        self.static_imports = {}  # 静态导入映射: {file_path: {method_name: full_class_path}}
        self.import_line_numbers = {}  # import语句行号映射: {file_path: {import_stmt: line_number}}
        
        for java_class in self.java_classes.values():
            file_path = java_class.file_path
            
            # 读取文件获取import语句
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                imports = []
                static_imports = {}  # 当前文件的静态导入
                import_lines = {}  # 当前文件的import行号
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    line = line.strip()
                    if line.startswith('import static '):
                        # 解析静态导入: import static com.xxx.ClassName.methodName;
                        static_import = line.replace('import static ', '').replace(';', '').strip()
                        # 分离类路径和方法名
                        last_dot = static_import.rfind('.')
                        if last_dot > 0:
                            class_path = static_import[:last_dot]
                            method_or_field = static_import[last_dot + 1:]
                            if method_or_field == '*':
                                # import static com.xxx.ClassName.* - 导入所有静态成员
                                static_imports[f"*:{class_path}"] = class_path
                            else:
                                static_imports[method_or_field] = class_path
                        # 保存静态导入的行号
                        import_lines[f"import static {static_import};"] = line_num
                    elif line.startswith('import ') and not line.startswith('import static'):
                        import_stmt = line.replace('import ', '').replace(';', '').strip()
                        imports.append(import_stmt)
                        # 保存import语句的行号
                        import_lines[f"import {import_stmt};"] = line_num
                
                self.package_imports[file_path] = imports
                self.static_imports[file_path] = static_imports
                self.import_line_numbers[file_path] = import_lines
                
            except Exception as e:
                logger.warning(f"读取文件导入失败 {file_path}: {e}")
                self.package_imports[file_path] = []
                self.static_imports[file_path] = {}
                self.import_line_numbers[file_path] = {}
        
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
        
        # 收集所有子节点和映射，稍后进行链式调用去重
        pending_children = []
        pending_mappings = []
        
        # 分析方法中的所有调用
        for call in method.method_calls:
            # 检查方法是否应该被忽略
            call_method_name = call.get("method", "")
            call_object_name = call.get("object", "")
            call_resolved_type = call.get("resolved_type", "")
            call_type = call.get("type", "")  # 获取调用类型
            
            # 确定调用的类名：优先使用resolved_type，其次解析变量类型
            call_class_name = ""
            if call_resolved_type:
                call_class_name = call_resolved_type
            elif call_object_name:
                # 尝试解析变量类型
                resolved_type = self._resolve_variable_type(call_object_name, method.file_path)
                if resolved_type:
                    call_class_name = resolved_type
                else:
                    # 如果是大写开头，可能是类名
                    if call_object_name and call_object_name[0].isupper():
                        call_class_name = call_object_name
            
            if self._should_ignore_method(call_method_name, call_class_name, method.file_path, call_type):
                logger.debug(f"{indent}  ⏭️ 跳过忽略的方法: {call_method_name}")
                continue
            
            child_nodes = self._resolve_method_call(call, method.file_path, parent_node.depth + 1)
            
            for child_node in child_nodes:
                # 再次检查解析后的节点是否应该被忽略（针对构造函数）
                if self._should_ignore_method(child_node.method_name, child_node.class_name, method.file_path, child_node.call_type):
                    continue
                    
                # 生成方法映射
                mapping = self._generate_method_mapping(call, child_node, method.file_path)
                pending_children.append((child_node, mapping))
        
        # 对链式调用进行去重，只保留最长的调用链
        filtered_children = self._filter_chain_calls(pending_children)
        
        # 添加过滤后的子节点
        for child_node, mapping in filtered_children:
            parent_node.children.append(child_node)
            
            if mapping:
                parent_node.method_mappings.append(mapping)
                self.method_mappings.append(mapping)
            
            # 递归分析子方法（使用父节点的文件路径来确定import上下文）
            child_method = self._find_method_by_signature(
                child_node.class_name, 
                child_node.method_name,
                method.file_path  # 传递当前文件路径以便正确解析import
            )
            if child_method:
                self._analyze_call_tree_recursive(child_node, child_method, max_depth)
    
    def _resolve_method_call(self, call: Dict, current_file: str, depth: int) -> List[CallTreeNode]:
        """解析方法调用，处理多态和继承"""
        method_name = call["method"]
        object_name = call.get("object", "")
        call_type = call.get("type", "instance")
        line_number = call.get("line", 0)
        arguments = call.get("arguments", 0)
        
        # 在创建节点之前进行忽略检查
        resolved_type = call.get("resolved_type", "")
        class_name = resolved_type or object_name
        
        if self._should_ignore_method(method_name, class_name, current_file, call_type):
            logger.debug(f"🚫 在节点创建阶段忽略方法: {class_name}.{method_name}")
            return []  # 返回空列表，不创建任何节点
        
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
            # 处理链式调用，如 StatusCode.CODE_1000.getKey()
            # 提取基础类名（第一个点之前的部分）
            base_class_name = object_name.split('.')[0] if '.' in object_name else object_name
            
            # 检查是否是已知的工具类静态方法
            if self._is_utility_class(object_name) or self._is_utility_class(base_class_name):
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
            
            # 检查是否是this.field的调用
            if object_name.startswith("this."):
                field_name = object_name[5:]  # 去掉"this."
                # 解析this.field的实际类型
                variable_type = self._resolve_variable_type(field_name, current_file)
                
                if variable_type:
                    # 查找所有可能的实现
                    implementations = self._find_all_implementations(variable_type, method_name, current_file)
                    
                    if implementations:
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
                        return nodes
                    else:
                        # 找到了变量类型但没有找到实现（外部类）
                        node = CallTreeNode(
                            method_name=method_name,
                            class_name=variable_type,
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
                        return nodes
                else:
                    # 无法解析this.field的类型，保留原始调用
                    node = CallTreeNode(
                        method_name=method_name,
                        class_name=object_name,
                        package_name="",
                        file_path="",
                        line_number=line_number,
                        call_type="chain_call",
                        parameters=[f"arg{i}" for i in range(arguments)],
                        return_type="",
                        children=[],
                        method_mappings=[],
                        depth=depth
                    )
                    nodes.append(node)
                    return nodes
            
            # 检查是否是枚举类或常量类的链式调用（如 StatusCode.CODE_1000.getKey()）
            elif '.' in object_name:
                # 这是链式调用，保留完整的调用链
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=object_name,  # 保留完整的链式调用对象
                    package_name="",
                    file_path="",
                    line_number=line_number,
                    call_type="chain_call",  # 新增链式调用类型
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
                # 查找所有可能的实现（传递current_file以便正确解析import）
                implementations = self._find_all_implementations(variable_type, method_name, current_file)
                
                if implementations:
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
                    # 找到了变量类型但没有找到实现（外部类），创建一个unresolved节点
                    node = CallTreeNode(
                        method_name=method_name,
                        class_name=variable_type,  # 使用解析出的类型名
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
            # 直接方法调用（可能是同类中的方法或静态导入的方法）
            
            # 1. 首先检查是否是静态导入的方法
            static_class = self._resolve_static_import(method_name, current_file)
            if static_class:
                node = CallTreeNode(
                    method_name=method_name,
                    class_name=static_class,
                    package_name="",
                    file_path="",
                    line_number=line_number,
                    call_type="static_import",
                    parameters=[f"arg{i}" for i in range(arguments)],
                    return_type="",
                    children=[],
                    method_mappings=[],
                    depth=depth
                )
                nodes.append(node)
            else:
                # 2. 同类中的方法
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
    
    def _resolve_static_import(self, method_name: str, current_file: str) -> Optional[str]:
        """解析静态导入的方法，返回完整的类路径"""
        static_imports = self.static_imports.get(current_file, {})
        
        # 直接匹配方法名
        if method_name in static_imports:
            return static_imports[method_name]
        
        # 检查通配符导入 (import static xxx.*)
        for key, class_path in static_imports.items():
            if key.startswith("*:"):
                # 这是通配符导入，需要检查类中是否有这个方法
                # 简化处理：返回类路径
                return class_path
        
        return None
    
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
        
        # 通用泛型字段推理 - 替代之前的baseService特殊处理
        generic_field_type = self._resolve_generic_field_type(variable_name, current_class, current_file)
        if generic_field_type:
            logger.debug(f"🎯 通过泛型推理得到字段类型: {variable_name} -> {generic_field_type}")
            return generic_field_type
        
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
    
    def _resolve_generic_field_type(self, field_name: str, current_class, current_file: str) -> Optional[str]:
        """
        通用的泛型字段类型推理
        支持所有泛型字段：baseService, baseMapper, 以及其他泛型字段
        """
        try:
            # 1. 获取字段的声明类型
            field_declared_type = self._get_field_declared_type(field_name, current_class)
            if not field_declared_type:
                return None
            
            logger.debug(f"🔍 字段 {field_name} 的声明类型: {field_declared_type}")
            
            # 2. 检查是否是泛型参数（如 M, W, T, E 等单字母泛型参数）
            if self._is_generic_parameter(field_declared_type):
                logger.debug(f"🧬 识别为泛型参数: {field_declared_type}")
                # 3. 从继承关系中推理具体类型
                concrete_type = self._resolve_generic_parameter_type(field_declared_type, current_class, current_file)
                if concrete_type:
                    logger.debug(f"✅ 泛型推理成功: {field_declared_type} -> {concrete_type}")
                    return concrete_type
            
            # 4. 如果不是泛型参数，但可能是泛型基类，尝试推理
            elif self._is_generic_base_type(field_declared_type):
                logger.debug(f"🏗️ 识别为泛型基类: {field_declared_type}")
                # 例如：BaseMapper<T> -> MaterialConfigMapper
                concrete_type = self._resolve_generic_base_type(field_declared_type, current_class, current_file)
                if concrete_type:
                    logger.debug(f"✅ 泛型基类推理成功: {field_declared_type} -> {concrete_type}")
                    return concrete_type
            
            return None
            
        except Exception as e:
            logger.debug(f"泛型字段推理失败 {field_name}: {e}")
            return None
    
    def _get_field_declared_type(self, field_name: str, current_class) -> Optional[str]:
        """获取字段的声明类型，包括从继承链中查找"""
        try:
            # 在当前类中查找字段
            for field in current_class.fields:
                if field.get("name") == field_name:
                    return field.get("type")
            
            # 特殊处理已知的框架字段
            framework_fields = self._get_framework_field_type(field_name, current_class)
            if framework_fields:
                return framework_fields
            
            # 在父类中查找字段（处理继承的字段）
            parent_classes = self._get_parent_classes_info(current_class)
            for parent_class in parent_classes:
                for field in parent_class.get('fields', []):
                    if field.get("name") == field_name:
                        return field.get("type")
            
            return None
            
        except Exception as e:
            logger.debug(f"获取字段声明类型失败 {field_name}: {e}")
            return None
    
    def _get_framework_field_type(self, field_name: str, current_class) -> Optional[str]:
        """获取框架字段的类型（如MyBatis Plus、Spring等框架的字段）"""
        try:
            extends_info = getattr(current_class, 'extends', '') or ''
            
            # MyBatis Plus ServiceImpl的baseMapper字段
            if field_name == "baseMapper" and "ServiceImpl" in extends_info:
                logger.debug(f"🔍 识别为MyBatis Plus的baseMapper字段")
                return "M"  # MyBatis Plus ServiceImpl<M, T>中的M
            
            # Spring框架的baseService字段
            if field_name == "baseService" and "BaseDatagridController" in extends_info:
                logger.debug(f"🔍 识别为Spring框架的baseService字段")
                return "W"  # BaseDatagridController<W, T>中的W
            
            # 其他框架字段可以在这里扩展
            
            return None
            
        except Exception as e:
            logger.debug(f"获取框架字段类型失败 {field_name}: {e}")
            return None
    
    def _is_generic_parameter(self, type_name: str) -> bool:
        """检查是否是泛型参数（如 M, W, T, E 等）"""
        if not type_name:
            return False
        
        # 泛型参数通常是单个大写字母，或者是简短的大写字母组合
        return (
            len(type_name) == 1 and type_name.isupper() or  # M, W, T
            len(type_name) <= 3 and type_name.isupper() and type_name.isalpha()  # DTO, VO等
        )
    
    def _is_generic_base_type(self, type_name: str) -> bool:
        """检查是否是泛型基类（如 BaseMapper, BaseService 等）"""
        if not type_name:
            return False
        
        # 常见的泛型基类模式
        generic_base_patterns = [
            'BaseMapper', 'BaseService', 'BaseDao', 'BaseRepository',
            'BaseController', 'BaseEntity', 'BaseModel'
        ]
        
        return any(pattern in type_name for pattern in generic_base_patterns)
    
    def _resolve_generic_parameter_type(self, generic_param: str, current_class, current_file: str) -> Optional[str]:
        """
        从继承关系中推理泛型参数的具体类型
        例如：M -> MaterialConfigMapper, W -> MaterialConfigServiceImpl
        """
        try:
            # 获取类的继承信息
            extends_info = getattr(current_class, 'extends', '') or ''
            
            if not extends_info:
                return None
            
            logger.debug(f"🔍 分析泛型参数 {generic_param}，继承信息: {extends_info}")
            
            # 解析泛型继承，如 BaseServiceImpl<MaterialConfigMapper, MaterialConfig>
            if '<' in extends_info and '>' in extends_info:
                # 提取泛型参数
                start = extends_info.find('<')
                end = extends_info.rfind('>')
                generic_params = extends_info[start+1:end]
                
                # 分割泛型参数
                params = self._parse_generic_parameters(generic_params)
                
                if params:
                    # 获取父类的泛型参数定义
                    parent_generic_params = self._get_parent_generic_parameters(extends_info)
                    
                    # 建立泛型参数映射
                    generic_mapping = {}
                    for i, parent_param in enumerate(parent_generic_params):
                        if i < len(params):
                            generic_mapping[parent_param] = params[i].strip()
                    
                    logger.debug(f"🗺️ 泛型参数映射: {generic_mapping}")
                    
                    # 查找目标泛型参数的具体类型
                    if generic_param in generic_mapping:
                        concrete_type = generic_mapping[generic_param]
                        # 解析完整类名
                        full_type = self._resolve_class_name_from_imports(concrete_type, current_file)
                        return full_type or concrete_type
            
            return None
            
        except Exception as e:
            logger.debug(f"解析泛型参数类型失败 {generic_param}: {e}")
            return None
    
    def _get_parent_generic_parameters(self, extends_info: str) -> List[str]:
        """
        获取父类的泛型参数定义
        例如：BaseServiceImpl<M extends BaseMapper<T>, T> -> ['M', 'T']
        """
        try:
            # 提取基类名
            base_class_name = extends_info.split('<')[0].strip()
            
            logger.debug(f"🔍 分析基类的泛型参数: {base_class_name}")
            
            # 常见的泛型参数模式
            generic_patterns = {
                'BaseDatagridController': ['W', 'T'],  # <W extends BaseServiceImpl, T>
                'BaseServiceImpl': ['M', 'T'],         # <M extends BaseMapper<T>, T>
                'ServiceImpl': ['M', 'T'],             # MyBatis Plus的ServiceImpl<M, T>
                'BaseController': ['S', 'T'],          # <S extends BaseService, T>
                'BaseMapper': ['T'],                   # <T>
                'BaseService': ['T'],                  # <T>
            }
            
            # 查找匹配的模式
            for pattern, params in generic_patterns.items():
                if pattern in base_class_name:
                    logger.debug(f"🎯 匹配到泛型模式: {pattern} -> {params}")
                    return params
            
            # 如果没有匹配的模式，尝试从继承信息中解析
            if '<' in extends_info and '>' in extends_info:
                # 尝试从实际的泛型声明中推断参数名
                # 例如：BaseServiceImpl<MaterialConfigMapper, MaterialConfig>
                # 推断父类应该有两个泛型参数
                start = extends_info.find('<')
                end = extends_info.rfind('>')
                generic_params = extends_info[start+1:end]
                param_count = len([p.strip() for p in generic_params.split(',') if p.strip()])
                
                if param_count == 1:
                    return ['T']
                elif param_count == 2:
                    return ['M', 'T']  # 最常见的模式
                elif param_count == 3:
                    return ['M', 'T', 'E']
                else:
                    return ['M', 'T']  # 默认
            
            # 最后的默认值
            return ['M', 'T']
            
        except Exception as e:
            logger.debug(f"获取父类泛型参数失败: {e}")
            return ['M', 'T']  # 返回默认值
    
    def _resolve_generic_base_type(self, base_type: str, current_class, current_file: str) -> Optional[str]:
        """
        解析泛型基类的具体实现
        例如：BaseMapper -> MaterialConfigMapper
        """
        try:
            # 这种情况较少见，通常字段类型会是泛型参数而不是泛型基类
            # 但为了完整性，提供基本实现
            
            if 'BaseMapper' in base_type:
                # 尝试根据当前类名推断Mapper名
                class_name = current_class.name
                if class_name.endswith('ServiceImpl'):
                    mapper_name = class_name.replace('ServiceImpl', 'Mapper')
                    return mapper_name
            
            return None
            
        except Exception as e:
            logger.debug(f"解析泛型基类失败 {base_type}: {e}")
            return None
    
    def _get_parent_classes_info(self, current_class) -> List[Dict]:
        """获取父类信息，用于查找继承的字段"""
        try:
            parent_classes = []
            extends_info = getattr(current_class, 'extends', '') or ''
            
            if extends_info:
                # 提取父类名（去掉泛型参数）
                parent_class_name = extends_info.split('<')[0].strip()
                
                # 在项目中查找父类
                for java_class in self.java_classes.values():
                    if java_class.name == parent_class_name:
                        parent_classes.append({
                            'name': java_class.name,
                            'fields': [{'name': f.get('name'), 'type': f.get('type')} 
                                     for f in java_class.fields]
                        })
                        break
            
            return parent_classes
            
        except Exception as e:
            logger.debug(f"获取父类信息失败: {e}")
            return []
    
    def _resolve_base_service_type_legacy(self, current_class, current_file: str) -> Optional[str]:
        """
        解析baseService的实际类型（遗留方法，保留作为参考）
        现在使用通用的_resolve_generic_field_type方法
        """
        try:
            # 获取类的继承信息
            extends_info = getattr(current_class, 'extends', '') or ''
            
            logger.debug(f"🔍 分析baseService类型，当前类: {current_class.name}")
            logger.debug(f"🔍 继承信息: {extends_info}")
            
            if not extends_info:
                return None
            
            # 解析泛型继承，如 BaseDatagridController<MaterialConfigServiceImpl, MaterialConfig>
            if '<' in extends_info and '>' in extends_info:
                # 提取泛型参数
                start = extends_info.find('<')
                end = extends_info.rfind('>')
                generic_params = extends_info[start+1:end]
                
                # 分割泛型参数，处理嵌套泛型
                params = self._parse_generic_parameters(generic_params)
                
                if params:
                    # 第一个泛型参数就是baseService的类型（根据BaseDatagridController<W extends BaseServiceImpl, T>）
                    service_type = params[0].strip()
                    
                    # 解析完整类名（处理import）
                    full_service_type = self._resolve_class_name_from_imports(service_type, current_file)
                    
                    logger.debug(f"✅ 推理出baseService类型: {service_type} -> {full_service_type}")
                    return full_service_type or service_type
            
            # 如果没有泛型参数，检查是否是BaseDatagridController的直接继承
            if 'BaseDatagridController' in extends_info:
                logger.debug(f"⚠️ 继承BaseDatagridController但没有泛型参数: {extends_info}")
                # 尝试从字段注解推断
                return self._resolve_base_service_from_field(current_class)
            
            return None
            
        except Exception as e:
            logger.debug(f"解析baseService类型失败: {e}")
            return None
    
    def _parse_generic_parameters(self, generic_params: str) -> List[str]:
        """解析泛型参数，处理嵌套泛型"""
        params = []
        current_param = ""
        bracket_count = 0
        
        for char in generic_params:
            if char == '<':
                bracket_count += 1
                current_param += char
            elif char == '>':
                bracket_count -= 1
                current_param += char
            elif char == ',' and bracket_count == 0:
                params.append(current_param.strip())
                current_param = ""
            else:
                current_param += char
        
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _resolve_class_name_from_imports(self, class_name: str, current_file: str) -> Optional[str]:
        """从import语句解析类名为完整类名"""
        if not class_name or not current_file:
            return class_name
        
        # 如果已经是完整类名，直接返回
        if '.' in class_name:
            return class_name
        
        # 从import语句中查找
        imports = self.package_imports.get(current_file, [])
        for import_stmt in imports:
            if import_stmt.endswith(f".{class_name}"):
                return class_name  # 返回简单类名，因为已经通过import确认了
        
        # 查找同包下的类
        current_class = self._find_class_by_file(current_file)
        if current_class and hasattr(current_class, 'package'):
            current_package = current_class.package
            if current_package:
                # 检查同包下是否有这个类
                full_class_name = f"{current_package}.{class_name}"
                if self._class_exists_in_project(full_class_name):
                    return class_name  # 返回简单类名
        
        return class_name
    
    def _resolve_base_service_from_field(self, current_class) -> Optional[str]:
        """从baseService字段的注解或类型信息推断类型"""
        try:
            # 查找baseService字段
            for field in current_class.fields:
                if field.get('name') == 'baseService':
                    field_type = field.get('type', '')
                    if field_type and field_type != 'W':  # W是泛型参数
                        return field_type
            
            return None
            
        except Exception as e:
            logger.debug(f"从字段推断baseService类型失败: {e}")
            return None
    
    def _class_exists_in_project(self, full_class_name: str) -> bool:
        """检查类是否存在于项目中"""
        for java_class in self.java_classes.values():
            if hasattr(java_class, 'full_name') and java_class.full_name == full_class_name:
                return True
            # 也检查package.name格式
            if hasattr(java_class, 'package') and hasattr(java_class, 'name'):
                if f"{java_class.package}.{java_class.name}" == full_class_name:
                    return True
        return False
    
    def _find_all_implementations(self, type_name: str, method_name: str, current_file: str = None) -> List[Dict]:
        """查找类型的所有实现，处理接口、继承和多态"""
        implementations = []
        
        # 1. 直接类实现（使用import语句确定正确的类）
        java_class = self._find_class_by_name(type_name, current_file)
        if java_class and self._class_has_method(java_class, method_name):
            implementations.append({
                "class": java_class.name,
                "package": java_class.package,
                "file": java_class.file_path,
                "call_type": "concrete"
            })
        
        # 如果找到了明确的import但类不在项目中，不应该继续查找
        if current_file and current_file in self.package_imports:
            imports = self.package_imports[current_file]
            for import_stmt in imports:
                if import_stmt.endswith(f".{type_name}"):
                    # 找到了明确的import语句
                    if not java_class:
                        # 类不在项目中（外部类），返回空列表
                        return implementations
                    break
        
        # 2. 接口实现
        if type_name in self.interface_implementations:
            for impl in self.interface_implementations[type_name]:
                impl_class = self._find_class_by_name(impl["class"], current_file)
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
            impl_class = self._find_class_by_name(impl_name, current_file)
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
    
    def _find_class_by_name(self, class_name: str, current_file: str = None) -> Optional[JavaClass]:
        """根据类名查找Java类，优先使用import语句确定正确的类"""
        # 如果提供了当前文件，先根据import语句查找
        found_import = False  # 标记是否找到了import语句
        if current_file and current_file in self.package_imports:
            imports = self.package_imports[current_file]
            for import_stmt in imports:
                # 检查import语句是否以类名结尾
                if import_stmt.endswith(f".{class_name}"):
                    found_import = True
                    # 找到了完整的包路径，查找对应的类
                    full_class_name = import_stmt
                    for java_class in self.java_classes.values():
                        full_name = f"{java_class.package}.{java_class.name}" if java_class.package else java_class.name
                        if full_name == full_class_name:
                            return java_class
                    # 如果找到了import但类不在项目中，说明是外部类，返回None
                    return None
                # 检查通配符导入
                elif import_stmt.endswith(".*"):
                    package_prefix = import_stmt[:-2]  # 去掉 .*
                    for java_class in self.java_classes.values():
                        if java_class.name == class_name and java_class.package == package_prefix:
                            return java_class
        
        # 如果没有找到明确的import语句，回退到简单的类名匹配
        # 但如果找到了import语句但类不在项目中，不应该回退
        if not found_import:
            for java_class in self.java_classes.values():
                if java_class.name == class_name:
                    return java_class
        return None
    
    def _find_method_by_signature(self, class_name: str, method_name: str, current_file: str = None) -> Optional[JavaMethod]:
        """根据类名和方法名查找方法"""
        # 1. 直接查找类名（使用import语句确定正确的类）
        java_class = self._find_class_by_name(class_name, current_file)
        if java_class:
            for method in java_class.methods:
                if method.name == method_name:
                    return method
        
        # 如果提供了current_file，检查是否有明确的import语句
        # 如果有明确的import但类不在项目中，不应该继续查找
        if current_file and current_file in self.package_imports:
            imports = self.package_imports[current_file]
            for import_stmt in imports:
                if import_stmt.endswith(f".{class_name}"):
                    # 找到了明确的import语句，但类不在项目中（外部类）
                    # 不应该继续查找
                    return None
        
        # 2. 尝试将变量名转换为类名（首字母大写）
        if class_name and class_name[0].islower():
            capitalized_name = class_name[0].upper() + class_name[1:]
            java_class = self._find_class_by_name(capitalized_name, current_file)
            if java_class:
                for method in java_class.methods:
                    if method.name == method_name:
                        return method
        
        # 3. 尝试查找 ServiceImpl 类
        if class_name.endswith("Service") or class_name.endswith("ServiceImpl"):
            impl_name = class_name.replace("Service", "ServiceImpl") if not class_name.endswith("Impl") else class_name
            # 首字母大写
            if impl_name[0].islower():
                impl_name = impl_name[0].upper() + impl_name[1:]
            java_class = self._find_class_by_name(impl_name, current_file)
            if java_class:
                for method in java_class.methods:
                    if method.name == method_name:
                        return method
        
        # 4. 模糊匹配：只在没有提供current_file时进行
        # 如果提供了current_file，说明我们已经检查过import语句了
        if not current_file:
            search_name = class_name[0].upper() + class_name[1:] if class_name and class_name[0].islower() else class_name
            for java_class in self.java_classes.values():
                # 匹配类名（忽略大小写）
                if java_class.name.lower() == search_name.lower():
                    for method in java_class.methods:
                        if method.name == method_name:
                            return method
                # 匹配 xxxImpl 模式
                if java_class.name.lower() == (search_name + "impl").lower():
                    for method in java_class.methods:
                        if method.name == method_name:
                            return method
        
        return None
    
    def _generate_method_mapping(self, call: Dict, node: CallTreeNode, current_file: str) -> Optional[MethodMapping]:
        """生成方法映射信息"""
        object_name = call.get("object", "")
        method_name = call["method"]
        resolved_type = call.get("resolved_type", "")  # 获取JDT解析出的实际类型
        
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
            file_path=current_file,
            resolved_type=resolved_type  # 保存JDT解析出的实际类型
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
        # 类.方法()映射（解析变量的实际类型）
        lines.append("## 类.方法()映射")
        lines.append("")
        lines.append("以下是调用链中变量对应的实际类型映射（去重）：")
        lines.append("")
        
        class_method_mappings = self._collect_class_method_mappings(call_tree)
        
        if class_method_mappings:
            lines.append("| 变量.方法() | 实际类型.方法() | 来源文件 | 行号 |")
            lines.append("|-------------|-----------------|----------|------|")
            for mapping in class_method_mappings:
                lines.append(f"| `{mapping['original']}` | `{mapping['resolved']}` | {mapping['file']} | {mapping['line']} |")
        else:
            lines.append("无需要映射的方法调用")
        
        lines.append("")
        
        lines.append("## Import语句汇总")
        lines.append("")
        
        # 收集有效的import语句（只包含实际解析到的类）
        import_info = {}  # {import_statement: {"file": file_path, "line": line_number}}
        
        for mapping in self.method_mappings:
            # 跳过无效的import
            if not mapping.import_statement:
                continue
            
            # 提取类名
            import_stmt = mapping.import_statement
            
            # 跳过明显无效的import（变量名、链式调用等）
            # 有效的import应该是: import xxx.xxx.ClassName; 或 import static xxx.xxx.ClassName.method;
            if any(invalid in import_stmt for invalid in ['()', '.trim', '.map', '.orElse', 'this.', '<>']):
                continue
            
            # 跳过小写开头的（变量名）
            class_part = import_stmt.replace('import ', '').replace(';', '').strip()
            if '.' in class_part:
                last_part = class_part.split('.')[-1]
            else:
                last_part = class_part
            
            # 类名应该大写开头，或者是完整包路径
            if last_part and last_part[0].islower() and '.' not in class_part:
                continue
            
            # 记录import来源（只保留第一次出现的）
            if import_stmt not in import_info:
                file_path = mapping.file_path
                file_name = Path(file_path).name if file_path else "unknown"
                
                # 尝试从import_line_numbers获取实际的import行号
                actual_line = 0
                actual_import_stmt = import_stmt  # 实际的import语句
                
                if file_path and file_path in self.import_line_numbers:
                    import_lines = self.import_line_numbers[file_path]
                    # 尝试匹配import语句
                    if import_stmt in import_lines:
                        actual_line = import_lines[import_stmt]
                    else:
                        # 尝试模糊匹配（去掉import前缀后匹配类名）
                        class_name = class_part.split('.')[-1] if '.' in class_part else class_part
                        for stmt, line_num in import_lines.items():
                            # 检查import语句是否以类名结尾
                            stmt_class = stmt.replace('import ', '').replace(';', '').strip()
                            stmt_class_name = stmt_class.split('.')[-1] if '.' in stmt_class else stmt_class
                            if stmt_class_name == class_name:
                                actual_line = line_num
                                actual_import_stmt = stmt  # 使用完整的import语句
                                break
                        
                        # 如果还是找不到，尝试查找通配符导入
                        if actual_line == 0:
                            for stmt, line_num in import_lines.items():
                                if stmt.endswith('.*;'):
                                    # 这是通配符导入，检查包名是否匹配
                                    package_prefix = stmt.replace('import ', '').replace('.*;', '')
                                    # 如果原始import语句包含这个包前缀，使用通配符导入
                                    if '.' in class_part and class_part.startswith(package_prefix):
                                        actual_line = line_num
                                        actual_import_stmt = stmt
                                        break
                
                # 如果找不到import行号，跳过这个import（可能是Java标准库的类）
                if actual_line == 0:
                    # 对于Java标准库的类（如Arrays, Optional），跳过
                    if class_part in ['Arrays', 'Optional', 'Collections', 'Objects', 'List', 'Map', 'Set']:
                        continue
                    # 对于没有包名的简单类名，也跳过
                    if '.' not in class_part:
                        continue
                
                import_info[actual_import_stmt] = {
                    "file": file_name,
                    "line": actual_line if actual_line > 0 else mapping.line_number
                }
        
        if import_info:
            lines.append("| Import语句 | 来源文件 | 行号 |")
            lines.append("|------------|----------|------|")
            for import_stmt, info in sorted(import_info.items()):
                lines.append(f"| `{import_stmt}` | {info['file']} | {info['line']} |")
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
        elif node.call_type == "chain_call":
            type_marker = " [链式调用]"
        elif node.call_type == "static":
            type_marker = " [静态方法]"
        elif node.call_type == "constructor":
            type_marker = " [构造函数]"
        elif node.call_type == "static_import":
            type_marker = " [静态导入]"
        
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
    
    def _collect_class_method_mappings(self, call_tree: CallTreeNode) -> List[Dict]:
        """
        收集类.方法()映射信息 - 直接从调用树节点收集，保证与调用树一致
        
        映射规则：
        1. 变量调用（小写开头）：显示变量名 -> 实际类型
        2. 类名调用（大写开头）：显示类名 -> 类名（保持一致性）
        3. 链式调用：不需要映射
        4. this调用：不需要映射
        5. 相同的映射只保留一个（按 原始调用 -> 解析调用 去重）
        """
        mappings = []
        seen = set()  # 用于去重：只按 original|resolved 去重，不包含行号
        
        def collect_from_tree(node: CallTreeNode, parent_file: str = ""):
            # 获取当前节点的文件路径
            current_file = node.file_path if node.file_path else parent_file
            
            # 处理当前节点的method_mappings（这些是从原始call数据生成的）
            for mapping in node.method_mappings:
                interface_call = mapping.interface_call  # 如 "sheetMergeService.merge()"
                implementation_call = mapping.implementation_call  # 如 "SheetMergeServiceImpl.merge()"
                resolved_type = mapping.resolved_type  # JDT解析出的实际类型
                
                if '.' in interface_call and '(' in interface_call:
                    parts = interface_call.replace('()', '').split('.')
                    if len(parts) >= 2:
                        object_name = parts[0]
                        method_name = parts[-1]
                        
                        # 跳过链式调用（包含多个点或括号）
                        if '(' in object_name or len(parts) > 2:
                            continue
                        
                        # 跳过this调用
                        if object_name == "this":
                            continue
                        
                        # 确定实际类型
                        actual_type = ""
                        
                        # 1. 优先使用JDT解析出的resolved_type
                        if resolved_type:
                            actual_type = resolved_type
                        else:
                            # 2. 从implementation_call中提取实际类型
                            impl_parts = implementation_call.replace('()', '').split('.')
                            impl_class_name = impl_parts[0] if impl_parts else ""
                            
                            if impl_class_name and impl_class_name[0].isupper():
                                actual_type = impl_class_name
                            elif object_name and object_name[0].isupper():
                                # 3. 如果object_name本身是大写开头（静态调用），使用它作为类型
                                actual_type = object_name
                        
                        if not actual_type:
                            continue
                        
                        # 构建映射
                        original = f"{object_name}.{method_name}()"
                        resolved = f"{actual_type}.{method_name}()"
                        
                        # 去重：只按 original|resolved 去重，相同映射只保留第一个
                        key = f"{original}|{resolved}"
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        mappings.append({
                            "original": original,
                            "resolved": resolved,
                            "file": Path(mapping.file_path).name if mapping.file_path else "unknown",
                            "line": mapping.line_number
                        })
            
            # 递归处理子节点
            for child in node.children:
                collect_from_tree(child, current_file)
        
        collect_from_tree(call_tree)
        
        logger.info(f"📊 收集到的类.方法()映射数: {len(mappings)}")
        return mappings
    
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
        import_info = {}  # {import_statement: {"file": file_path, "line": line_number}}
        
        for mapping in self.method_mappings:
            import_stmt = mapping.import_statement
            if not import_stmt:
                continue
            
            # 跳过无效的import
            if any(invalid in import_stmt for invalid in ['()', '.trim', '.map', '.orElse', 'this.', '<>']):
                continue
            
            class_part = import_stmt.replace('import ', '').replace(';', '').strip()
            if '.' in class_part:
                last_part = class_part.split('.')[-1]
            else:
                last_part = class_part
            
            if last_part and last_part[0].islower() and '.' not in class_part:
                continue
            
            if import_stmt not in import_info:
                import_info[import_stmt] = {
                    "file": Path(mapping.file_path).name if mapping.file_path else "unknown",
                    "line": mapping.line_number
                }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("// 深度调用树分析生成的Import语句\n")
            f.write("// 根据实际需要添加到对应的Java文件中\n")
            f.write("// 格式: import语句 // 来源文件:行号\n\n")
            
            for import_stmt, info in sorted(import_info.items()):
                f.write(f"{import_stmt} // {info['file']}:{info['line']}\n")
    
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