#!/usr/bin/env python3
"""
SQL映射分析器 - 分析MyBatis/ORM相关的映射文件
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

class SQLMapperAnalyzer:
    """SQL映射分析器"""
    
    def __init__(self):
        self.xml_namespace = {
            'mapper': 'http://mybatis.org/dtd/mybatis-3-mapper.dtd'
        }
    
    def find_related_mappers(self, call_chain: Dict, project_path: str) -> List[Dict]:
        """查找相关的SQL映射文件"""
        related_mappers = []
        project_root = Path(project_path)
        
        # 1. 从调用链中提取可能的Mapper名称
        mapper_candidates = self._extract_mapper_candidates(call_chain)
        
        # 2. 查找对应的XML映射文件
        for candidate in mapper_candidates:
            mapper_files = self._find_mapper_files(project_root, candidate)
            
            for mapper_file in mapper_files:
                mapper_info = self._analyze_mapper_file(mapper_file, project_root)
                if mapper_info:
                    related_mappers.append(mapper_info)
        
        # 3. 查找注解形式的Mapper（如MyBatis注解）
        annotated_mappers = self._find_annotated_mappers(call_chain, project_root)
        related_mappers.extend(annotated_mappers)
        
        return related_mappers
    
    def _extract_mapper_candidates(self, call_chain: Dict) -> List[str]:
        """从调用链提取Mapper候选"""
        candidates = set()
        
        # 从方法调用中提取
        for call in call_chain.get("method_calls", []):
            method_name = call.get("method", "").lower()
            object_name = call.get("object", "").lower()
            
            # 常见的Mapper相关模式
            if any(keyword in method_name for keyword in ['select', 'insert', 'update', 'delete', 'query']):
                if object_name:
                    candidates.add(object_name)
            
            if any(keyword in object_name for keyword in ['mapper', 'dao', 'repository']):
                candidates.add(object_name)
        
        # 从SQL语句中提取表名
        for sql in call_chain.get("sql_statements", []):
            table_names = self._extract_table_names(sql)
            candidates.update(table_names)
        
        return list(candidates)
    
    def _find_mapper_files(self, project_root: Path, mapper_name: str) -> List[Path]:
        """查找Mapper XML文件"""
        mapper_files = []
        
        # 常见的位置
        search_paths = [
            project_root / "src/main/resources/mapper",
            project_root / "resources/mapper",
            project_root / "mapper",
            project_root / "src/main/resources",
            project_root / "src/resources",
        ]
        
        # 可能的文件名模式
        name_patterns = [
            f"*{mapper_name}*Mapper.xml",
            f"*{mapper_name}*Dao.xml",
            f"*{mapper_name}*.xml",
            f"{mapper_name}*.xml",
        ]
        
        for search_path in search_paths:
            if search_path.exists() and search_path.is_dir():
                for pattern in name_patterns:
                    found_files = list(search_path.rglob(pattern))
                    mapper_files.extend(found_files)
        
        # 如果没找到，在整个项目中搜索
        if not mapper_files:
            for pattern in name_patterns:
                found_files = list(project_root.rglob(pattern))
                mapper_files.extend(found_files)
        
        return list(set(mapper_files))[:10]  # 限制数量
    
    def _analyze_mapper_file(self, mapper_file: Path, project_root: Path) -> Optional[Dict]:
        """分析Mapper XML文件"""
        try:
            content = mapper_file.read_text(encoding='utf-8', errors='ignore')
            
            # 解析XML
            try:
                root = ET.fromstring(content)
            except ET.ParseError:
                # 如果解析失败，使用正则提取信息
                return self._parse_mapper_with_regex(content, mapper_file, project_root)
            
            # 提取Mapper信息
            namespace = root.get('namespace', '')
            methods = []
            
            # 查找所有的SQL操作
            sql_elements = ['select', 'insert', 'update', 'delete']
            for elem_name in sql_elements:
                for elem in root.findall(elem_name, self.xml_namespace):
                    method_info = {
                        "id": elem.get('id', ''),
                        "type": elem_name,
                        "parameterType": elem.get('parameterType', ''),
                        "resultType": elem.get('resultType', ''),
                        "sql": self._extract_sql_text(elem)
                    }
                    methods.append(method_info)
            
            return {
                "file_path": str(mapper_file.relative_to(project_root)),
                "namespace": namespace,
                "methods": methods,
                "file_type": "xml_mapper"
            }
            
        except Exception as e:
            print(f"解析Mapper文件失败 {mapper_file}: {e}")
            return None
    
    def _parse_mapper_with_regex(self, content: str, mapper_file: Path, project_root: Path) -> Dict:
        """使用正则表达式解析Mapper文件"""
        methods = []
        
        # 正则匹配SQL语句
        sql_patterns = [
            (r'<select[^>]*id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</select>', 'select'),
            (r'<insert[^>]*id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</insert>', 'insert'),
            (r'<update[^>]*id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</update>', 'update'),
            (r'<delete[^>]*id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</delete>', 'delete'),
        ]
        
        for pattern, sql_type in sql_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                method_id = match[0]
                sql_fragment = match[1]
                
                # 清理SQL
                sql_text = self._clean_sql_text(sql_fragment)
                
                methods.append({
                    "id": method_id,
                    "type": sql_type,
                    "sql": sql_text
                })
        
        # 提取namespace
        namespace_match = re.search(r'namespace=["\']([^"\']+)["\']', content)
        namespace = namespace_match.group(1) if namespace_match else ""
        
        return {
            "file_path": str(mapper_file.relative_to(project_root)),
            "namespace": namespace,
            "methods": methods,
            "file_type": "xml_mapper_regex",
            "note": "Parsed with regex due to XML parsing error"
        }
    
    def _extract_sql_text(self, elem) -> str:
        """从XML元素提取SQL文本"""
        sql_parts = []
        
        # 提取文本内容
        if elem.text and elem.text.strip():
            sql_parts.append(elem.text.strip())
        
        # 提取CDATA部分
        for child in elem:
            if child.tag == '![CDATA[':
                sql_parts.append(child.text.strip() if child.text else '')
            elif child.text and child.text.strip():
                sql_parts.append(child.text.strip())
        
        return ' '.join(sql_parts)
    
    def _clean_sql_text(self, sql: str) -> str:
        """清理SQL文本"""
        # 移除XML标签
        sql = re.sub(r'<[^>]+>', ' ', sql)
        # 标准化空格
        sql = re.sub(r'\s+', ' ', sql)
        # 移除CDATA标记
        sql = sql.replace('<![CDATA[', '').replace(']]>', '')
        return sql.strip()
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """从SQL语句提取表名"""
        table_names = []
        
        # 简单的表名提取（实际项目需要更复杂的解析）
        patterns = [
            r'from\s+(\w+)',
            r'join\s+(\w+)',
            r'into\s+(\w+)',
            r'update\s+(\w+)',
            r'table\s+(\w+)',
        ]
        
        sql_lower = sql.lower()
        for pattern in patterns:
            matches = re.findall(pattern, sql_lower, re.IGNORECASE)
            table_names.extend(matches)
        
        # 过滤掉常见的关键字
        keywords = {'select', 'where', 'set', 'values', 'from', 'join', 'inner', 'left', 'right'}
        return [name for name in table_names if name.lower() not in keywords]
    
    def _find_annotated_mappers(self, call_chain: Dict, project_root: Path) -> List[Dict]:
        """查找注解形式的Mapper（如@Select, @Insert等）"""
        annotated_mappers = []
        
        # 在Java文件中查找MyBatis注解
        java_files = list(project_root.rglob("*.java"))
        
        for java_file in java_files[:100]:  # 限制搜索数量
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                
                # 检查是否有Mapper注解
                if '@Mapper' in content or '@Repository' in content:
                    # 提取方法上的SQL注解
                    methods = self._extract_annotated_methods(content)
                    
                    if methods:
                        mapper_info = {
                            "file_path": str(java_file.relative_to(project_root)),
                            "methods": methods,
                            "file_type": "annotated_mapper"
                        }
                        annotated_mappers.append(mapper_info)
                        
            except Exception:
                continue
        
        return annotated_mappers
    
    def _extract_annotated_methods(self, content: str) -> List[Dict]:
        """从Java内容提取注解方法"""
        methods = []
        
        # MyBatis注解模式
        annotation_patterns = [
            (r'@Select\(["\']([^"\']+)["\']\)', 'select'),
            (r'@Insert\(["\']([^"\']+)["\']\)', 'insert'),
            (r'@Update\(["\']([^"\']+)["\']\)', 'update'),
            (r'@Delete\(["\']([^"\']+)["\']\)', 'delete'),
        ]
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            for pattern, sql_type in annotation_patterns:
                match = re.search(pattern, line)
                if match:
                    sql = match.group(1)
                    
                    # 查找方法定义（通常在注解后面）
                    method_name = None
                    for j in range(i + 1, min(i + 5, len(lines))):
                        method_match = re.search(r'(public|private|protected)\s+[^{]+\s+(\w+)\s*\(', lines[j])
                        if method_match:
                            method_name = method_match.group(2)
                            break
                    
                    methods.append({
                        "id": method_name or f"anonymous_{i}",
                        "type": sql_type,
                        "sql": sql
                    })
        
        return methods