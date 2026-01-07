#!/usr/bin/env python3
"""
增强版JDT分析器
结合Maven依赖解析，提供完整的类路径支持
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from jdt_parser import JDTParser
from maven_dependency_analyzer import MavenDependencyAnalyzer
from jdt_call_chain_analyzer import JDTDeepCallChainAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedJDTAnalyzer:
    """增强版JDT分析器，支持Maven依赖解析"""
    
    def __init__(self, project_path: str, maven_repo_path: str = None):
        """初始化增强版JDT分析器"""
        self.project_path = Path(project_path)
        self.maven_analyzer = MavenDependencyAnalyzer(maven_repo_path)
        self.jdt_parser = None
        self.call_chain_analyzer = None
        
        # Maven依赖信息
        self.dependencies = []
        self.classpath_jars = []
        self.dependency_classes = {}
        
        logger.info(f"🚀 初始化增强版JDT分析器: {project_path}")
    
    def initialize_with_maven_dependencies(self) -> bool:
        """使用Maven依赖初始化JDT环境"""
        logger.info("📦 解析Maven依赖...")
        
        # 查找pom.xml文件
        pom_path = self.project_path / "pom.xml"
        if not pom_path.exists():
            logger.error(f"未找到pom.xml文件: {pom_path}")
            return False
        
        # 解析Maven依赖
        self.dependencies = self.maven_analyzer.parse_pom(str(pom_path))
        if not self.dependencies:
            logger.error("未解析到任何Maven依赖")
            return False
        
        # 解析依赖JAR包
        resolution_result = self.maven_analyzer.resolve_dependencies()
        logger.info(f"✅ Maven依赖解析完成: {len(resolution_result['resolved'])} 个JAR包")
        
        # 获取类路径JAR包
        self.classpath_jars = self.maven_analyzer.get_classpath_jars("all")  # 包含所有scope
        logger.info(f"🛤️ 类路径JAR包: {len(self.classpath_jars)} 个")
        
        # 初始化JDT解析器
        return self._initialize_jdt_with_classpath()
    
    def _initialize_jdt_with_classpath(self) -> bool:
        """使用类路径初始化JDT解析器"""
        logger.info("🔧 初始化JDT解析器...")
        
        # 创建自定义配置
        config = {
            'java': {
                'java_home': 'D:/Program Files/Java/jdk-1.8',
                'jvm_args': ['-Xmx4g', '-Xms1g', '-Dfile.encoding=UTF-8'],
                'jdt_lib_dir': './lib/jdt',
                'auto_download_jdt': True,
                'external_classpath': [str(jar) for jar in self.classpath_jars]  # 添加外部类路径
            },
            'parsing': {
                'method': 'jdt',
                'source_encoding': 'UTF-8',
                'java_version': '11',
                'include_tests': False,
                'resolve_bindings': True,  # 启用绑定解析
                'include_classpath': True   # 包含类路径
            }
        }
        
        # 创建JDT解析器
        self.jdt_parser = JDTParser()
        
        # 修改JDT解析器的类路径配置
        if hasattr(self.jdt_parser, '_initialize_jpype'):
            # 保存原始方法
            original_init_jpype = self.jdt_parser._initialize_jpype
            
            def enhanced_init_jpype():
                """增强版JPype初始化，包含Maven依赖"""
                try:
                    import jpype
                    self.jdt_parser.jpype = jpype
                    
                    if jpype.isJVMStarted():
                        logger.info("JVM已启动")
                        return True
                    
                    # 构建完整的类路径
                    jdt_lib_dir = Path(self.jdt_parser.config['java']['jdt_lib_dir'])
                    classpath = []
                    
                    # 添加JDT JAR文件
                    for jar_file in jdt_lib_dir.glob("*.jar"):
                        classpath.append(str(jar_file))
                    
                    # 添加Maven依赖JAR文件
                    for jar_path in self.classpath_jars:
                        if jar_path.exists():
                            classpath.append(str(jar_path))
                    
                    logger.info(f"📚 完整类路径包含 {len(classpath)} 个JAR包")
                    
                    # 启动JVM
                    logger.info("启动JVM...")
                    jpype.startJVM(
                        jpype.getDefaultJVMPath(),
                        "-Xmx4g",
                        "-Xms1g",
                        "-Dfile.encoding=UTF-8",
                        classpath=classpath
                    )
                    logger.info("JVM启动成功")
                    return True
                    
                except Exception as e:
                    logger.error(f"增强版JPype初始化失败: {e}")
                    return False
            
            # 替换初始化方法
            self.jdt_parser._initialize_jpype = enhanced_init_jpype
        
        # 初始化JDT环境
        success = self.jdt_parser.initialize_jdt()
        if success:
            logger.info("✅ 增强版JDT环境初始化成功")
        else:
            logger.error("❌ 增强版JDT环境初始化失败")
        
        return success
    
    def analyze_project_with_dependencies(self) -> Dict:
        """分析项目，包含依赖解析"""
        logger.info("🔍 开始项目分析...")
        
        if not self.jdt_parser:
            logger.error("JDT解析器未初始化")
            return {}
        
        # 解析项目源代码
        java_classes = self.jdt_parser.parse_project(str(self.project_path))
        
        # 创建深度调用链分析器
        self.call_chain_analyzer = JDTDeepCallChainAnalyzer(str(self.project_path))
        
        # 使用已初始化的JDT解析器
        self.call_chain_analyzer.jdt_parser = self.jdt_parser
        self.call_chain_analyzer.java_classes = java_classes
        
        # 构建关系映射
        self.call_chain_analyzer._build_class_relationships()
        self.call_chain_analyzer._build_package_imports()
        
        logger.info(f"✅ 项目分析完成: {len(java_classes)} 个类")
        
        return {
            'java_classes': java_classes,
            'maven_dependencies': len(self.dependencies),
            'classpath_jars': len(self.classpath_jars),
            'total_classes': len(java_classes)
        }
    
    def analyze_method_with_dependencies(self, file_path: str, method_name: str, max_depth: int = 4) -> Dict:
        """分析方法调用，包含依赖解析"""
        logger.info(f"🌳 分析方法调用: {method_name}")
        
        if not self.call_chain_analyzer:
            logger.error("调用链分析器未初始化")
            return {}
        
        # 执行深度调用树分析
        call_tree = self.call_chain_analyzer.analyze_deep_call_tree(
            file_path, method_name, max_depth
        )
        
        if call_tree:
            logger.info(f"✅ 方法调用分析完成: {len(call_tree.children)} 个子调用")
            
            return {
                'call_tree': call_tree,
                'method_mappings': len(self.call_chain_analyzer.method_mappings),
                'max_depth_reached': call_tree.depth,
                'total_calls': len(call_tree.children)
            }
        else:
            logger.error("方法调用分析失败")
            return {}
    
    def generate_enhanced_report(self, output_dir: str = "test_output") -> Dict:
        """生成增强版分析报告"""
        logger.info("📝 生成增强版分析报告...")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # 生成Maven依赖报告
        maven_report_path = output_dir / "enhanced_maven_dependency_report.md"
        maven_analysis = self.maven_analyzer.generate_dependency_report(str(maven_report_path))
        
        # 生成项目分析报告
        project_analysis = self.analyze_project_with_dependencies()
        
        # 生成综合报告
        comprehensive_report_path = output_dir / "enhanced_comprehensive_report.md"
        self._generate_comprehensive_report(
            str(comprehensive_report_path), 
            maven_analysis, 
            project_analysis
        )
        
        logger.info("✅ 增强版分析报告生成完成")
        
        return {
            'maven_report': str(maven_report_path),
            'comprehensive_report': str(comprehensive_report_path),
            'maven_analysis': maven_analysis,
            'project_analysis': project_analysis
        }
    
    def _generate_comprehensive_report(self, output_path: str, maven_analysis: Dict, project_analysis: Dict):
        """生成综合报告"""
        content = []
        
        content.append("# 增强版Java项目分析报告\n")
        content.append(f"**分析时间**: {self._get_current_time()}\n")
        content.append(f"**项目路径**: {self.project_path}\n")
        content.append(f"**Maven仓库**: {self.maven_analyzer.maven_repo_path}\n\n")
        
        # 总体统计
        content.append("## 总体统计\n\n")
        content.append(f"- **源代码类数**: {project_analysis.get('total_classes', 0)}\n")
        content.append(f"- **Maven依赖数**: {project_analysis.get('maven_dependencies', 0)}\n")
        content.append(f"- **类路径JAR包**: {project_analysis.get('classpath_jars', 0)}\n")
        content.append(f"- **依赖总大小**: {maven_analysis.get('total_size_mb', 0)} MB\n\n")
        
        # 依赖分析摘要
        content.append("## 依赖分析摘要\n\n")
        content.append(f"- ✅ **已解析依赖**: {maven_analysis.get('total_count', 0)} 个\n")
        content.append(f"- ❌ **缺失依赖**: {len(maven_analysis.get('missing_dependencies', []))} 个\n")
        
        if maven_analysis.get('missing_dependencies'):
            content.append(f"\n### 缺失的依赖\n\n")
            for dep in maven_analysis['missing_dependencies'][:10]:
                content.append(f"- `{dep}`\n")
        
        # 类路径配置
        content.append(f"\n## 类路径配置\n\n")
        content.append(f"JDT解析器已配置包含 {len(self.classpath_jars)} 个外部JAR包的类路径，\n")
        content.append(f"这使得源代码分析能够正确解析对外部依赖的引用。\n\n")
        
        # 分析能力
        content.append("## 分析能力\n\n")
        content.append("### ✅ 支持的分析\n\n")
        content.append("- 源代码的完整AST分析\n")
        content.append("- 对外部依赖的类型解析\n")
        content.append("- 深度方法调用链分析\n")
        content.append("- Maven依赖关系分析\n")
        content.append("- 类继承和接口实现分析\n\n")
        
        content.append("### ⚠️ 限制\n\n")
        content.append("- 无法分析外部JAR包内部的方法实现\n")
        content.append("- 依赖于本地Maven仓库的完整性\n")
        content.append("- 需要正确的Java环境配置\n\n")
        
        # 使用建议
        content.append("## 使用建议\n\n")
        content.append("1. **代码重构**: 使用深度调用链分析识别影响范围\n")
        content.append("2. **依赖管理**: 基于Maven分析结果优化依赖结构\n")
        content.append("3. **架构分析**: 结合源代码和依赖信息进行架构评估\n")
        content.append("4. **迁移规划**: 基于调用关系制定迁移策略\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("".join(content))
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def shutdown(self):
        """关闭分析器"""
        if self.jdt_parser:
            self.jdt_parser.shutdown()
        logger.info("增强版JDT分析器已关闭")


def test_enhanced_jdt_analyzer():
    """测试增强版JDT分析器"""
    print("🧪 测试增强版JDT分析器")
    print("=" * 50)
    
    # 初始化分析器
    project_path = "test_projects/sc_pcc_business"
    maven_repo = "apache-maven-repository"
    
    analyzer = EnhancedJDTAnalyzer(project_path, maven_repo)
    
    try:
        # 使用Maven依赖初始化
        success = analyzer.initialize_with_maven_dependencies()
        
        if not success:
            print("❌ 初始化失败")
            return
        
        print("✅ 增强版JDT分析器初始化成功")
        
        # 生成增强版报告
        report_result = analyzer.generate_enhanced_report()
        
        print(f"\n📊 分析结果:")
        print(f"   源代码类数: {report_result['project_analysis'].get('total_classes', 0)}")
        print(f"   Maven依赖数: {report_result['project_analysis'].get('maven_dependencies', 0)}")
        print(f"   类路径JAR包: {report_result['project_analysis'].get('classpath_jars', 0)}")
        
        # 测试方法调用分析
        controller_file = f"{project_path}/src/main/java/com/unicom/microserv/cs/pcc/core/sheetmerge/controller/SheetMergeController.java"
        
        if os.path.exists(controller_file):
            print(f"\n🌳 测试方法调用分析...")
            method_analysis = analyzer.analyze_method_with_dependencies(
                controller_file, "merge", max_depth=4
            )
            
            if method_analysis:
                print(f"   方法调用数: {method_analysis.get('total_calls', 0)}")
                print(f"   方法映射数: {method_analysis.get('method_mappings', 0)}")
        
        print(f"\n📝 报告文件:")
        print(f"   Maven依赖报告: {report_result['maven_report']}")
        print(f"   综合分析报告: {report_result['comprehensive_report']}")
        
    finally:
        analyzer.shutdown()


if __name__ == "__main__":
    test_enhanced_jdt_analyzer()