#!/usr/bin/env python3
"""
AI代码分析器 - 结合AI模块和代码分析功能

演示如何使用AI模块分析migration_output中的代码分析结果。
"""

import os
import json
import logging
from pathlib import Path
from ai_module import AIManager, OllamaProvider
from ai_module.config import load_config
from ai_module.utils import setup_logging, format_code_for_ai

# 设置日志
setup_logging("INFO")
logger = logging.getLogger(__name__)


class AICodeAnalyzer:
    """AI代码分析器"""
    
    def __init__(self, config_path: str = "ai_config.yaml"):
        """初始化AI代码分析器"""
        self.config = load_config(config_path)
        self.ai_manager = AIManager()
        self._setup_ai_provider()
    
    def _setup_ai_provider(self):
        """设置AI提供者"""
        ollama_provider = OllamaProvider(
            base_url=self.config.ollama.base_url,
            timeout=self.config.ollama.timeout,
            default_model=self.config.ollama.default_model  # 使用配置中的默认模型
        )
        
        if self.ai_manager.register_provider(ollama_provider, set_as_default=True, config=self.config.ollama.to_dict()):
            logger.info("✅ AI提供者初始化成功")
        else:
            logger.error("❌ AI提供者初始化失败")
            raise RuntimeError("无法初始化AI提供者")
    
    def analyze_call_tree_report(self, report_path: str) -> str:
        """分析调用树报告
        
        Args:
            report_path: 调用树报告文件路径
            
        Returns:
            str: AI分析结果
        """
        try:
            # 读取报告文件
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # 构建分析提示
            system_prompt = """你是一个专业的Java代码架构分析师。请分析提供的调用树报告，重点关注：
1. 代码架构和设计模式
2. 潜在的性能问题
3. 安全风险
4. 代码质量和可维护性
5. 改进建议

请提供结构化的分析结果。"""
            
            user_message = f"""请分析以下Java代码调用树报告：

{report_content}

请提供详细的分析和改进建议。"""
            
            # 发送给AI分析
            response = self.ai_manager.chat(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,  # 较低的温度以获得更准确的分析
                use_history=False
            )
            
            if response:
                return response.content
            else:
                return "AI分析失败"
                
        except Exception as e:
            logger.error(f"分析调用树报告失败: {e}")
            return f"分析失败: {e}"
    
    def analyze_jar_resolutions(self, jar_file_path: str) -> str:
        """分析JAR推理结果
        
        Args:
            jar_file_path: JAR推理结果JSON文件路径
            
        Returns:
            str: AI分析结果
        """
        try:
            # 读取JAR推理结果
            with open(jar_file_path, 'r', encoding='utf-8') as f:
                jar_data = json.load(f)
            
            if not jar_data:
                return "没有JAR推理结果可分析"
            
            # 格式化JAR推理数据
            formatted_data = self._format_jar_data(jar_data)
            
            # 构建分析提示
            system_prompt = """你是一个Java框架和依赖分析专家。请分析JAR方法推理结果，重点关注：
1. 框架使用情况和版本兼容性
2. 依赖关系的合理性
3. 潜在的框架冲突
4. 升级和迁移建议
5. 最佳实践建议"""
            
            user_message = f"""请分析以下JAR方法推理结果：

{formatted_data}

请提供框架使用分析和优化建议。"""
            
            # 发送给AI分析
            response = self.ai_manager.chat(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                use_history=False
            )
            
            if response:
                return response.content
            else:
                return "AI分析失败"
                
        except Exception as e:
            logger.error(f"分析JAR推理结果失败: {e}")
            return f"分析失败: {e}"
    
    def _format_jar_data(self, jar_data: list) -> str:
        """格式化JAR推理数据"""
        if not jar_data:
            return "无JAR推理数据"
        
        lines = ["## JAR方法推理结果分析"]
        
        # 按框架分组
        framework_groups = {}
        for item in jar_data:
            framework = item.get('framework', 'Unknown')
            if framework not in framework_groups:
                framework_groups[framework] = []
            framework_groups[framework].append(item)
        
        # 统计信息
        lines.append(f"\n### 统计信息")
        lines.append(f"- 总推理方法数: {len(jar_data)}")
        lines.append(f"- 涉及框架数: {len(framework_groups)}")
        
        # 按框架详细列出
        for framework, items in framework_groups.items():
            lines.append(f"\n### {framework} 框架 ({len(items)} 个方法)")
            
            for item in items[:5]:  # 限制显示数量
                original = item.get('original_call', '')
                resolved = item.get('resolved_method', '')
                description = item.get('description', '')
                
                lines.append(f"- **{original}**")
                lines.append(f"  - 推理结果: {resolved}")
                lines.append(f"  - 描述: {description}")
            
            if len(items) > 5:
                lines.append(f"  - ... 还有 {len(items) - 5} 个方法")
        
        return "\n".join(lines)
    
    def analyze_code_extraction(self, code_file_path: str) -> str:
        """分析代码提取结果
        
        Args:
            code_file_path: 代码提取文件路径
            
        Returns:
            str: AI分析结果
        """
        try:
            # 读取代码文件
            with open(code_file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 构建分析提示
            system_prompt = """你是一个Java代码重构专家。请分析提供的Java代码，重点关注：
1. 代码结构和组织
2. 设计模式的使用
3. 代码复杂度和可读性
4. 潜在的bug和安全问题
5. 重构和优化建议

请提供具体的改进方案。"""
            
            user_message = f"""请分析以下Java代码提取结果：

{code_content}

请提供详细的代码质量分析和重构建议。"""
            
            # 发送给AI分析
            response = self.ai_manager.chat(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.2,  # 更低的温度以获得更准确的代码分析
                use_history=False
            )
            
            if response:
                return response.content
            else:
                return "AI分析失败"
                
        except Exception as e:
            logger.error(f"分析代码提取结果失败: {e}")
            return f"分析失败: {e}"
    
    def generate_migration_suggestions(self, output_dir: str = "migration_output") -> str:
        """生成迁移建议
        
        Args:
            output_dir: 输出目录
            
        Returns:
            str: 迁移建议
        """
        try:
            output_path = Path(output_dir)
            if not output_path.exists():
                return "输出目录不存在"
            
            # 收集所有分析文件
            analysis_files = {
                'call_trees': list(output_path.glob("deep_call_tree_*.md")),
                'jar_resolutions': list(output_path.glob("jar_resolved_methods.json")),
                'code_extractions': list(output_path.glob("java_code_*.md"))
            }
            
            # 构建综合分析
            analysis_summary = []
            
            # 分析调用树
            if analysis_files['call_trees']:
                analysis_summary.append("## 调用树分析结果")
                for file_path in analysis_files['call_trees'][:3]:  # 限制分析数量
                    file_analysis = self.analyze_call_tree_report(str(file_path))
                    analysis_summary.append(f"### {file_path.name}")
                    analysis_summary.append(file_analysis[:1000] + "..." if len(file_analysis) > 1000 else file_analysis)
            
            # 分析JAR推理
            if analysis_files['jar_resolutions']:
                analysis_summary.append("\n## JAR推理分析结果")
                jar_analysis = self.analyze_jar_resolutions(str(analysis_files['jar_resolutions'][0]))
                analysis_summary.append(jar_analysis[:1000] + "..." if len(jar_analysis) > 1000 else jar_analysis)
            
            # 生成综合建议
            summary_content = "\n".join(analysis_summary)
            
            system_prompt = """你是一个资深的系统架构师和技术迁移专家。基于提供的代码分析结果，请生成：
1. 系统架构评估
2. 技术栈迁移建议
3. 风险评估和缓解策略
4. 迁移路线图
5. 最佳实践建议

请提供可执行的迁移方案。"""
            
            user_message = f"""基于以下代码分析结果，请生成系统迁移建议：

{summary_content}

请提供详细的迁移策略和实施计划。"""
            
            # 发送给AI生成建议
            response = self.ai_manager.chat(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.4,
                use_history=False
            )
            
            if response:
                return response.content
            else:
                return "生成迁移建议失败"
                
        except Exception as e:
            logger.error(f"生成迁移建议失败: {e}")
            return f"生成建议失败: {e}"


def main():
    """主函数 - 演示AI代码分析功能"""
    print("🤖 AI代码分析器演示")
    print("=" * 60)
    
    try:
        # 创建AI代码分析器
        analyzer = AICodeAnalyzer()
        
        # 检查输出目录
        output_dir = Path("migration_output")
        if not output_dir.exists():
            print("❌ migration_output目录不存在，请先运行代码分析")
            return
        
        # 查找分析文件
        call_tree_files = list(output_dir.glob("deep_call_tree_*.md"))
        jar_files = list(output_dir.glob("jar_resolved_methods.json"))
        code_files = list(output_dir.glob("java_code_*.md"))
        
        print(f"📁 找到分析文件:")
        print(f"  - 调用树报告: {len(call_tree_files)} 个")
        print(f"  - JAR推理结果: {len(jar_files)} 个")
        print(f"  - 代码提取文件: {len(code_files)} 个")
        
        if not any([call_tree_files, jar_files, code_files]):
            print("❌ 没有找到可分析的文件")
            return
        
        # 分析调用树报告
        if call_tree_files:
            print(f"\n🌳 分析调用树报告: {call_tree_files[0].name}")
            call_tree_analysis = analyzer.analyze_call_tree_report(str(call_tree_files[0]))
            print("📊 调用树分析结果:")
            print(call_tree_analysis[:500] + "..." if len(call_tree_analysis) > 500 else call_tree_analysis)
        
        # 分析JAR推理结果
        if jar_files:
            print(f"\n🔍 分析JAR推理结果: {jar_files[0].name}")
            jar_analysis = analyzer.analyze_jar_resolutions(str(jar_files[0]))
            print("📋 JAR推理分析结果:")
            print(jar_analysis[:500] + "..." if len(jar_analysis) > 500 else jar_analysis)
        
        # 生成综合迁移建议
        print(f"\n🚀 生成综合迁移建议...")
        migration_suggestions = analyzer.generate_migration_suggestions()
        print("📝 迁移建议:")
        print(migration_suggestions[:800] + "..." if len(migration_suggestions) > 800 else migration_suggestions)
        
        # 保存分析结果
        results_file = output_dir / "ai_analysis_results.md"
        with open(results_file, 'w', encoding='utf-8') as f:
            f.write("# AI代码分析结果\n\n")
            
            if call_tree_files:
                f.write("## 调用树分析\n\n")
                f.write(call_tree_analysis)
                f.write("\n\n")
            
            if jar_files:
                f.write("## JAR推理分析\n\n")
                f.write(jar_analysis)
                f.write("\n\n")
            
            f.write("## 迁移建议\n\n")
            f.write(migration_suggestions)
        
        print(f"\n💾 分析结果已保存到: {results_file}")
        
    except Exception as e:
        logger.error(f"AI代码分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()