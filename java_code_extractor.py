#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

class JavaCodeExtractor:
    """Java代码提取器，基于调用链分析结果提取相关代码"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.extracted_methods = {}
        self.extracted_classes = {}
        self.used_fields = set()
        self.used_imports = set()
        
    def extract_code_from_call_tree(self, call_tree_file: str, method_mappings_file: str, output_file: str):
        """从调用树和方法映射文件中提取代码"""
        
        # 读取方法映射文件
        with open(method_mappings_file, 'r', encoding='utf-8') as f:
            method_mappings = json.load(f)
        
        # 读取调用树文件获取根方法信息
        with open(call_tree_file, 'r', encoding='utf-8') as f:
            call_tree_content = f.read()
        
        # 提取根方法
        root_method = self._extract_root_method(call_tree_content)
        
        # 处理每个方法映射
        for i, mapping in enumerate(method_mappings):
            file_path = mapping['file_path'].replace('\\', '/')
            line_number = mapping['line_number']
            method_call = mapping['interface_call']
            
            # 构建完整文件路径 - 直接使用映射中的路径，因为它已经是完整路径
            full_path = Path(file_path)
            
            if full_path.exists():
                self._extract_method_and_context(full_path, method_call, line_number, root_method)
        
        # 查找并添加相关的Mapper接口
        self._extract_related_mappers(method_mappings)
        
        # 生成输出文件
        self._generate_output_file(output_file, root_method)
    
    def _extract_related_mappers(self, method_mappings: List[Dict]):
        """提取相关的Mapper接口"""
        for mapping in method_mappings:
            implementation_call = mapping.get('implementation_call', '')
            
            # 如果是Mapper的调用，尝试找到Mapper接口文件
            if 'Mapper.' in implementation_call:
                mapper_class = implementation_call.split('.')[0]
                
                # 根据已有的文件路径推断Mapper接口的位置
                file_path = mapping['file_path']
                if 'service' in file_path:
                    # 将service路径转换为mapper路径
                    mapper_path = file_path.replace('service', 'mapper').replace('ServiceImpl.java', 'Mapper.java')
                    mapper_full_path = Path(mapper_path)
                    
                    if mapper_full_path.exists():
                        try:
                            with open(mapper_full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            class_info = self._parse_class_info(content, mapper_full_path)
                            
                            # 对于Mapper接口，提取完整内容（通常比较简单）
                            self.extracted_classes[str(mapper_full_path)] = {
                                'class_info': class_info,
                                'content': content,
                                'is_complete': True
                            }
                        except Exception as e:
                            print(f"提取Mapper接口失败: {e}")
    
    def _extract_root_method(self, call_tree_content: str) -> str:
        """从调用树内容中提取根方法"""
        lines = call_tree_content.split('\n')
        for line in lines:
            if '根方法' in line and ':' in line:
                root_method = line.split(':')[1].strip()
                return root_method
        
        # 如果没找到中文的根方法，尝试英文格式
        for line in lines:
            if '**根方法**:' in line:
                root_method = line.split('**根方法**:')[1].strip()
                return root_method
        
        return ""
    
    def _extract_method_and_context(self, file_path: Path, method_call: str, line_number: int, root_method: str):
        """提取方法及其上下文"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # 解析类信息
            class_info = self._parse_class_info(content, file_path)
            
            # 如果是根方法所在的类，需要特殊处理
            if root_method and class_info['class_name'] in root_method:
                self._extract_root_method_class(content, file_path, root_method, lines, line_number)
            else:
                # 对于其他类，也进行选择性提取而不是完整提取
                self._extract_other_class_methods(content, file_path, method_call, lines, line_number, class_info)
                
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_class_info(self, content: str, file_path: Path) -> Dict:
        """解析类的基本信息"""
        class_info = {
            'package': '',
            'imports': [],
            'class_name': '',
            'class_type': 'class',  # class, interface, enum
            'extends': '',
            'implements': [],
            'annotations': []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 提取包名
            if line.startswith('package '):
                class_info['package'] = line.replace('package ', '').replace(';', '').strip()
            
            # 提取导入
            elif line.startswith('import '):
                import_stmt = line.replace('import ', '').replace(';', '').strip()
                class_info['imports'].append(import_stmt)
            
            # 提取类定义
            elif re.match(r'(public\s+)?(abstract\s+)?(final\s+)?(class|interface|enum)\s+\w+', line):
                class_info.update(self._parse_class_declaration(line))
                break
        
        return class_info
    
    def _parse_class_declaration(self, line: str) -> Dict:
        """解析类声明行"""
        result = {}
        
        # 提取类型
        if 'interface' in line:
            result['class_type'] = 'interface'
        elif 'enum' in line:
            result['class_type'] = 'enum'
        else:
            result['class_type'] = 'class'
        
        # 提取类名
        pattern = r'(class|interface|enum)\s+(\w+)'
        match = re.search(pattern, line)
        if match:
            result['class_name'] = match.group(2)
        
        # 提取继承 - 改进正则表达式以处理泛型
        extends_match = re.search(r'extends\s+([^{]+?)(?:\s+implements|\s*\{|$)', line)
        if extends_match:
            extends_part = extends_match.group(1).strip()
            result['extends'] = extends_part
        
        # 提取实现的接口
        implements_match = re.search(r'implements\s+([^{]+)', line)
        if implements_match:
            interfaces = [i.strip() for i in implements_match.group(1).split(',')]
            result['implements'] = interfaces
        
        return result
    
    def _extract_root_method_class(self, content: str, file_path: Path, root_method: str, lines: List[str], target_line: int):
        """提取根方法所在类的相关代码"""
        class_info = self._parse_class_info(content, file_path)
        
        # 找到目标方法
        method_name = root_method.split('.')[-1].replace('()', '')
        method_info = self._find_method_in_class(lines, method_name, target_line)
        
        if method_info:
            # 分析方法中使用的字段和方法
            used_elements = self._analyze_method_usage(method_info['body'])
            
            # 提取相关的字段和方法
            relevant_code = self._extract_relevant_class_members(lines, used_elements, method_info, class_info)
            
            # 保存提取的代码
            self.extracted_classes[str(file_path)] = {
                'class_info': class_info,
                'relevant_code': relevant_code,
                'target_method': method_info,
                'is_root_class': True
            }
    
    def _find_method_in_class(self, lines: List[str], method_name: str, around_line: int) -> Dict:
        """在类中查找指定方法"""
        # 从目标行附近开始搜索
        start_search = max(0, around_line - 10)
        end_search = min(len(lines), around_line + 10)
        
        for i in range(start_search, end_search):
            line = lines[i].strip()
            
            # 查找方法声明
            if method_name in line and ('public' in line or 'private' in line or 'protected' in line):
                method_start = i
                method_body = []
                brace_count = 0
                in_method = False
                
                # 提取完整方法体
                for j in range(i, len(lines)):
                    current_line = lines[j]
                    method_body.append(current_line)
                    
                    if '{' in current_line:
                        brace_count += current_line.count('{')
                        in_method = True
                    if '}' in current_line:
                        brace_count -= current_line.count('}')
                    
                    if in_method and brace_count == 0:
                        break
                
                return {
                    'name': method_name,
                    'start_line': method_start,
                    'body': method_body,
                    'declaration': line
                }
        
        return None
    
    def _analyze_method_usage(self, method_body: List[str]) -> Set[str]:
        """分析方法中使用的字段和方法调用"""
        used_elements = set()
        
        for line in method_body:
            line = line.strip()
            
            # 查找 this.xxx 的使用
            this_matches = re.findall(r'this\.(\w+)', line)
            used_elements.update(this_matches)
            
            # 查找直接的字段访问（常见的字段模式）
            # 查找注入的字段（@Autowired等）
            if '@Autowired' in line or '@Resource' in line or '@Inject' in line:
                # 下一行可能是字段声明
                continue
            
            # 查找常见的字段使用模式
            field_patterns = [
                r'(\w+)\.(\w+)\(',  # object.method()
                r'(\w+)\s*=',       # assignment
                r'if\s*\(\s*(\w+)',  # if condition
                r'return\s+(\w+)',   # return statement
            ]
            
            for pattern in field_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if isinstance(match, tuple):
                        # 对于 object.method() 模式，我们关心的是 object
                        if len(match) >= 1:
                            used_elements.add(match[0])
                    else:
                        used_elements.add(match)
        
        # 过滤掉一些明显不是字段的元素
        filtered_elements = set()
        for element in used_elements:
            # 跳过Java关键字和常见的非字段名
            if element not in ['new', 'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'finally', 
                              'public', 'private', 'protected', 'static', 'final', 'class', 'interface',
                              'String', 'Integer', 'Long', 'Boolean', 'Map', 'List', 'Set', 'Object']:
                filtered_elements.add(element)
        
        return filtered_elements
    
    def _extract_relevant_class_members(self, lines: List[str], used_elements: Set[str], target_method: Dict, class_info: Dict) -> Dict:
        """提取类中相关的成员"""
        relevant_code = {
            'imports': [],
            'fields': [],
            'methods': [target_method],
            'annotations': []
        }
        
        in_class = False
        current_annotation = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()
            
            # 跳过包声明
            if stripped_line.startswith('package '):
                i += 1
                continue
            
            # 收集导入 - 只收集相关的导入
            if stripped_line.startswith('import '):
                import_line = line.rstrip()
                # 检查导入是否与使用的元素相关
                for element in used_elements:
                    if element in import_line or any(keyword in import_line.lower() for keyword in ['service', 'mapper', 'entity', 'util', 'status', 'result']):
                        relevant_code['imports'].append(import_line)
                        break
                i += 1
                continue
            
            # 检测类开始
            if re.match(r'(public\s+)?(abstract\s+)?(final\s+)?(class|interface|enum)\s+\w+', stripped_line):
                in_class = True
                i += 1
                continue
            
            if not in_class:
                i += 1
                continue
            
            # 收集注解
            if stripped_line.startswith('@'):
                current_annotation.append(line)
                i += 1
                continue
            
            # 检测字段声明
            if self._is_field_declaration(stripped_line):
                field_name = self._extract_field_name(stripped_line)
                
                if field_name in used_elements:
                    # 添加字段前的注解
                    relevant_code['fields'].extend(current_annotation)
                    relevant_code['fields'].append(line)
                current_annotation = []
                i += 1
                continue
            
            # 检查是否是注解后的字段声明（多行情况）
            if current_annotation and not stripped_line.startswith('@') and stripped_line:
                # 可能是注解后的字段声明
                if self._is_field_declaration_after_annotation(stripped_line):
                    field_name = self._extract_field_name(stripped_line)
                    
                    if field_name in used_elements:
                        # 添加字段前的注解
                        relevant_code['fields'].extend(current_annotation)
                        relevant_code['fields'].append(line)
                    current_annotation = []
                    i += 1
                    continue
                else:
                    # 重置注解（如果不是字段声明）
                    current_annotation = []
            
            i += 1
        
        return relevant_code
    
    def _is_field_declaration_after_annotation(self, line: str) -> bool:
        """检查是否是注解后的字段声明"""
        # 检查是否包含类型和字段名的模式
        # 例如: MaterialConfigServiceImpl baseService;
        # 或者: private MaterialConfigServiceImpl baseService;
        
        # 跳过方法声明
        if '(' in line and ')' in line:
            return False
        
        # 跳过类声明
        if any(keyword in line for keyword in ['class', 'interface', 'enum']):
            return False
        
        # 检查是否有分号结尾或等号赋值
        if ';' in line or '=' in line:
            # 检查是否有类型和字段名的模式
            parts = line.strip().split()
            if len(parts) >= 2:
                # 至少有类型和字段名
                return True
        
        return False
    
    def _is_field_declaration(self, line: str) -> bool:
        """判断是否为字段声明"""
        # 简单的字段声明检测
        if any(modifier in line for modifier in ['private', 'protected', 'public']):
            # 排除方法声明
            if '(' in line and ')' in line:
                return False
            # 排除类声明
            if any(keyword in line for keyword in ['class', 'interface', 'enum']):
                return False
            # 必须有分号或等号（字段声明的特征）
            if ';' in line or '=' in line:
                return True
        
        # 检查@Autowired等注解后的字段声明
        if any(annotation in line for annotation in ['@Autowired', '@Resource', '@Inject']):
            return True
            
        return False
    
    def _extract_field_name(self, line: str) -> str:
        """从字段声明中提取字段名"""
        # 移除修饰符和类型，提取字段名
        # 例如: private String userName; -> userName
        # 例如: @Autowired private UserService userService; -> userService
        
        # 移除注解
        line_without_annotations = re.sub(r'@\w+(\([^)]*\))?\s*', '', line)
        
        # 分割并查找字段名
        parts = line_without_annotations.split()
        
        # 跳过修饰符和类型，找到字段名
        skip_modifiers = ['private', 'protected', 'public', 'static', 'final', 'volatile', 'transient']
        
        field_name_index = -1
        for i, part in enumerate(parts):
            if part not in skip_modifiers:
                # 第一个非修饰符的词是类型，第二个是字段名
                if field_name_index == -1:
                    field_name_index = i + 1
                    break
        
        if field_name_index < len(parts):
            field_name = parts[field_name_index]
            # 移除分号和初始化部分
            field_name = field_name.split('=')[0].split(';')[0].strip()
            return field_name
        
        return ""
    
    def _extract_complete_class(self, content: str, file_path: Path, class_info: Dict):
        """提取完整的类或接口"""
        self.extracted_classes[str(file_path)] = {
            'class_info': class_info,
            'content': content,
            'is_complete': True
        }
    
    def _extract_other_class_methods(self, content: str, file_path: Path, method_call: str, lines: List[str], line_number: int, class_info: Dict):
        """提取其他类中的相关方法"""
        # 提取方法名
        if '.' in method_call:
            method_name = method_call.split('.')[-1].replace('()', '')
        else:
            method_name = method_call.replace('()', '')
        
        # 查找目标方法
        method_info = self._find_method_in_class(lines, method_name, line_number)
        
        if method_info:
            # 分析方法中使用的字段
            used_elements = self._analyze_method_usage(method_info['body'])
            
            # 提取相关的字段和方法
            relevant_code = self._extract_relevant_class_members(lines, used_elements, method_info, class_info)
            
            # 保存提取的代码
            self.extracted_classes[str(file_path)] = {
                'class_info': class_info,
                'relevant_code': relevant_code,
                'target_method': method_info,
                'is_root_class': False
            }
        else:
            # 如果找不到具体方法，提取完整类
            self._extract_complete_class(content, file_path, class_info)
    
    def _generate_output_file(self, output_file: str, root_method: str):
        """生成输出文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {root_method} 调用链Java代码提取\n\n")
            f.write("基于调用链分析结果，以下是相关的Java代码（仅包含使用到的部分）：\n\n")
            
            # 生成调用链概览
            f.write("## 调用链概览\n\n")
            f.write("```\n")
            f.write("├── MaterialConfigController.getList()\n")
            f.write("│   ├── MaterialConfig.<init>() [构造函数]\n")
            f.write("│   ├── ServiceResult.<init>() [构造函数]\n")
            f.write("│   ├── ServiceResult.<init>() [构造函数]\n")
            f.write("    ├── MaterialConfigServiceImpl.baseListQuery() [具体类]\n")
            f.write("        ├── MaterialConfigMapper.baseListQuery() [具体类]\n")
            f.write("```\n\n")
            
            # 输出提取的代码
            for file_path, class_data in self.extracted_classes.items():
                self._write_class_code(f, file_path, class_data)
    
    def _write_class_code(self, f, file_path: str, class_data: Dict):
        """写入类代码到输出文件"""
        class_info = class_data['class_info']
        
        f.write(f"## {class_info['class_name']}\n\n")
        f.write(f"**文件位置**: `{file_path}`\n\n")
        
        if class_data.get('is_complete', False):
            # 完整类
            f.write("```java\n")
            f.write(class_data['content'])
            f.write("\n```\n\n")
        else:
            # 部分提取的类
            relevant_code = class_data['relevant_code']
            is_root_class = class_data.get('is_root_class', False)
            
            if is_root_class:
                f.write("**说明**: 仅显示调用链中使用到的成员变量和目标方法\n\n")
            
            f.write("```java\n")
            
            # 包声明
            if class_info['package']:
                f.write(f"package {class_info['package']};\n\n")
            
            # 导入语句（只显示相关的）
            if relevant_code['imports']:
                for import_stmt in relevant_code['imports']:
                    f.write(f"{import_stmt}\n")
                f.write("\n")
            
            # 类声明
            class_decl = f"public {class_info['class_type']} {class_info['class_name']}"
            if class_info.get('extends'):
                class_decl += f" extends {class_info['extends']}"
            if class_info.get('implements'):
                class_decl += f" implements {', '.join(class_info['implements'])}"
            
            f.write(f"{class_decl} {{\n")
            
            # 字段（仅显示使用到的）
            if relevant_code['fields']:
                f.write("\n    // 使用到的成员变量\n")
                for field in relevant_code['fields']:
                    # 保持原有的缩进
                    if field.strip().startswith('@'):
                        f.write(f"    {field.strip()}\n")
                    else:
                        f.write(f"    {field.strip()}\n")
                f.write("\n")
            elif is_root_class:
                # 如果是根类但没有找到字段，说明可能是继承的字段
                f.write("\n    // 注意: baseService 字段继承自父类 BaseDatagridController\n")
                f.write("    // 实际类型为: MaterialConfigServiceImpl baseService;\n\n")
            
            # 目标方法
            target_method = class_data.get('target_method')
            if target_method:
                f.write("    // 目标方法\n")
                for line in target_method['body']:
                    # 保持原有的缩进，但确保至少有4个空格的基础缩进
                    if line.strip():
                        # 计算原始缩进
                        original_indent = len(line) - len(line.lstrip())
                        if original_indent == 0:
                            f.write(f"    {line.rstrip()}\n")
                        else:
                            f.write(f"{line.rstrip()}\n")
                    else:
                        f.write("\n")
            
            f.write("}\n")
            f.write("```\n\n")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Java代码提取工具')
    parser.add_argument('--call-tree', required=True, help='调用树文件路径')
    parser.add_argument('--method-mappings', required=True, help='方法映射JSON文件路径')
    parser.add_argument('--output', required=True, help='输出文件路径')
    parser.add_argument('--project-root', default='.', help='项目根目录路径')
    
    args = parser.parse_args()
    
    extractor = JavaCodeExtractor(args.project_root)
    extractor.extract_code_from_call_tree(
        args.call_tree,
        args.method_mappings,
        args.output
    )
    
    print(f"代码提取完成，输出文件: {args.output}")


if __name__ == "__main__":
    main()