#!/usr/bin/env python3
"""
JAR包分析工具
结合JDT和字节码分析技术
"""

import os
import zipfile
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JarAnalyzer:
    """JAR包分析器"""
    
    def __init__(self):
        self.jar_info = {}
        self.class_signatures = {}
        self.dependencies = {}
    
    def analyze_jar(self, jar_path: str) -> Dict:
        """分析JAR包"""
        jar_path = Path(jar_path)
        
        if not jar_path.exists():
            logger.error(f"JAR文件不存在: {jar_path}")
            return {}
        
        logger.info(f"🔍 分析JAR包: {jar_path.name}")
        
        analysis_result = {
            "jar_name": jar_path.name,
            "jar_path": str(jar_path),
            "size_mb": jar_path.stat().st_size / (1024 * 1024),
            "manifest": {},
            "classes": [],
            "packages": set(),
            "dependencies": []
        }
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar_file:
                # 分析MANIFEST.MF
                analysis_result["manifest"] = self._analyze_manifest(jar_file)
                
                # 分析类文件
                class_files = [f for f in jar_file.namelist() if f.endswith('.class')]
                analysis_result["classes"] = self._analyze_class_files(jar_file, class_files)
                
                # 提取包信息
                packages = set()
                for class_file in class_files:
                    package = '/'.join(class_file.split('/')[:-1]).replace('/', '.')
                    if package:
                        packages.add(package)
                
                analysis_result["packages"] = sorted(packages)
                
                logger.info(f"✅ 分析完成: {len(class_files)} 个类, {len(packages)} 个包")
                
        except Exception as e:
            logger.error(f"分析JAR包失败: {e}")
        
        return analysis_result
    
    def _analyze_manifest(self, jar_file: zipfile.ZipFile) -> Dict:
        """分析MANIFEST.MF文件"""
        manifest_info = {}
        
        try:
            if 'META-INF/MANIFEST.MF' in jar_file.namelist():
                manifest_content = jar_file.read('META-INF/MANIFEST.MF').decode('utf-8')
                
                for line in manifest_content.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        manifest_info[key.strip()] = value.strip()
                
                logger.info(f"📋 MANIFEST信息: {len(manifest_info)} 个属性")
                
        except Exception as e:
            logger.warning(f"读取MANIFEST失败: {e}")
        
        return manifest_info
    
    def _analyze_class_files(self, jar_file: zipfile.ZipFile, class_files: List[str]) -> List[Dict]:
        """分析类文件（基础信息）"""
        classes = []
        
        for class_file in class_files[:50]:  # 限制分析数量
            try:
                class_name = class_file.replace('/', '.').replace('.class', '')
                
                # 基础类信息
                class_info = {
                    "name": class_name,
                    "file_path": class_file,
                    "package": '.'.join(class_name.split('.')[:-1]),
                    "simple_name": class_name.split('.')[-1]
                }
                
                classes.append(class_info)
                
            except Exception as e:
                logger.warning(f"分析类文件失败 {class_file}: {e}")
        
        return classes
    
    def find_jars_in_project(self, project_path: str) -> List[Path]:
        """在项目中查找JAR包"""
        project_path = Path(project_path)
        jar_files = []
        
        # 常见的JAR包位置
        search_paths = [
            project_path / "lib",
            project_path / "libs", 
            project_path / "target" / "lib",
            project_path / "target" / "dependency",
            project_path / "build" / "libs",
            project_path / "WEB-INF" / "lib",
            project_path / "src" / "main" / "webapp" / "WEB-INF" / "lib"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                jars = list(search_path.glob("*.jar"))
                jar_files.extend(jars)
                if jars:
                    logger.info(f"📁 在 {search_path} 找到 {len(jars)} 个JAR包")
        
        return jar_files
    
    def analyze_project_dependencies(self, project_path: str) -> Dict:
        """分析项目的JAR包依赖"""
        logger.info(f"🔍 分析项目依赖: {project_path}")
        
        jar_files = self.find_jars_in_project(project_path)
        
        if not jar_files:
            logger.warning("未找到JAR包")
            return {"jars": [], "total_count": 0, "total_size_mb": 0}
        
        analysis_results = []
        total_size = 0
        
        for jar_file in jar_files:
            jar_analysis = self.analyze_jar(str(jar_file))
            if jar_analysis:
                analysis_results.append(jar_analysis)
                total_size += jar_analysis.get("size_mb", 0)
        
        return {
            "jars": analysis_results,
            "total_count": len(analysis_results),
            "total_size_mb": round(total_size, 2),
            "packages": self._collect_all_packages(analysis_results),
            "summary": self._generate_dependency_summary(analysis_results)
        }
    
    def _collect_all_packages(self, jar_analyses: List[Dict]) -> List[str]:
        """收集所有包名"""
        all_packages = set()
        
        for jar_analysis in jar_analyses:
            packages = jar_analysis.get("packages", [])
            all_packages.update(packages)
        
        return sorted(all_packages)
    
    def _generate_dependency_summary(self, jar_analyses: List[Dict]) -> Dict:
        """生成依赖摘要"""
        summary = {
            "framework_jars": [],
            "utility_jars": [],
            "business_jars": [],
            "unknown_jars": []
        }
        
        for jar_analysis in jar_analyses:
            jar_name = jar_analysis["jar_name"].lower()
            
            # 分类JAR包
            if any(fw in jar_name for fw in ['spring', 'hibernate', 'mybatis', 'struts']):
                summary["framework_jars"].append(jar_analysis["jar_name"])
            elif any(util in jar_name for util in ['commons', 'guava', 'jackson', 'gson']):
                summary["utility_jars"].append(jar_analysis["jar_name"])
            elif any(biz in jar_name for biz in ['unicom', 'holly', 'pcc']):
                summary["business_jars"].append(jar_analysis["jar_name"])
            else:
                summary["unknown_jars"].append(jar_analysis["jar_name"])
        
        return summary
    
    def generate_report(self, analysis_result: Dict, output_path: str = "jar_analysis_report.md"):
        """生成分析报告"""
        logger.info(f"📝 生成报告: {output_path}")
        
        report_content = self._build_report_content(analysis_result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"✅ 报告生成完成: {output_path}")
    
    def _build_report_content(self, analysis_result: Dict) -> str:
        """构建报告内容"""
        content = []
        
        content.append("# JAR包依赖分析报告\n")
        content.append(f"**分析时间**: {self._get_current_time()}\n")
        content.append(f"**JAR包总数**: {analysis_result['total_count']}\n")
        content.append(f"**总大小**: {analysis_result['total_size_mb']} MB\n\n")
        
        # 依赖摘要
        summary = analysis_result.get("summary", {})
        content.append("## 依赖分类\n\n")
        
        for category, jars in summary.items():
            category_name = {
                "framework_jars": "框架JAR包",
                "utility_jars": "工具JAR包", 
                "business_jars": "业务JAR包",
                "unknown_jars": "其他JAR包"
            }.get(category, category)
            
            content.append(f"### {category_name} ({len(jars)}个)\n\n")
            for jar in jars:
                content.append(f"- {jar}\n")
            content.append("\n")
        
        # 详细信息
        content.append("## JAR包详细信息\n\n")
        
        for jar in analysis_result["jars"]:
            content.append(f"### {jar['jar_name']}\n\n")
            content.append(f"- **大小**: {jar['size_mb']:.2f} MB\n")
            content.append(f"- **类数量**: {len(jar['classes'])}\n")
            content.append(f"- **包数量**: {len(jar['packages'])}\n")
            
            # MANIFEST信息
            manifest = jar.get("manifest", {})
            if manifest:
                content.append(f"- **版本**: {manifest.get('Implementation-Version', 'N/A')}\n")
                content.append(f"- **供应商**: {manifest.get('Implementation-Vendor', 'N/A')}\n")
            
            content.append("\n")
        
        return "".join(content)
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def test_jar_analyzer():
    """测试JAR包分析器"""
    print("🧪 测试JAR包分析器")
    print("=" * 40)
    
    analyzer = JarAnalyzer()
    
    # 分析项目依赖
    project_path = "test_projects/sc_pcc_business"
    
    if os.path.exists(project_path):
        analysis_result = analyzer.analyze_project_dependencies(project_path)
        
        print(f"\n📊 分析结果:")
        print(f"   JAR包总数: {analysis_result['total_count']}")
        print(f"   总大小: {analysis_result['total_size_mb']} MB")
        
        if analysis_result['jars']:
            print(f"\n📋 JAR包列表:")
            for jar in analysis_result['jars'][:10]:  # 显示前10个
                print(f"   - {jar['jar_name']} ({jar['size_mb']:.1f}MB)")
        
        # 生成报告
        analyzer.generate_report(analysis_result, "test_output/jar_analysis_report.md")
        
    # 无论项目路径是否存在，都测试分析JDT JAR包
    jdt_jar = "lib/jdt/org.eclipse.jdt.core.jar"
    if os.path.exists(jdt_jar):
        print(f"\n🔍 分析JDT JAR包: {jdt_jar}")
        jar_analysis = analyzer.analyze_jar(jdt_jar)
        
        if jar_analysis:
            print(f"   大小: {jar_analysis['size_mb']:.1f} MB")
            print(f"   类数量: {len(jar_analysis['classes'])}")
            print(f"   包数量: {len(jar_analysis['packages'])}")
            
            # 显示一些包名
            if jar_analysis['packages']:
                print(f"   主要包:")
                for pkg in jar_analysis['packages'][:10]:
                    print(f"     - {pkg}")
            
            # 显示MANIFEST信息
            manifest = jar_analysis.get('manifest', {})
            if manifest:
                print(f"   MANIFEST信息:")
                for key, value in list(manifest.items())[:5]:
                    print(f"     - {key}: {value}")
    else:
        print(f"❌ JDT JAR包不存在: {jdt_jar}")
        
    if not os.path.exists(project_path):
        print(f"❌ 项目路径不存在: {project_path}")


if __name__ == "__main__":
    test_jar_analyzer()