#!/usr/bin/env python3
"""
调用链分析器 - 分析接口内部的方法调用链
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional
import javalang  # 需要安装: pip install javalang

class CallChainAnalyzer:
    """调用链分析器"""
    
    def __init__(self):
        self.method_cache = {}
    
    def analyze_call_chain(self, endpoint, project_path: str) -> Dict:
        """分析接口的调用链"""
        file_path = Path(endpoint.file_path)
        
        if not file_path.exists():
            return {"error": "File not found"}
        
        # 根据文件类型选择分析器
        if file_path.suffix == '.java':
            return self._analyze_java_call_chain(endpoint, project_path)
        elif file_path.suffix == '.py':
            return self._analyze_python_call_chain(endpoint, project_path)
        else:
            return self._generic_call_chain_analysis(endpoint, project_path)
    
    def _analyze_java_call_chain(self, endpoint, project_path: str) -> Dict:
        """分析Java调用链"""
        result = {
            "endpoint": endpoint.name,
            "method_calls": [],
            "service_calls": [],
            "dao_calls": [],
            "sql_statements": [],
            "files": [],
            "dependencies": []
        }
        
        try:
            content = Path(endpoint.file_path).read_text(encoding='utf-8')
            
            # 使用javalang解析Java代码
            tree = javalang.parse.parse(content)
            
            # 查找目标方法
            target_method = None
            for path, node in tree.filter(javalang.tree.MethodDeclaration):
                if node.name == endpoint.handler:
                    target_method = node
                    break
            
            if not target_method:
                return result
            
            # 收集方法内的调用
            method_calls = self._extract_java_method_calls(target_method)
            result["method_calls"] = method_calls
            
            # 查找相关文件（Service, DAO等）
            related_files = self._find_related_java_files(
                method_calls, project_path, endpoint.file_path
            )
            result["files"] = related_files
            
            # 提取SQL语句
            sql_statements = self._extract_sql_from_java(content)
            result["sql_statements"] = sql_statements
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _analyze_python_call_chain(self, endpoint, project_path: str) -> Dict:
        """分析Python调用链"""
        result = {
            "endpoint": endpoint.name,
            "method_calls": [],
            "function_calls": [],
            "imports": [],
            "files": [],
            "dependencies": []
        }
        
        try:
            content = Path(endpoint.file_path).read_text(encoding='utf-8')
            
            # 使用ast解析Python代码
            tree = ast.parse(content)
            
            # 查找目标函数
            target_func = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == endpoint.handler:
                    target_func = node
                    break
            
            if not target_func:
                return result
            
            # 收集函数内的调用
            calls = self._extract_python_calls(target_func)
            result["function_calls"] = calls
            
            # 收集导入
            imports = self._extract_python_imports(tree)
            result["imports"] = imports
            
            # 查找相关文件
            related_files = self._find_related_python_files(
                calls, imports, project_path, endpoint.file_path
            )
            result["files"] = related_files
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _extract_java_method_calls(self, method_node) -> List[Dict]:
        """提取Java方法调用"""
        calls = []
        
        for path, node in method_node.filter(javalang.tree.MethodInvocation):
            call_info = {
                "method": node.member,
                "arguments": len(node.arguments) if node.arguments else 0,
                "position": node.position.line if node.position else 0
            }
            
            # 如果是链式调用，尝试获取对象
            if hasattr(node, 'qualifier') and node.qualifier:
                if isinstance(node.qualifier, str):
                    call_info["object"] = node.qualifier
                elif hasattr(node.qualifier, 'member'):
                    call_info["object"] = node.qualifier.member
            
            calls.append(call_info)
        
        return calls
    
    def _extract_python_calls(self, func_node) -> List[Dict]:
        """提取Python函数调用"""
        calls = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_info = {
                        "function": node.func.id,
                        "arguments": len(node.args) if node.args else 0,
                        "keywords": [kw.arg for kw in node.keywords] if node.keywords else []
                    }
                    calls.append(call_info)
                elif isinstance(node.func, ast.Attribute):
                    call_info = {
                        "function": node.func.attr,
                        "object": self._get_ast_name(node.func.value),
                        "arguments": len(node.args) if node.args else 0
                    }
                    calls.append(call_info)
        
        return calls
    
    def _get_ast_name(self, node):
        """从AST节点获取名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_ast_name(node.value)}.{node.attr}"
        return "unknown"
    
    def _extract_python_imports(self, tree) -> List[str]:
        """提取Python导入语句"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
        
        return imports
    
    def _find_related_java_files(self, method_calls, project_path, source_file):
        """查找Java相关文件"""
        related_files = []
        project_root = Path(project_path)
        
        # 常见的Java文件后缀和目录
        java_patterns = [
            "*Service.java",
            "*ServiceImpl.java",
            "*DAO.java",
            "*Mapper.java",
            "*Repository.java"
        ]
        
        # 从方法调用推断相关文件
        for call in method_calls:
            method_name = call.get("method", "")
            object_name = call.get("object", "")
            
            # 如果调用的是Service方法
            if method_name and ('Service' in object_name or method_name.endswith('Service')):
                # 查找对应的Service文件
                service_files = list(project_root.rglob(f"*{object_name}*.java"))
                service_files.extend(list(project_root.rglob(f"*{method_name}*.java")))
                
                for file in service_files:
                    if file != Path(source_file):
                        related_files.append({
                            "path": str(file.relative_to(project_root)),
                            "type": "service",
                            "reason": f"Called from {method_name}"
                        })
        
        return related_files
    
    def _find_related_python_files(self, calls, imports, project_path, source_file):
        """查找Python相关文件"""
        related_files = []
        project_root = Path(project_path)
        
        # 从导入语句推断相关文件
        for imp in imports:
            # 将导入转换为可能的文件路径
            module_parts = imp.split('.')
            
            # 尝试找到对应的.py文件
            possible_paths = [
                project_root / f"{'/'.join(module_parts)}.py",
                project_root / f"{'/'.join(module_parts)}/__init__.py"
            ]
            
            for path in possible_paths:
                if path.exists() and path != Path(source_file):
                    related_files.append({
                        "path": str(path.relative_to(project_root)),
                        "type": "module",
                        "reason": f"Imported as {imp}"
                    })
        
        return related_files
    
    def _extract_sql_from_java(self, content: str) -> List[str]:
        """从Java代码中提取SQL语句"""
        sql_patterns = [
            r'"(SELECT|INSERT|UPDATE|DELETE)[^";]*"',  # 双引号内的SQL
            r"'(SELECT|INSERT|UPDATE|DELETE)[^';]*'",  # 单引号内的SQL
            r'@Select\(["\']([^"\']+)["\']\)',         # MyBatis注解
            r'@Update\(["\']([^"\']+)["\']\)',
            r'@Insert\(["\']([^"\']+)["\']\)',
            r'@Delete\(["\']([^"\']+)["\']\)',
        ]
        
        sql_statements = []
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    sql = match[0]
                else:
                    sql = match
                
                # 清理SQL
                sql = sql.strip('"\'')
                sql = re.sub(r'\s+', ' ', sql)  # 标准化空格
                
                if sql not in sql_statements and len(sql) > 10:
                    sql_statements.append(sql)
        
        return sql_statements
    
    def _generic_call_chain_analysis(self, endpoint, project_path: str) -> Dict:
        """通用调用链分析"""
        # 读取文件内容
        content = Path(endpoint.file_path).read_text(encoding='utf-8', errors='ignore')
        
        # 简单的正则匹配方法调用
        method_patterns = {
            'java': r'(\w+)\.(\w+)\([^)]*\)',
            'python': r'(\w+)\.(\w+)\([^)]*\)',
            'javascript': r'(\w+)\.(\w+)\([^)]*\)',
        }
        
        result = {
            "endpoint": endpoint.name,
            "method_calls": [],
            "files": [],
            "note": "Generic analysis - may be incomplete"
        }
        
        # 根据文件扩展名选择模式
        file_ext = Path(endpoint.file_path).suffix[1:]  # 移除点
        pattern = method_patterns.get(file_ext, r'(\w+)\.(\w+)\([^)]*\)')
        
        matches = re.findall(pattern, content)
        for obj, method in matches:
            result["method_calls"].append({
                "object": obj,
                "method": method
            })
        
        return result