#!/usr/bin/env python3
"""
修复版本的JDT解析器 - 解决ASTVisitor继承问题
使用更简单的方法直接遍历AST节点
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import urllib.request

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class JavaMethod:
    """Java方法信息"""
    name: str
    class_name: str
    file_path: str
    line_number: int
    parameters: List[str] = field(default_factory=list)
    return_type: str = ""
    modifiers: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    method_calls: List[Dict] = field(default_factory=list)
    is_constructor: bool = False

@dataclass
class JavaClass:
    """Java类信息"""
    name: str
    package: str
    file_path: str
    line_number: int
    modifiers: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    methods: List[JavaMethod] = field(default_factory=list)
    fields: List[Dict] = field(default_factory=list)
    is_interface: bool = False
    is_abstract: bool = False

class JDTParserFixed:
    """修复版本的JDT解析器"""
    
    def __init__(self, config_path: str = "config.yml"):
        """初始化JDT解析器"""
        self.config = self._load_config(config_path)
        self.jpype = None
        self.jdt_initialized = False
        self.java_classes = {}
        
        # JDT相关的Java类引用
        self.ASTParser = None
        self.AST = None
        self.CompilationUnit = None
        
        self._setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {config_path}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'java': {
                'java_home': os.environ.get('JAVA_HOME', ''),
                'jvm_args': ['-Xmx2g', '-Xms512m', '-Dfile.encoding=UTF-8'],
                'jdt_lib_dir': './lib/jdt',
                'auto_download_jdt': True
            },
            'parsing': {
                'method': 'jdt',
                'source_encoding': 'UTF-8',
                'java_version': '11',
                'include_tests': False
            },
            'analysis': {
                'max_call_depth': 6,
                'analyze_interfaces': True,
                'analyze_inheritance': True,
                'enable_cache': True,
                'cache_dir': './cache'
            },
            'logging': {
                'level': 'INFO',
                'console': True
            }
        }
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        logger.setLevel(level)
    
    def initialize_jdt(self) -> bool:
        """初始化JDT环境"""
        if self.jdt_initialized:
            return True
            
        try:
            # 检查JDT依赖
            if not self._check_jdt_dependencies():
                return False
            
            # 初始化JPype
            if not self._initialize_jpype():
                return False
            
            # 导入JDT类
            if not self._import_jdt_classes():
                return False
            
            self.jdt_initialized = True
            logger.info("JDT环境初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"JDT环境初始化失败: {e}")
            return False
    
    def _check_jdt_dependencies(self) -> bool:
        """检查JDT依赖"""
        jdt_lib_dir = Path(self.config['java']['jdt_lib_dir'])
        jdt_core_jar = jdt_lib_dir / "org.eclipse.jdt.core.jar"
        
        if jdt_core_jar.exists():
            logger.info("JDT依赖已存在")
            return True
        else:
            logger.error("JDT依赖不存在，请运行 python download_unified_eclipse_jdt.py")
            return False
    
    def _initialize_jpype(self) -> bool:
        """初始化JPype"""
        try:
            import jpype
            self.jpype = jpype
            
            if jpype.isJVMStarted():
                logger.info("JVM已启动")
                return True
            
            # 构建classpath
            jdt_lib_dir = Path(self.config['java']['jdt_lib_dir'])
            classpath = []
            
            for jar_file in jdt_lib_dir.glob("*.jar"):
                classpath.append(str(jar_file))
            
            if not classpath:
                logger.error("未找到JDT JAR文件")
                return False
            
            logger.info("启动JVM...")
            jpype.startJVM(
                jpype.getDefaultJVMPath(),
                "-Xmx2g",
                "-Xms512m",
                classpath=classpath
            )
            logger.info("JVM启动成功")
            return True
            
        except ImportError:
            logger.error("JPype未安装，请运行: pip install JPype1")
            return False
        except Exception as e:
            logger.error(f"JPype初始化失败: {e}")
            return False
    
    def _import_jdt_classes(self) -> bool:
        """导入JDT相关的Java类"""
        try:
            self.ASTParser = self.jpype.JClass("org.eclipse.jdt.core.dom.ASTParser")
            self.AST = self.jpype.JClass("org.eclipse.jdt.core.dom.AST")
            self.CompilationUnit = self.jpype.JClass("org.eclipse.jdt.core.dom.CompilationUnit")
            
            # 导入节点类型
            self.ASTNode = self.jpype.JClass("org.eclipse.jdt.core.dom.ASTNode")
            self.MethodDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.MethodDeclaration")
            self.TypeDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.TypeDeclaration")
            self.MethodInvocation = self.jpype.JClass("org.eclipse.jdt.core.dom.MethodInvocation")
            self.PackageDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.PackageDeclaration")
            self.ImportDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.ImportDeclaration")
            
            logger.info("JDT类导入成功")
            return True
            
        except Exception as e:
            logger.error(f"JDT类导入失败: {e}")
            return False
    
    def parse_java_file(self, file_path: str) -> Optional[JavaClass]:
        """解析单个Java文件"""
        if not self.initialize_jdt():
            logger.error("JDT环境未初始化")
            return None
        
        try:
            # 读取Java源代码
            with open(file_path, 'r', encoding=self.config['parsing']['source_encoding']) as f:
                source_code = f.read()
            
            # 创建AST解析器
            parser = self.ASTParser.newParser(self.AST.JLS8)
            parser.setSource(source_code)
            parser.setKind(self.ASTParser.K_COMPILATION_UNIT)
            
            # 解析AST
            compilation_unit = parser.createAST(None)
            
            # 直接遍历AST节点而不使用访问器
            java_class = self._extract_class_info(compilation_unit, file_path)
            
            return java_class
            
        except Exception as e:
            logger.error(f"解析Java文件失败 {file_path}: {e}")
            return None
    
    def _extract_class_info(self, compilation_unit, file_path: str) -> Optional[JavaClass]:
        """从编译单元中提取类信息"""
        try:
            java_class = None
            package_name = ""
            
            # 获取包名
            package_decl = compilation_unit.getPackage()
            if package_decl:
                package_name = str(package_decl.getName())
            
            # 获取类型声明
            types = compilation_unit.types()
            if types and types.size() > 0:
                # 获取第一个类型声明
                type_decl = types.get(0)
                
                if self._is_instance_of(type_decl, "TypeDeclaration"):
                    java_class = self._extract_type_declaration(type_decl, package_name, file_path)
            
            return java_class
            
        except Exception as e:
            logger.error(f"提取类信息失败: {e}")
            return None
    
    def _is_instance_of(self, obj, class_name: str) -> bool:
        """检查对象是否是指定类的实例"""
        try:
            return obj.getClass().getSimpleName() == class_name
        except:
            return False
    
    def _extract_type_declaration(self, type_decl, package_name: str, file_path: str) -> JavaClass:
        """提取类型声明信息"""
        class_name = str(type_decl.getName())
        
        # 获取修饰符
        modifiers = []
        try:
            modifier_flags = type_decl.getModifiers()
            # 这里可以解析修饰符标志
        except:
            pass
        
        # 获取继承信息
        extends = None
        try:
            superclass_type = type_decl.getSuperclassType()
            if superclass_type:
                extends = str(superclass_type)
        except:
            pass
        
        # 获取实现的接口
        implements = []
        try:
            super_interfaces = type_decl.superInterfaceTypes()
            if super_interfaces:
                for i in range(super_interfaces.size()):
                    interface_type = super_interfaces.get(i)
                    implements.append(str(interface_type))
        except:
            pass
        
        # 创建Java类对象
        java_class = JavaClass(
            name=class_name,
            package=package_name,
            file_path=file_path,
            line_number=1,
            modifiers=modifiers,
            extends=extends,
            implements=implements,
            is_interface=type_decl.isInterface() if hasattr(type_decl, 'isInterface') else False
        )
        
        # 提取方法
        try:
            methods = type_decl.getMethods()
            if methods:
                for i in range(len(methods)):
                    method = methods[i]
                    java_method = self._extract_method_declaration(method, class_name, file_path)
                    if java_method:
                        java_class.methods.append(java_method)
        except Exception as e:
            logger.warning(f"提取方法失败: {e}")
        
        return java_class
    
    def _extract_method_declaration(self, method_decl, class_name: str, file_path: str) -> Optional[JavaMethod]:
        """提取方法声明信息"""
        try:
            method_name = str(method_decl.getName())
            
            # 获取参数
            parameters = []
            try:
                params = method_decl.parameters()
                if params:
                    for i in range(params.size()):
                        param = params.get(i)
                        param_type = str(param.getType())
                        parameters.append(param_type)
            except:
                pass
            
            # 获取返回类型
            return_type = ""
            try:
                ret_type = method_decl.getReturnType2()
                if ret_type:
                    return_type = str(ret_type)
            except:
                pass
            
            # 创建方法对象
            java_method = JavaMethod(
                name=method_name,
                class_name=class_name,
                file_path=file_path,
                line_number=1,
                parameters=parameters,
                return_type=return_type,
                is_constructor=method_decl.isConstructor() if hasattr(method_decl, 'isConstructor') else False
            )
            
            # 提取方法调用
            java_method.method_calls = self._extract_method_calls(method_decl)
            
            return java_method
            
        except Exception as e:
            logger.warning(f"提取方法声明失败: {e}")
            return None
    
    def _extract_method_calls(self, method_decl) -> List[Dict]:
        """提取方法调用"""
        calls = []
        try:
            # 这里需要遍历方法体中的所有方法调用
            # 由于AST遍历比较复杂，暂时返回空列表
            # 可以在后续版本中实现完整的方法调用提取
            pass
        except Exception as e:
            logger.warning(f"提取方法调用失败: {e}")
        
        return calls
    
    def parse_project(self, project_path: str) -> Dict[str, JavaClass]:
        """解析整个Java项目"""
        if not self.initialize_jdt():
            logger.error("JDT环境未初始化")
            return {}
        
        project_path = Path(project_path)
        java_classes = {}
        
        logger.info(f"开始解析Java项目: {project_path}")
        
        # 查找所有Java文件
        java_files = []
        exclude_patterns = self.config['parsing'].get('exclude_patterns', [])
        
        for java_file in project_path.rglob("*.java"):
            # 检查是否应该排除
            should_exclude = False
            for pattern in exclude_patterns:
                if java_file.match(pattern):
                    should_exclude = True
                    break
            
            if not should_exclude:
                java_files.append(java_file)
        
        logger.info(f"找到 {len(java_files)} 个Java文件")
        
        # 解析每个Java文件
        for i, java_file in enumerate(java_files, 1):
            if i % 50 == 0 or i == len(java_files):
                logger.info(f"解析进度: {i}/{len(java_files)} ({i/len(java_files)*100:.1f}%)")
            
            java_class = self.parse_java_file(str(java_file))
            if java_class:
                key = f"{java_class.package}.{java_class.name}" if java_class.package else java_class.name
                java_classes[key] = java_class
        
        logger.info(f"项目解析完成，共解析 {len(java_classes)} 个类")
        self.java_classes = java_classes
        return java_classes
    
    def shutdown(self):
        """关闭JDT环境"""
        if self.jpype and self.jpype.isJVMStarted():
            try:
                self.jpype.shutdownJVM()
                logger.info("JVM已关闭")
            except Exception as e:
                logger.warning(f"关闭JVM时出现警告: {e}")


def test_fixed_parser():
    """测试修复版本的解析器"""
    parser = JDTParserFixed()
    
    # 测试解析单个文件
    test_file = "test_projects/sc_pcc_business/src/main/java/com/unicom/microserv/cs/pcc/core/sheetmerge/controller/SheetMergeController.java"
    if os.path.exists(test_file):
        java_class = parser.parse_java_file(test_file)
        if java_class:
            print(f"✅ 解析成功: {java_class.name}")
            print(f"   包名: {java_class.package}")
            print(f"   方法数量: {len(java_class.methods)}")
            for method in java_class.methods:
                print(f"   - {method.name}({', '.join(method.parameters)})")
        else:
            print("❌ 解析失败")
    else:
        print(f"❌ 测试文件不存在: {test_file}")
    
    parser.shutdown()


if __name__ == "__main__":
    test_fixed_parser()