#!/usr/bin/env python3
"""
增强版JDT调用链分析器 - 集成JAR包方法推理
支持推理外部JAR包中的方法，特别是MyBatis-Plus、Spring等框架方法
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer, CallTreeNode, MethodMapping
from jar_method_resolver import JarMethodResolver, FrameworkMethod

logger = logging.getLogger(__name__)

class EnhancedJDTAnalyzer(JDTDeepCallChainAnalyzer):
    """增强版JDT分析器，集成JAR包方法推理"""
    
    def __init__(self, project_root: str, config_path: str = "config.yml", 
                 ignore_methods_file: str = "igonre_method.txt", 
                 show_getters_setters: bool = True, 
                 show_constructors: bool = True):
        
        # 初始化父类
        super().__init__(project_root, config_path, ignore_methods_file, 
                        show_getters_setters, show_constructors)
        
        # 初始化JAR方法推理器
        self.jar_resolver = JarMethodResolver()
        
        # 统计信息
        self.resolved_jar_methods = []  # 推理出的JAR方法
        self.unresolved_methods = []    # 无法推理的方法
        
        logger.info("✅ 增强版JDT分析器初始化完成，支持JAR包方法推理")
    
    def _resolve_method_call(self, call: Dict, current_file: str, depth: int) -> List[CallTreeNode]:
        """
        重写方法调用解析，集成JAR包推理
        """
        # 先调用父类的解析方法
        nodes = super()._resolve_method_call(call, current_file, depth)
        
        # 如果父类解析成功且不是unresolved，直接返回
        if nodes and any(node.call_type != "unresolved" for node in nodes):
            return nodes
        
        # 如果父类解析失败或返回unresolved，尝试JAR包推理
        method_name = call["method"]
        object_name = call.get("object", "")
        resolved_type = call.get("resolved_type", "")
        
        # 确定要推理的类名
        target_class = resolved_type or object_name
        if not target_class:
            return nodes  # 无法确定类名，返回原结果
        
        # 构建推理上下文
        context = self._build_inference_context(current_file)
        
        # 尝试推理JAR方法
        jar_method = self.jar_resolver.resolve_method(target_class, method_name, context)
        
        if jar_method:
            logger.debug(f"🎯 JAR推理成功: {target_class}.{method_name} -> {jar_method.framework}")
            
            # 创建推理出的节点
            jar_node = CallTreeNode(
                method_name=jar_method.method_name,
                class_name=jar_method.class_name,
                package_name=jar_method.package,
                file_path="",  # JAR包中的方法没有源文件
                line_number=call.get("line", 0),
                call_type="jar_resolved",  # 新的调用类型
                parameters=jar_method.parameters,
                return_type=jar_method.return_type,
                children=[],
                method_mappings=[],
                depth=depth
            )
            
            # 记录推理信息
            self.resolved_jar_methods.append({
                "original_call": f"{object_name}.{method_name}()",
                "resolved_method": jar_method,
                "file": current_file,
                "line": call.get("line", 0)
            })
            
            return [jar_node]
        else:
            # 推理失败，记录未解析的方法
            self.unresolved_methods.append({
                "class": target_class,
                "method": method_name,
                "file": current_file,
                "line": call.get("line", 0),
                "reason": "无法推理JAR方法"
            })
            
            return nodes  # 返回原结果
    
    def _build_inference_context(self, current_file: str) -> Dict:
        """构建推理上下文信息"""
        context = {
            'class_hierarchy': self.class_hierarchy,
            'interface_implementations': self.interface_implementations,
            'imports': self.package_imports.get(current_file, []),
            'static_imports': self.static_imports.get(current_file, {}),
        }
        
        # 添加当前文件的类信息
        current_class = self._find_class_by_file(current_file)
        if current_class:
            context['current_class'] = {
                'name': current_class.name,
                'package': current_class.package,
                'extends': current_class.extends,
                'implements': current_class.implements,
                'fields': [{'name': f.get('name'), 'type': f.get('type')} 
                          for f in current_class.fields]
            }
        
        return context
    
    def _build_call_tree_markdown(self, call_tree: CallTreeNode, endpoint_path: str) -> str:
        """
        重写报告生成，包含JAR推理信息
        """
        # 调用父类方法生成基础报告
        base_content = super()._build_call_tree_markdown(call_tree, endpoint_path)
        
        # 添加JAR推理统计信息
        jar_stats = self._build_jar_resolution_stats()
        
        # 在统计信息后插入JAR推理信息
        lines = base_content.split('\n')
        
        # 找到统计信息部分的结束位置
        stats_end_index = -1
        for i, line in enumerate(lines):
            if line.startswith("## 深度调用树"):
                stats_end_index = i
                break
        
        if stats_end_index > 0:
            # 在统计信息后插入JAR推理信息
            jar_lines = jar_stats.split('\n')
            lines = lines[:stats_end_index] + jar_lines + [''] + lines[stats_end_index:]
        
        return '\n'.join(lines)
    
    def _build_jar_resolution_stats(self) -> str:
        """构建JAR推理统计信息"""
        lines = []
        
        lines.append("## JAR包方法推理统计")
        lines.append("")
        lines.append(f"- **推理成功**: {len(self.resolved_jar_methods)} 个方法")
        lines.append(f"- **推理失败**: {len(self.unresolved_methods)} 个方法")
        
        # 按框架分组统计
        framework_stats = {}
        for resolved in self.resolved_jar_methods:
            framework = resolved['resolved_method'].framework
            if framework not in framework_stats:
                framework_stats[framework] = 0
            framework_stats[framework] += 1
        
        if framework_stats:
            lines.append("- **框架分布**:")
            for framework, count in framework_stats.items():
                lines.append(f"  - {framework}: {count} 个方法")
        
        lines.append("")
        
        # 推理成功的方法详情
        if self.resolved_jar_methods:
            lines.append("### 推理成功的JAR方法")
            lines.append("")
            lines.append("| 原始调用 | 推理结果 | 框架 | 描述 | 文件位置 |")
            lines.append("|----------|----------|------|------|----------|")
            
            for resolved in self.resolved_jar_methods[:10]:  # 限制显示数量
                method = resolved['resolved_method']
                original = resolved['original_call']
                resolved_call = f"{method.class_name}.{method.method_name}()"
                file_name = Path(resolved['file']).name if resolved['file'] else "unknown"
                
                lines.append(f"| `{original}` | `{resolved_call}` | {method.framework} | {method.description} | {file_name}:{resolved['line']} |")
            
            if len(self.resolved_jar_methods) > 10:
                lines.append(f"| ... | ... | ... | ... | 还有 {len(self.resolved_jar_methods) - 10} 个推理结果 |")
        
        lines.append("")
        
        # 推理失败的方法
        if self.unresolved_methods:
            lines.append("### 无法推理的方法")
            lines.append("")
            lines.append("| 类名 | 方法名 | 失败原因 | 文件位置 |")
            lines.append("|------|--------|----------|----------|")
            
            for unresolved in self.unresolved_methods[:5]:  # 限制显示数量
                class_name = unresolved['class']
                method_name = unresolved['method']
                reason = unresolved['reason']
                file_name = Path(unresolved['file']).name if unresolved['file'] else "unknown"
                
                lines.append(f"| `{class_name}` | `{method_name}` | {reason} | {file_name}:{unresolved['line']} |")
            
            if len(self.unresolved_methods) > 5:
                lines.append(f"| ... | ... | ... | 还有 {len(self.unresolved_methods) - 5} 个未推理方法 |")
        
        lines.append("")
        
        return '\n'.join(lines)
    
    def _build_tree_visualization(self, node: CallTreeNode, lines: List[str], prefix: str):
        """
        重写树形可视化，添加JAR推理标记
        """
        # 构建当前节点显示
        node_display = f"{node.class_name}.{node.method_name}()"
        type_marker = ""
        
        if node.call_type == "jar_resolved":
            type_marker = " [JAR推理]"
        elif node.call_type == "interface":
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
        elif node.call_type == "unresolved":
            type_marker = " [未解析]"
        
        lines.append(f"{prefix}├── {node_display}{type_marker}")
        
        # 递归处理子节点
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._build_tree_visualization(child, lines, child_prefix)
    
    def get_jar_resolution_summary(self) -> Dict:
        """获取JAR推理摘要信息"""
        framework_stats = {}
        for resolved in self.resolved_jar_methods:
            framework = resolved['resolved_method'].framework
            if framework not in framework_stats:
                framework_stats[framework] = 0
            framework_stats[framework] += 1
        
        return {
            "resolved_count": len(self.resolved_jar_methods),
            "unresolved_count": len(self.unresolved_methods),
            "framework_distribution": framework_stats,
            "resolution_rate": len(self.resolved_jar_methods) / (len(self.resolved_jar_methods) + len(self.unresolved_methods)) if (len(self.resolved_jar_methods) + len(self.unresolved_methods)) > 0 else 0
        }
    
    def add_custom_framework_method(self, framework: str, class_name: str, method: FrameworkMethod):
        """添加自定义框架方法"""
        self.jar_resolver.framework_methods.setdefault(framework, {}).setdefault(class_name, []).append(method)
        logger.info(f"✅ 添加自定义框架方法: {framework}.{class_name}.{method.method_name}")
    
    def save_jar_resolution_report(self, output_dir: str = "./migration_output"):
        """保存JAR推理报告"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存推理成功的方法
        resolved_file = f"{output_dir}/jar_resolved_methods.json"
        import json
        
        resolved_data = []
        for resolved in self.resolved_jar_methods:
            method = resolved['resolved_method']
            resolved_data.append({
                "original_call": resolved['original_call'],
                "resolved_class": method.class_name,
                "resolved_method": method.method_name,
                "framework": method.framework,
                "description": method.description,
                "parameters": method.parameters,
                "return_type": method.return_type,
                "is_inherited": method.is_inherited,
                "parent_class": method.parent_class,
                "file": resolved['file'],
                "line": resolved['line']
            })
        
        with open(resolved_file, 'w', encoding='utf-8') as f:
            json.dump(resolved_data, f, indent=2, ensure_ascii=False)
        
        # 保存未推理的方法
        unresolved_file = f"{output_dir}/jar_unresolved_methods.json"
        with open(unresolved_file, 'w', encoding='utf-8') as f:
            json.dump(self.unresolved_methods, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ JAR推理报告已保存:")
        logger.info(f"  - 推理成功: {resolved_file}")
        logger.info(f"  - 推理失败: {unresolved_file}")


# 使用示例
def test_enhanced_jdt_analyzer():
    """测试增强版JDT分析器"""
    project_path = "test_projects/sc_pcc_config"
    
    if not os.path.exists(project_path):
        print(f"测试项目不存在: {project_path}")
        return
    
    # 创建增强版分析器
    analyzer = EnhancedJDTAnalyzer(project_path)
    
    # 测试方法调用分析
    controller_file = "test_projects/sc_pcc_config/src/main/java/com/unicom/microserv/cs/pcc/config/materialConfig/controller/MaterialConfigController.java"
    
    if os.path.exists(controller_file):
        print("🔍 分析MaterialConfigController.saveOrUpdate方法...")
        
        # 分析深度调用树
        call_tree = analyzer.analyze_deep_call_tree(controller_file, "saveOrUpdate", max_depth=4)
        
        if call_tree:
            # 生成报告
            report_file = analyzer.generate_call_tree_report(call_tree, "POST /materialConfig/saveOrUpdate")
            print(f"✅ 报告生成完成: {report_file}")
            
            # 获取JAR推理摘要
            summary = analyzer.get_jar_resolution_summary()
            print(f"📊 JAR推理摘要:")
            print(f"  - 推理成功: {summary['resolved_count']} 个方法")
            print(f"  - 推理失败: {summary['unresolved_count']} 个方法")
            print(f"  - 推理成功率: {summary['resolution_rate']:.2%}")
            
            if summary['framework_distribution']:
                print(f"  - 框架分布:")
                for framework, count in summary['framework_distribution'].items():
                    print(f"    - {framework}: {count} 个方法")
            
            # 保存JAR推理报告
            analyzer.save_jar_resolution_report()
        else:
            print("❌ 分析失败")
    else:
        print(f"❌ 控制器文件不存在: {controller_file}")
    
    analyzer.shutdown()


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    test_enhanced_jdt_analyzer()