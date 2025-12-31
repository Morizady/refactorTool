#!/usr/bin/env python3
"""
Java HTTP接口提取器 - 专注于Spring Boot框架
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
    framework: str = "spring"   # 框架类型: spring
    
    def __hash__(self):
        return hash(f"{self.path}:{self.method}:{self.file_path}")

class EndpointExtractor:
    """Java HTTP接口提取器 - 专注于Spring Boot框架"""
    
    def __init__(self):
        # 定义Spring框架的识别模式
        self.patterns = {
            "spring": {
                "controller": r'@(RestController|Controller)\s*.*?class\s+(\w+)',
                "mapping": r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping|PatchMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
                "method": r'(public|private|protected)\s+[^{]*?\s+(\w+)\s*\([^)]*\)'
            }
        }
        
    def extract_from_project(self, project_path: str) -> Dict[str, ApiEndpoint]:
        """从Java项目中提取所有HTTP接口"""
        endpoints = {}
        
        project_path = Path(project_path)
        
        # 遍历项目文件，只处理Java文件
        for root, dirs, files in os.walk(project_path):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'target', 'build', 'node_modules', 'venv', '__pycache__'}]
            
            for file in files:
                if not file.endswith('.java'):
                    continue
                    
                file_path = Path(root) / file
                
                # 提取Java接口
                file_endpoints = self.extract_endpoints_from_file(file_path)
                
                for endpoint in file_endpoints:
                    # 使用 path:method 作为唯一键
                    key = f"{endpoint.path}:{endpoint.method}"
                    endpoints[key] = endpoint
                    
        return endpoints
    
    def extract_endpoints_from_file(self, file_path: Path) -> List[ApiEndpoint]:
        """从Java文件提取接口"""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # 只处理Java文件
        if file_path.suffix.lower() == '.java':
            return self._extract_spring_endpoints(content, file_path)
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
        base_matches = re.finditer(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', content)
        for match in base_matches:
            base_path = match.group(1)
            break
        
        # 提取各个方法映射
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_number = i + 1
            
            # 查找方法映射注解
            mapping_match = re.search(self.patterns["spring"]["mapping"], line)
            if not mapping_match:
                i += 1
                continue
                
            annotation = mapping_match.group(1)  # GetMapping, PostMapping等
            sub_path = mapping_match.group(2)
            
            # 确定HTTP方法
            http_method = self._get_http_method_from_annotation(annotation, line)
            
            # 查找方法定义（通常在接下来的几行）
            method_name = None
            method_line_number = line_number
            
            # 向前查找方法定义，最多查找15行
            for j in range(i + 1, min(i + 15, len(lines))):
                current_line = lines[j].strip()
                
                # 跳过空行和注解行
                if not current_line or current_line.startswith('@'):
                    continue
                
                method_match = re.search(self.patterns["spring"]["method"], current_line)
                if method_match:
                    method_name = method_match.group(2)
                    method_line_number = j + 1
                    break
                    
            if not method_name:
                i += 1
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
                line_number=method_line_number,
                framework="spring"
            )
            
            endpoints.append(endpoint)
            i += 1
            
        return endpoints
    
    def _get_http_method_from_annotation(self, annotation: str, line: str = "") -> str:
        """从Spring注解获取HTTP方法"""
        mapping = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
        }
        
        if annotation in mapping:
            return mapping[annotation]
        
        # 处理@RequestMapping的method参数
        if annotation == "RequestMapping":
            # 查找method参数
            method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', line)
            if method_match:
                return method_match.group(1).upper()
            else:
                return "GET"  # 默认GET方法
        
        return "GET"  # 默认
    
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