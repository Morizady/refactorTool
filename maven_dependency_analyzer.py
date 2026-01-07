#!/usr/bin/env python3
"""
Maven依赖解析器
解析pom.xml文件，从本地Maven仓库中找到JAR包并进行分析
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from jar_analyzer import JarAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MavenDependency:
    """Maven依赖信息"""
    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    type: str = "jar"
    classifier: str = ""
    exclusions: List[Dict] = None
    
    def __post_init__(self):
        if self.exclusions is None:
            self.exclusions = []
    
    @property
    def coordinate(self) -> str:
        """获取Maven坐标"""
        return f"{self.group_id}:{self.artifact_id}:{self.version}"
    
    @property
    def path_in_repo(self) -> str:
        """获取在Maven仓库中的路径"""
        group_path = self.group_id.replace('.', '/')
        filename = f"{self.artifact_id}-{self.version}"
        if self.classifier:
            filename += f"-{self.classifier}"
        filename += f".{self.type}"
        
        return f"{group_path}/{self.artifact_id}/{self.version}/{filename}"

class MavenDependencyAnalyzer:
    """Maven依赖分析器"""
    
    def __init__(self, maven_repo_path: str = None):
        """初始化Maven依赖分析器"""
        self.maven_repo_path = Path(maven_repo_path) if maven_repo_path else self._find_maven_repo()
        self.jar_analyzer = JarAnalyzer()
        self.dependencies = []
        self.resolved_jars = {}
        self.missing_jars = []
        
        logger.info(f"Maven仓库路径: {self.maven_repo_path}")
    
    def _find_maven_repo(self) -> Path:
        """查找Maven仓库路径"""
        # 常见的Maven仓库位置
        possible_paths = [
            Path("apache-maven-repository"),  # 用户指定的路径
            Path.home() / ".m2" / "repository",  # 默认位置
            Path("D:/apache-maven-repository"),  # Windows常见位置
            Path("C:/Users") / os.getenv("USERNAME", "") / ".m2" / "repository"
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"找到Maven仓库: {path}")
                return path
        
        # 如果都找不到，使用用户指定的路径
        default_path = Path("apache-maven-repository")
        logger.warning(f"未找到标准Maven仓库，使用: {default_path}")
        return default_path
    
    def parse_pom(self, pom_path: str) -> List[MavenDependency]:
        """解析pom.xml文件"""
        logger.info(f"🔍 解析POM文件: {pom_path}")
        
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            # 处理XML命名空间
            namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            if root.tag.startswith('{'):
                namespace_uri = root.tag.split('}')[0][1:]
                namespace = {'maven': namespace_uri}
            
            dependencies = []
            
            # 查找dependencies节点
            deps_node = root.find('.//maven:dependencies', namespace)
            if deps_node is None:
                # 尝试不使用命名空间
                deps_node = root.find('.//dependencies')
            
            if deps_node is not None:
                for dep_node in deps_node.findall('.//maven:dependency', namespace):
                    if dep_node is None:
                        dep_node = deps_node.findall('.//dependency')
                    
                    dependency = self._parse_dependency_node(dep_node, namespace)
                    if dependency:
                        dependencies.append(dependency)
            
            logger.info(f"✅ 解析完成，找到 {len(dependencies)} 个依赖")
            self.dependencies = dependencies
            return dependencies
            
        except Exception as e:
            logger.error(f"解析POM文件失败: {e}")
            return []
    
    def _parse_dependency_node(self, dep_node, namespace: Dict) -> Optional[MavenDependency]:
        """解析单个dependency节点"""
        try:
            def get_text(node, tag):
                """获取节点文本，支持命名空间"""
                element = node.find(f'maven:{tag}', namespace)
                if element is None:
                    element = node.find(tag)
                return element.text if element is not None else None
            
            group_id = get_text(dep_node, 'groupId')
            artifact_id = get_text(dep_node, 'artifactId')
            version = get_text(dep_node, 'version')
            
            if not all([group_id, artifact_id]):
                return None
            
            scope = get_text(dep_node, 'scope') or 'compile'
            type_val = get_text(dep_node, 'type') or 'jar'
            classifier = get_text(dep_node, 'classifier') or ''
            
            # 解析exclusions
            exclusions = []
            exclusions_node = dep_node.find('maven:exclusions', namespace)
            if exclusions_node is None:
                exclusions_node = dep_node.find('exclusions')
            
            if exclusions_node is not None:
                for excl_node in exclusions_node.findall('.//maven:exclusion', namespace):
                    if excl_node is None:
                        excl_node = exclusions_node.findall('.//exclusion')
                    
                    excl_group = get_text(excl_node, 'groupId')
                    excl_artifact = get_text(excl_node, 'artifactId')
                    if excl_group and excl_artifact:
                        exclusions.append({
                            'groupId': excl_group,
                            'artifactId': excl_artifact
                        })
            
            return MavenDependency(
                group_id=group_id,
                artifact_id=artifact_id,
                version=version or "UNKNOWN",
                scope=scope,
                type=type_val,
                classifier=classifier,
                exclusions=exclusions
            )
            
        except Exception as e:
            logger.warning(f"解析依赖节点失败: {e}")
            return None
    
    def resolve_dependencies(self) -> Dict:
        """解析依赖，查找对应的JAR包"""
        logger.info(f"🔍 解析 {len(self.dependencies)} 个依赖...")
        
        resolved_count = 0
        missing_count = 0
        
        for dependency in self.dependencies:
            jar_path = self._find_jar_in_repo(dependency)
            
            if jar_path and jar_path.exists():
                self.resolved_jars[dependency.coordinate] = {
                    'dependency': dependency,
                    'jar_path': jar_path,
                    'size_mb': jar_path.stat().st_size / (1024 * 1024)
                }
                resolved_count += 1
                logger.debug(f"✅ 找到: {dependency.coordinate}")
            else:
                self.missing_jars.append(dependency)
                missing_count += 1
                logger.debug(f"❌ 缺失: {dependency.coordinate}")
        
        logger.info(f"📊 解析结果: {resolved_count} 个找到, {missing_count} 个缺失")
        
        return {
            'resolved': self.resolved_jars,
            'missing': self.missing_jars,
            'total': len(self.dependencies)
        }
    
    def _find_jar_in_repo(self, dependency: MavenDependency) -> Optional[Path]:
        """在Maven仓库中查找JAR包"""
        jar_path = self.maven_repo_path / dependency.path_in_repo
        
        if jar_path.exists():
            return jar_path
        
        # 如果找不到，尝试不同的文件名格式
        group_path = self.maven_repo_path / dependency.group_id.replace('.', '/') / dependency.artifact_id / dependency.version
        
        if group_path.exists():
            # 查找所有可能的JAR文件
            possible_jars = list(group_path.glob(f"{dependency.artifact_id}-{dependency.version}*.jar"))
            if possible_jars:
                return possible_jars[0]  # 返回第一个找到的
        
        return None
    
    def analyze_resolved_jars(self) -> Dict:
        """分析已解析的JAR包"""
        logger.info(f"🔍 分析 {len(self.resolved_jars)} 个JAR包...")
        
        analysis_results = []
        total_size = 0
        
        for coordinate, jar_info in self.resolved_jars.items():
            jar_path = jar_info['jar_path']
            dependency = jar_info['dependency']
            
            logger.info(f"分析: {coordinate}")
            
            # 使用JAR分析器分析
            jar_analysis = self.jar_analyzer.analyze_jar(str(jar_path))
            
            if jar_analysis:
                # 添加Maven依赖信息
                jar_analysis['maven_info'] = {
                    'coordinate': coordinate,
                    'group_id': dependency.group_id,
                    'artifact_id': dependency.artifact_id,
                    'version': dependency.version,
                    'scope': dependency.scope,
                    'type': dependency.type,
                    'exclusions': dependency.exclusions
                }
                
                analysis_results.append(jar_analysis)
                total_size += jar_analysis.get('size_mb', 0)
        
        return {
            'jars': analysis_results,
            'total_count': len(analysis_results),
            'total_size_mb': round(total_size, 2),
            'missing_dependencies': [dep.coordinate for dep in self.missing_jars]
        }
    
    def generate_dependency_report(self, output_path: str = "maven_dependency_report.md"):
        """生成Maven依赖分析报告"""
        logger.info(f"📝 生成依赖报告: {output_path}")
        
        # 解析依赖
        resolution_result = self.resolve_dependencies()
        
        # 分析JAR包
        analysis_result = self.analyze_resolved_jars()
        
        # 生成报告
        report_content = self._build_dependency_report(resolution_result, analysis_result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"✅ 报告生成完成: {output_path}")
        
        return analysis_result
    
    def _build_dependency_report(self, resolution_result: Dict, analysis_result: Dict) -> str:
        """构建依赖报告内容"""
        content = []
        
        content.append("# Maven依赖分析报告\n")
        content.append(f"**分析时间**: {self._get_current_time()}\n")
        content.append(f"**Maven仓库**: {self.maven_repo_path}\n")
        content.append(f"**总依赖数**: {resolution_result['total']}\n")
        content.append(f"**已解析**: {len(resolution_result['resolved'])}\n")
        content.append(f"**缺失**: {len(resolution_result['missing'])}\n")
        content.append(f"**总大小**: {analysis_result['total_size_mb']} MB\n\n")
        
        # 依赖解析统计
        content.append("## 依赖解析统计\n\n")
        content.append(f"- ✅ **已找到JAR包**: {len(resolution_result['resolved'])} 个\n")
        content.append(f"- ❌ **缺失JAR包**: {len(resolution_result['missing'])} 个\n")
        content.append(f"- 📦 **总大小**: {analysis_result['total_size_mb']} MB\n\n")
        
        # 按scope分类
        scope_stats = {}
        for jar_info in resolution_result['resolved'].values():
            scope = jar_info['dependency'].scope
            scope_stats[scope] = scope_stats.get(scope, 0) + 1
        
        content.append("### 按Scope分类\n\n")
        for scope, count in scope_stats.items():
            content.append(f"- **{scope}**: {count} 个\n")
        content.append("\n")
        
        # 缺失的依赖
        if resolution_result['missing']:
            content.append("## 缺失的依赖\n\n")
            content.append("以下依赖在本地Maven仓库中未找到:\n\n")
            for dep in resolution_result['missing']:
                content.append(f"- `{dep.coordinate}` (scope: {dep.scope})\n")
            content.append("\n")
        
        # 已解析的依赖详情
        content.append("## 已解析的依赖详情\n\n")
        
        for jar in analysis_result['jars']:
            maven_info = jar.get('maven_info', {})
            content.append(f"### {maven_info.get('artifact_id', 'Unknown')}\n\n")
            content.append(f"- **坐标**: `{maven_info.get('coordinate', 'Unknown')}`\n")
            content.append(f"- **大小**: {jar['size_mb']:.2f} MB\n")
            content.append(f"- **类数量**: {len(jar['classes'])}\n")
            content.append(f"- **包数量**: {len(jar['packages'])}\n")
            content.append(f"- **Scope**: {maven_info.get('scope', 'compile')}\n")
            
            # 显示主要包
            if jar['packages']:
                content.append(f"- **主要包**: {', '.join(jar['packages'][:5])}\n")
                if len(jar['packages']) > 5:
                    content.append(f"  ... 还有 {len(jar['packages']) - 5} 个包\n")
            
            # 排除项
            exclusions = maven_info.get('exclusions', [])
            if exclusions:
                content.append(f"- **排除项**: {len(exclusions)} 个\n")
                for excl in exclusions[:3]:
                    content.append(f"  - {excl.get('groupId', '')}:{excl.get('artifactId', '')}\n")
            
            content.append("\n")
        
        return "".join(content)
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_classpath_jars(self, scope: str = "compile") -> List[Path]:
        """获取指定scope的JAR包路径列表，用于配置JDT类路径"""
        classpath_jars = []
        
        for jar_info in self.resolved_jars.values():
            dependency = jar_info['dependency']
            if scope == "all" or dependency.scope == scope or dependency.scope == "compile":
                classpath_jars.append(jar_info['jar_path'])
        
        return classpath_jars


def test_maven_dependency_analyzer():
    """测试Maven依赖分析器"""
    print("🧪 测试Maven依赖分析器")
    print("=" * 50)
    
    # 初始化分析器
    maven_repo = "apache-maven-repository"  # 用户指定的Maven仓库路径
    analyzer = MavenDependencyAnalyzer(maven_repo)
    
    # 解析POM文件
    pom_path = "test_projects/sc_pcc_business/pom.xml"
    
    if not os.path.exists(pom_path):
        print(f"❌ POM文件不存在: {pom_path}")
        return
    
    # 解析依赖
    dependencies = analyzer.parse_pom(pom_path)
    
    print(f"\n📋 解析结果:")
    print(f"   总依赖数: {len(dependencies)}")
    
    # 显示前10个依赖
    print(f"\n📦 依赖列表 (前10个):")
    for i, dep in enumerate(dependencies[:10], 1):
        print(f"   {i}. {dep.coordinate} (scope: {dep.scope})")
    
    if len(dependencies) > 10:
        print(f"   ... 还有 {len(dependencies) - 10} 个依赖")
    
    # 生成完整报告
    print(f"\n📝 生成完整分析报告...")
    analysis_result = analyzer.generate_dependency_report("test_output/maven_dependency_report.md")
    
    print(f"\n📊 分析统计:")
    print(f"   已解析JAR包: {analysis_result['total_count']}")
    print(f"   缺失依赖: {len(analysis_result['missing_dependencies'])}")
    print(f"   总大小: {analysis_result['total_size_mb']} MB")
    
    # 获取类路径JAR包
    classpath_jars = analyzer.get_classpath_jars("compile")
    print(f"\n🛤️ 编译类路径JAR包: {len(classpath_jars)} 个")
    
    return analyzer


if __name__ == "__main__":
    analyzer = test_maven_dependency_analyzer()