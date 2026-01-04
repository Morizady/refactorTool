#!/usr/bin/env python3
"""
基于JPype和Eclipse JDT的Java代码解析器
提供精确的Java代码分析功能，替代javalang
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
import zipfile
import hashlib

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

class JDTParser:
    """基于Eclipse JDT的Java代码解析器"""
    
    def __init__(self, config_path: str = "config.yml"):
        """初始化JDT解析器"""
        self.config = self._load_config(config_path)
        self.jpype = None
        self.jdt_initialized = False
        self.java_classes = {}  # 缓存解析的类
        self.project_classpath = []
        
        # JDT相关的Java类引用
        self.ASTParser = None
        self.AST = None
        self.ASTVisitor = None
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
        
        if log_config.get('file'):
            os.makedirs(os.path.dirname(log_config['file']), exist_ok=True)
            file_handler = logging.FileHandler(log_config['file'], encoding='utf-8')
            file_handler.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    def initialize_jdt(self) -> bool:
        """初始化JDT环境"""
        if self.jdt_initialized:
            return True
            
        try:
            # 检查并下载JDT依赖
            if not self._ensure_jdt_dependencies():
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
    
    def _ensure_jdt_dependencies(self) -> bool:
        """确保JDT依赖存在"""
        jdt_lib_dir = Path(self.config['java']['jdt_lib_dir'])
        
        # 检查是否已存在JDT JAR文件
        jdt_core_jar = jdt_lib_dir / "org.eclipse.jdt.core.jar"
        
        if jdt_core_jar.exists():
            logger.info("JDT依赖已存在")
            return True
        
        if not self.config['java']['auto_download_jdt']:
            logger.error("JDT依赖不存在且未启用自动下载")
            return False
        
        logger.info("开始下载JDT依赖...")
        return self._download_jdt_dependencies(jdt_lib_dir)
    
    def _download_jdt_dependencies(self, lib_dir: Path) -> bool:
        """下载JDT依赖"""
        try:
            lib_dir.mkdir(parents=True, exist_ok=True)
            
            # JDT Core下载URL (使用Maven Central)
            jdt_version = self.config.get('java', {}).get('jdt_version', '3.13.0')  # 从配置读取版本
            jdt_url = f"https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/{jdt_version}/org.eclipse.jdt.core-{jdt_version}.jar"
            
            jdt_jar_path = lib_dir / "org.eclipse.jdt.core.jar"
            
            logger.info(f"下载JDT Core: {jdt_url}")
            urllib.request.urlretrieve(jdt_url, jdt_jar_path)
            
            # 验证下载的文件
            if jdt_jar_path.exists() and jdt_jar_path.stat().st_size > 1000000:  # 至少1MB
                logger.info("JDT依赖下载成功")
                return True
            else:
                logger.error("JDT依赖下载失败或文件损坏")
                return False
                
        except Exception as e:
            logger.error(f"下载JDT依赖失败: {e}")
            return False
    
    def _initialize_jpype(self) -> bool:
        """初始化JPype"""
        try:
            import jpype
            self.jpype = jpype
            
            if jpype.isJVMStarted():
                logger.info("JVM已启动")
                return True
            
            # 获取Java路径
            java_home = self.config['java']['java_home']
            if not java_home:
                java_home = os.environ.get('JAVA_HOME')
            
            if not java_home:
                logger.error("未找到JAVA_HOME，请在配置文件中设置java.java_home")
                return False
            
            # 构建classpath
            jdt_lib_dir = Path(self.config['java']['jdt_lib_dir'])
            classpath = []
            
            # 添加JDT JAR文件
            for jar_file in jdt_lib_dir.glob("*.jar"):
                classpath.append(str(jar_file))
            
            if not classpath:
                logger.error("未找到JDT JAR文件")
                return False
            
            # 简化的JVM启动
            logger.info("启动JVM...")
            
            # 基本JVM参数
            jvm_args = ["-Xmx2g", "-Xms512m"]
            
            try:
                # 尝试启动JVM
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    *jvm_args,
                    classpath=classpath
                )
                logger.info("JVM启动成功")
                return True
                
            except Exception as e:
                logger.error(f"JVM启动失败: {e}")
                # 尝试不使用classpath参数
                try:
                    jpype.startJVM(jpype.getDefaultJVMPath(), *jvm_args)
                    logger.info("JVM启动成功（无classpath）")
                    return True
                except Exception as e2:
                    logger.error(f"JVM启动完全失败: {e2}")
                    return False
            
        except ImportError:
            logger.error("JPype未安装，请运行: pip install JPype1")
            return False
        except Exception as e:
            logger.error(f"JPype初始化失败: {e}")
            return False
    
    def _import_jdt_classes(self) -> bool:
        """导入JDT相关的Java类"""
        try:
            # 导入JDT核心类
            self.ASTParser = self.jpype.JClass("org.eclipse.jdt.core.dom.ASTParser")
            self.AST = self.jpype.JClass("org.eclipse.jdt.core.dom.AST")
            self.ASTVisitor = self.jpype.JClass("org.eclipse.jdt.core.dom.ASTVisitor")
            self.CompilationUnit = self.jpype.JClass("org.eclipse.jdt.core.dom.CompilationUnit")
            
            # 导入其他需要的类
            self.ASTNode = self.jpype.JClass("org.eclipse.jdt.core.dom.ASTNode")
            self.MethodDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.MethodDeclaration")
            self.TypeDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.TypeDeclaration")
            self.MethodInvocation = self.jpype.JClass("org.eclipse.jdt.core.dom.MethodInvocation")
            self.FieldDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.FieldDeclaration")
            self.ImportDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.ImportDeclaration")
            self.PackageDeclaration = self.jpype.JClass("org.eclipse.jdt.core.dom.PackageDeclaration")
            
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
    
    def find_method_calls(self, class_name: str, method_name: str, max_depth: int = 4) -> List[Dict]:
        """查找方法的所有调用链"""
        if not self.java_classes:
            logger.warning("未解析任何Java类，请先调用parse_project")
            return []
        
        # 查找目标方法
        target_class = None
        target_method = None
        
        for cls in self.java_classes.values():
            if cls.name == class_name:
                target_class = cls
                for method in cls.methods:
                    if method.name == method_name:
                        target_method = method
                        break
                break
        
        if not target_method:
            logger.warning(f"未找到方法: {class_name}.{method_name}")
            return []
        
        # 递归分析方法调用
        return self._analyze_method_calls_recursive(target_method, 0, max_depth, set())
    
    def _analyze_method_calls_recursive(self, method: JavaMethod, depth: int, max_depth: int, visited: set) -> List[Dict]:
        """递归分析方法调用"""
        if depth >= max_depth:
            return []
        
        method_key = f"{method.class_name}.{method.name}"
        if method_key in visited:
            return []
        
        visited.add(method_key)
        calls = []
        
        for call in method.method_calls:
            call_info = {
                "method": call["method"],
                "object": call.get("object", ""),
                "line": call.get("line", 0),
                "arguments": call.get("arguments", 0),
                "type": call.get("type", "instance")
            }
            
            # 查找被调用方法的实现
            implementations = self._find_method_implementations(call)
            if implementations:
                call_info["implementations"] = []
                
                for impl in implementations:
                    impl_info = {
                        "class": impl["class"],
                        "file": impl["file"],
                        "type": impl["type"]
                    }
                    
                    # 递归分析子调用
                    if impl["method"]:
                        sub_calls = self._analyze_method_calls_recursive(
                            impl["method"], depth + 1, max_depth, visited.copy()
                        )
                        if sub_calls:
                            impl_info["sub_calls"] = {"calls": sub_calls}
                    
                    call_info["implementations"].append(impl_info)
            
            calls.append(call_info)
        
        visited.remove(method_key)
        return calls
    
    def _find_method_implementations(self, call: Dict) -> List[Dict]:
        """查找方法实现"""
        implementations = []
        method_name = call["method"]
        object_name = call.get("object", "")
        
        # 在所有类中查找匹配的方法
        for cls in self.java_classes.values():
            # 检查类名匹配
            if object_name and cls.name != object_name:
                continue
            
            # 查找匹配的方法
            for method in cls.methods:
                if method.name == method_name:
                    implementations.append({
                        "class": cls.name,
                        "file": cls.file_path,
                        "method": method,
                        "type": "concrete"
                    })
        
        return implementations
    
    def get_class_hierarchy(self) -> Dict[str, Dict]:
        """获取类继承关系"""
        hierarchy = {}
        
        for cls in self.java_classes.values():
            class_info = {
                "name": cls.name,
                "package": cls.package,
                "file": cls.file_path,
                "extends": cls.extends,
                "implements": cls.implements,
                "is_interface": cls.is_interface,
                "is_abstract": cls.is_abstract
            }
            
            key = f"{cls.package}.{cls.name}" if cls.package else cls.name
            hierarchy[key] = class_info
        
        return hierarchy
    
    def shutdown(self):
        """关闭JDT环境"""
        if self.jpype and self.jpype.isJVMStarted():
            try:
                self.jpype.shutdownJVM()
                logger.info("JVM已关闭")
            except Exception as e:
                logger.warning(f"关闭JVM时出现警告: {e}")


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
            # 获取方法体
            body = method_decl.getBody()
            if body:
                # 遍历方法体中的所有语句
                calls = self._extract_calls_from_block(body)
        except Exception as e:
            logger.warning(f"提取方法调用失败: {e}")
        
        return calls
    
    def _extract_calls_from_block(self, block) -> List[Dict]:
        """从代码块中提取方法调用"""
        calls = []
        try:
            statements = block.statements()
            if statements:
                for i in range(statements.size()):
                    stmt = statements.get(i)
                    calls.extend(self._extract_calls_from_statement(stmt))
        except Exception as e:
            logger.warning(f"从代码块提取调用失败: {e}")
        
        return calls
    
    def _extract_calls_from_statement(self, stmt) -> List[Dict]:
        """从语句中提取方法调用"""
        calls = []
        try:
            stmt_type = stmt.getClass().getSimpleName()
            
            if stmt_type == "ExpressionStatement":
                # 表达式语句
                expr = stmt.getExpression()
                calls.extend(self._extract_calls_from_expression(expr))
            elif stmt_type == "VariableDeclarationStatement":
                # 变量声明语句
                fragments = stmt.fragments()
                if fragments:
                    for j in range(fragments.size()):
                        fragment = fragments.get(j)
                        initializer = fragment.getInitializer()
                        if initializer:
                            calls.extend(self._extract_calls_from_expression(initializer))
            elif stmt_type == "ReturnStatement":
                # 返回语句
                expr = stmt.getExpression()
                if expr:
                    calls.extend(self._extract_calls_from_expression(expr))
            elif stmt_type == "IfStatement":
                # if语句
                condition = stmt.getExpression()
                if condition:
                    calls.extend(self._extract_calls_from_expression(condition))
                
                then_stmt = stmt.getThenStatement()
                if then_stmt:
                    calls.extend(self._extract_calls_from_statement(then_stmt))
                
                else_stmt = stmt.getElseStatement()
                if else_stmt:
                    calls.extend(self._extract_calls_from_statement(else_stmt))
            elif stmt_type == "Block":
                # 代码块
                calls.extend(self._extract_calls_from_block(stmt))
                
        except Exception as e:
            logger.warning(f"从语句提取调用失败: {e}")
        
        return calls
    
    def _extract_calls_from_expression(self, expr) -> List[Dict]:
        """从表达式中提取方法调用"""
        calls = []
        try:
            expr_type = expr.getClass().getSimpleName()
            
            if expr_type == "MethodInvocation":
                # 方法调用
                call_info = self._extract_method_invocation(expr)
                if call_info:
                    calls.append(call_info)
            elif expr_type == "ClassInstanceCreation":
                # 构造函数调用
                call_info = self._extract_constructor_call(expr)
                if call_info:
                    calls.append(call_info)
            elif expr_type == "Assignment":
                # 赋值表达式
                right_side = expr.getRightHandSide()
                if right_side:
                    calls.extend(self._extract_calls_from_expression(right_side))
            elif expr_type == "InfixExpression":
                # 中缀表达式
                left = expr.getLeftOperand()
                right = expr.getRightOperand()
                if left:
                    calls.extend(self._extract_calls_from_expression(left))
                if right:
                    calls.extend(self._extract_calls_from_expression(right))
                    
        except Exception as e:
            logger.warning(f"从表达式提取调用失败: {e}")
        
        return calls
    
    def _extract_method_invocation(self, method_invocation) -> Optional[Dict]:
        """提取方法调用信息"""
        try:
            method_name = str(method_invocation.getName())
            
            # 获取调用对象
            expression = method_invocation.getExpression()
            object_name = ""
            if expression:
                object_name = str(expression)
            
            # 获取参数数量
            arguments = method_invocation.arguments()
            arg_count = arguments.size() if arguments else 0
            
            # 获取参数类型
            arg_types = []
            if arguments:
                for i in range(arguments.size()):
                    arg = arguments.get(i)
                    arg_types.append(str(arg))
            
            return {
                "method": method_name,
                "object": object_name,
                "arguments": arg_count,
                "argument_types": arg_types,
                "type": "instance" if object_name else "static",
                "line": 0  # JDT可以提供准确的行号
            }
            
        except Exception as e:
            logger.warning(f"提取方法调用信息失败: {e}")
            return None
    
    def _extract_constructor_call(self, constructor_call) -> Optional[Dict]:
        """提取构造函数调用信息"""
        try:
            type_name = str(constructor_call.getType())
            
            # 获取参数数量
            arguments = constructor_call.arguments()
            arg_count = arguments.size() if arguments else 0
            
            # 获取参数类型
            arg_types = []
            if arguments:
                for i in range(arguments.size()):
                    arg = arguments.get(i)
                    arg_types.append(str(arg))
            
            return {
                "method": "<init>",
                "object": type_name,
                "arguments": arg_count,
                "argument_types": arg_types,
                "type": "constructor",
                "line": 0
            }
            
        except Exception as e:
            logger.warning(f"提取构造函数调用信息失败: {e}")
            return None


# 使用示例和测试函数
def test_jdt_parser():
    """测试JDT解析器"""
    parser = JDTParser()
    
    # 测试解析单个文件
    test_file = "test_projects/sc_pcc_business/src/main/java/com/example/TestController.java"
    if os.path.exists(test_file):
        java_class = parser.parse_java_file(test_file)
        if java_class:
            print(f"解析成功: {java_class.name}")
            for method in java_class.methods:
                print(f"  方法: {method.name}")
    
    # 测试解析项目
    project_path = "test_projects/sc_pcc_business"
    if os.path.exists(project_path):
        classes = parser.parse_project(project_path)
        print(f"项目解析完成，共 {len(classes)} 个类")
    
    parser.shutdown()


if __name__ == "__main__":
    test_jdt_parser()