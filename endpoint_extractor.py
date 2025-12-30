#!/usr/bin/env python3
"""
HTTP接口提取器 - 支持多种框架
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json

@dataclass
class ApiEndpoint:
    """API端点定义"""
    name: str
    path: str                    # 请求路径，如 /api/user/list
    method: str                  # HTTP方法，如 GET, POST
    controller: str              # 控制器/类名
    handler: str                 # 处理方法名
    file_path: str               # 源文件路径
    line_number: int             # 代码行号
    parameters: List[str] = field(default_factory=list)  # 参数列表
    return_type: Optional[str] = None
    annotations: List[str] = field(default_factory=list)  # 注解
    framework: str = "unknown"   # 框架类型: spring, flask, django, gin等
    
    def __hash__(self):
        return hash(f"{self.path}:{self.method}:{self.file_path}")

class EndpointExtractor:
    """HTTP接口提取器"""
    
    def __init__(self):
        # 定义各种框架的识别模式
        self.patterns = {
            "spring": {
                "controller": r'@(RestController|Controller)\s*.*?class\s+(\w+)',
                "mapping": r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping|PatchMapping)\s*\(\s*["\']([^"\']+)["\']',
                "method": r'(public|private|protected)\s+[^{]*?\s+(\w+)\s*\([^)]*\)'
            },
            "flask": {
                "route": r'@app\.route\(["\']([^"\']+)["\'][^)]*\)\s*\n\s*def\s+(\w+)',
                "method": r'methods=\[["\']([^"\']+)["\'\]\]'
            },
            "django": {
                "url": r'path\(["\']([^"\']+)["\'][^)]*,\s*([^)]+)\)',
                "view": r'def\s+(\w+)\s*\([^)]*\)'
            },
            "gin": {
                "route": r'\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\'][^)]*,\s*(\w+)'
            }
        }
        
    def extract_from_project(self, project_path: str) -> Dict[str, ApiEndpoint]:
        """从项目中提取所有HTTP接口"""
        endpoints = {}
        
        project_path = Path(project_path)
        
        # 支持的文件扩展名
        extensions = {'.java', '.py', '.go', '.js', '.ts', '.php'}
        
        # 遍历项目文件
        for root, dirs, files in os.walk(project_path):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', 'venv', '__pycache__'}]
            
            for file in files:
                file_path = Path(root) / file
                
                if file_path.suffix.lower() not in extensions:
                    continue
                    
                # 根据文件类型选择合适的提取器
                file_endpoints = self.extract_endpoints_from_file(file_path)
                
                for endpoint in file_endpoints:
                    # 使用 path:method 作为唯一键
                    key = f"{endpoint.path}:{endpoint.method}"
                    endpoints[key] = endpoint
                    
        return endpoints
    
    def extract_endpoints_from_file(self, file_path: Path) -> List[ApiEndpoint]:
        """从单个文件提取接口"""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # 根据文件扩展名选择提取策略
        suffix = file_path.suffix.lower()
        
        if suffix == '.java':
            return self._extract_spring_endpoints(content, file_path)
        elif suffix == '.py':
            return self._extract_python_endpoints(content, file_path)
        elif suffix == '.go':
            return self._extract_go_endpoints(content, file_path)
        elif suffix in ('.js', '.ts'):
            return self._extract_js_endpoints(content, file_path)
        else:
            return []
    
    def _extract_spring_endpoints(self, content: str, file_path: Path) -> List[ApiEndpoint]:
        """提取Spring Boot接口"""
        endpoints = []
        
        # 提取类名
        class_match = re.search(self.patterns["spring"]["controller"], content, re.DOTALL)
        if not class_match:
            return endpoints
            
        class_name = class_match.group(2)
        
        # 查找所有@RequestMapping注解获取基础路径
        base_path = ""
        base_matches = re.finditer(r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']', content)
        for match in base_matches:
            base_path = match.group(1)
            break
        
        # 提取各个方法映射
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_number = i + 1
            
            # 查找方法映射注解
            mapping_match = re.search(self.patterns["spring"]["mapping"], line)
            if not mapping_match:
                continue
                
            annotation = mapping_match.group(1)  # GetMapping, PostMapping等
            sub_path = mapping_match.group(2)
            
            # 确定HTTP方法
            http_method = self._get_http_method_from_annotation(annotation)
            
            # 查找方法定义（通常在接下来的几行）
            method_name = None
            for j in range(i + 1, min(i + 10, len(lines))):
                method_match = re.search(self.patterns["spring"]["method"], lines[j])
                if method_match:
                    method_name = method_match.group(2)
                    break
                    
            if not method_name:
                continue
                
            # 构建完整路径
            full_path = self._normalize_path(base_path, sub_path)
            
            # 创建端点对象
            endpoint = ApiEndpoint(
                name=f"{class_name}.{method_name}",
                path=full_path,
                method=http_method,
                controller=class_name,
                handler=method_name,
                file_path=str(file_path),
                line_number=line_number,
                framework="spring"
            )
            
            endpoints.append(endpoint)
            
        return endpoints
    
    def _extract_python_endpoints(self, content: str, file_path: Path) -> List[ApiEndpoint]:
        """提取Python Flask/Django接口"""
        endpoints = []
        lines = content.split('\n')
        
        # 尝试Flask风格
        for i, line in enumerate(lines):
            # Flask路由
            flask_match = re.search(self.patterns["flask"]["route"], line)
            if flask_match:
                path = flask_match.group(1)
                method_name = flask_match.group(2)
                
                # 查找HTTP方法
                http_method = "GET"  # 默认
                method_match = re.search(self.patterns["flask"]["method"], line)
                if method_match:
                    http_method = method_match.group(1)
                
                # 查找函数定义
                func_match = None
                for j in range(i + 1, len(lines)):
                    if f"def {method_name}" in lines[j]:
                        func_match = re.search(r'def\s+(\w+)', lines[j])
                        break
                
                if func_match:
                    endpoint = ApiEndpoint(
                        name=method_name,
                        path=path,
                        method=http_method,
                        controller=file_path.stem,
                        handler=method_name,
                        file_path=str(file_path),
                        line_number=i + 1,
                        framework="flask"
                    )
                    endpoints.append(endpoint)
        
        # 尝试Django风格
        for i, line in enumerate(lines):
            django_match = re.search(self.patterns["django"]["url"], line)
            if django_match:
                path = django_match.group(1)
                view_ref = django_match.group(2).strip()
                
                # 解析视图函数/类
                if '.as_view()' in view_ref:
                    # 类视图
                    view_name = view_ref.split('.as_view')[0].split('.')[-1]
                else:
                    # 函数视图
                    view_name = view_ref
                
                endpoint = ApiEndpoint(
                    name=view_name,
                    path=path,
                        method="GET",  # Django需要进一步分析
                    controller=file_path.stem,
                    handler=view_name,
                    file_path=str(file_path),
                    line_number=i + 1,
                    framework="django"
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_go_endpoints(self, content: str, file_path: Path) -> List[ApiEndpoint]:
        """提取Go Gin接口"""
        endpoints = []
        
        gin_matches = re.finditer(self.patterns["gin"]["route"], content)
        
        for match in gin_matches:
            http_method = match.group(1)
            path = match.group(2)
            handler = match.group(3)
            
            # 查找handler函数定义
            func_pattern = rf'func\s+{handler}\s*\([^)]*\)'
            func_match = re.search(func_pattern, content)
            line_number = 1
            
            if func_match:
                # 粗略估计行号
                line_number = content[:func_match.start()].count('\n') + 1
            
            endpoint = ApiEndpoint(
                name=handler,
                path=path,
                method=http_method,
                controller=file_path.stem,
                handler=handler,
                file_path=str(file_path),
                line_number=line_number,
                framework="gin"
            )
            endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_js_endpoints(self, content: str, file_path: Path) -> List[ApiEndpoint]:
        """提取JavaScript/TypeScript接口（Express/Koa）"""
        endpoints = []
        
        # Express.js模式
        express_patterns = [
            r'\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'][^,]*,\s*(?:async\s*)?(?:function\s*)?(\w+)\s*\(',
            r'\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'][^,]*,\s*\([^)]*\)\s*=>'
        ]
        
        for pattern in express_patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                http_method = match.group(1).upper()
                path = match.group(2)
                handler = match.group(3) if len(match.groups()) > 2 else "anonymous"
                
                endpoint = ApiEndpoint(
                    name=handler,
                    path=path,
                    method=http_method,
                    controller=file_path.stem,
                    handler=handler,
                    file_path=str(file_path),
                    line_number=1,  # 简化处理
                    framework="express"
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _get_http_method_from_annotation(self, annotation: str) -> str:
        """从Spring注解获取HTTP方法"""
        mapping = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
            "RequestMapping": "GET"  # 默认
        }
        return mapping.get(annotation, "GET")
    
    def _normalize_path(self, base_path: str, sub_path: str) -> str:
        """规范化URL路径"""
        if not base_path:
            return sub_path if sub_path.startswith('/') else f'/{sub_path}'
        
        if not sub_path:
            return base_path if base_path.startswith('/') else f'/{base_path}'
        
        # 确保没有双斜杠
        base = base_path.rstrip('/')
        sub = sub_path.lstrip('/')
        
        return f'{base}/{sub}' if sub else base