#!/usr/bin/env python3
"""
JAR包方法推理器 - 用于推理外部JAR包中的方法
支持MyBatis-Plus、Spring Framework等常见框架的方法推理
"""

import os
import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class FrameworkMethod:
    """框架方法信息"""
    method_name: str
    class_name: str
    package: str
    description: str
    parameters: List[str]
    return_type: str
    framework: str
    version: str = ""
    is_inherited: bool = False
    parent_class: str = ""

class JarMethodResolver:
    """JAR包方法推理器"""
    
    def __init__(self, config_path: str = "framework_methods.json"):
        self.framework_methods = {}  # {framework: {class: [methods]}}
        self.inheritance_chains = {}  # {class: parent_class}
        self.interface_implementations = {}  # {interface: [implementations]}
        
        # 加载框架方法定义
        self._load_framework_methods(config_path)
        
        # 初始化常见框架的方法映射
        self._initialize_framework_mappings()
    
    def _load_framework_methods(self, config_path: str):
        """加载框架方法配置"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 转换字典为FrameworkMethod对象
                    raw_methods = data.get('framework_methods', {})
                    self.framework_methods = {}
                    
                    for framework, classes in raw_methods.items():
                        self.framework_methods[framework] = {}
                        for class_name, methods in classes.items():
                            self.framework_methods[framework][class_name] = []
                            for method_data in methods:
                                method_obj = FrameworkMethod(
                                    method_name=method_data['method_name'],
                                    class_name=method_data['class_name'],
                                    package=method_data['package'],
                                    description=method_data['description'],
                                    parameters=method_data['parameters'],
                                    return_type=method_data['return_type'],
                                    framework=method_data['framework'],
                                    version=method_data.get('version', ''),
                                    is_inherited=method_data.get('is_inherited', False),
                                    parent_class=method_data.get('parent_class', '')
                                )
                                self.framework_methods[framework][class_name].append(method_obj)
                    
                    self.inheritance_chains = data.get('inheritance_chains', {})
                    self.interface_implementations = data.get('interface_implementations', {})
                logger.info(f"✅ 加载框架方法配置: {len(self.framework_methods)} 个框架")
            else:
                logger.info(f"⚠️ 框架方法配置文件不存在: {config_path}，使用默认配置")
        except Exception as e:
            logger.warning(f"加载框架方法配置失败: {e}")
    
    def _initialize_framework_mappings(self):
        """初始化常见框架的方法映射"""
        # MyBatis-Plus ServiceImpl 方法
        mybatis_plus_methods = [
            FrameworkMethod("insertOrUpdate", "ServiceImpl", "com.baomidou.mybatisplus.service.impl", 
                          "插入或更新实体", ["entity"], "boolean", "MyBatis-Plus", "3.x", True, "IService"),
            FrameworkMethod("selectById", "ServiceImpl", "com.baomidou.mybatisplus.service.impl",
                          "根据ID查询", ["id"], "T", "MyBatis-Plus", "3.x", True, "IService"),
            FrameworkMethod("selectList", "ServiceImpl", "com.baomidou.mybatisplus.service.impl",
                          "查询列表", ["wrapper"], "List<T>", "MyBatis-Plus", "3.x", True, "IService"),
            FrameworkMethod("insert", "ServiceImpl", "com.baomidou.mybatisplus.service.impl",
                          "插入实体", ["entity"], "boolean", "MyBatis-Plus", "3.x", True, "IService"),
            FrameworkMethod("updateById", "ServiceImpl", "com.baomidou.mybatisplus.service.impl",
                          "根据ID更新", ["entity"], "boolean", "MyBatis-Plus", "3.x", True, "IService"),
            FrameworkMethod("deleteById", "ServiceImpl", "com.baomidou.mybatisplus.service.impl",
                          "根据ID删除", ["id"], "boolean", "MyBatis-Plus", "3.x", True, "IService"),
        ]
        
        # Spring Framework 方法
        spring_methods = [
            FrameworkMethod("getBean", "ApplicationContext", "org.springframework.context",
                          "获取Bean实例", ["name"], "Object", "Spring", "5.x"),
            FrameworkMethod("autowire", "AutowireCapableBeanFactory", "org.springframework.beans.factory.config",
                          "自动装配", ["existingBean", "autowireMode", "dependencyCheck"], "void", "Spring", "5.x"),
        ]
        
        # Java标准库方法
        java_stdlib_methods = [
            # Map接口方法
            FrameworkMethod("keySet", "Map", "java.util", "返回此映射中包含的键的Set视图", [], "Set<K>", "Java-Stdlib", "8+"),
            FrameworkMethod("values", "Map", "java.util", "返回此映射中包含的值的Collection视图", [], "Collection<V>", "Java-Stdlib", "8+"),
            FrameworkMethod("entrySet", "Map", "java.util", "返回此映射中包含的映射关系的Set视图", [], "Set<Map.Entry<K,V>>", "Java-Stdlib", "8+"),
            FrameworkMethod("get", "Map", "java.util", "返回指定键所映射的值", ["key"], "V", "Java-Stdlib", "8+"),
            FrameworkMethod("put", "Map", "java.util", "将指定的值与此映射中的指定键关联", ["key", "value"], "V", "Java-Stdlib", "8+"),
            FrameworkMethod("remove", "Map", "java.util", "如果存在一个键的映射关系，则将其从此映射中移除", ["key"], "V", "Java-Stdlib", "8+"),
            FrameworkMethod("size", "Map", "java.util", "返回此映射中的键-值映射关系数", [], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("isEmpty", "Map", "java.util", "如果此映射未包含键-值映射关系，则返回true", [], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("containsKey", "Map", "java.util", "如果此映射包含指定键的映射关系，则返回true", ["key"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("containsValue", "Map", "java.util", "如果此映射将一个或多个键映射到指定值，则返回true", ["value"], "boolean", "Java-Stdlib", "8+"),
            
            # Collection接口方法
            FrameworkMethod("add", "Collection", "java.util", "确保此collection包含指定的元素", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("remove", "Collection", "java.util", "从此collection中移除指定元素的单个实例", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("size", "Collection", "java.util", "返回此collection中的元素数", [], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("isEmpty", "Collection", "java.util", "如果此collection不包含元素，则返回true", [], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("contains", "Collection", "java.util", "如果此collection包含指定的元素，则返回true", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("iterator", "Collection", "java.util", "返回在此collection的元素上进行迭代的迭代器", [], "Iterator<E>", "Java-Stdlib", "8+"),
            FrameworkMethod("toArray", "Collection", "java.util", "返回包含此collection中所有元素的数组", [], "Object[]", "Java-Stdlib", "8+"),
            
            # Set接口方法 (继承Collection，但这里明确列出常用方法)
            FrameworkMethod("add", "Set", "java.util", "如果指定的元素尚未存在，则将其添加到此set中", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("remove", "Set", "java.util", "如果指定的元素存在于此set中，则将其移除", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("contains", "Set", "java.util", "如果此set包含指定的元素，则返回true", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("size", "Set", "java.util", "返回此set中的元素数", [], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("isEmpty", "Set", "java.util", "如果此set不包含元素，则返回true", [], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("iterator", "Set", "java.util", "返回在此set的元素上进行迭代的迭代器", [], "Iterator<E>", "Java-Stdlib", "8+"),
            
            # List接口方法
            FrameworkMethod("get", "List", "java.util", "返回此列表中指定位置的元素", ["index"], "E", "Java-Stdlib", "8+"),
            FrameworkMethod("set", "List", "java.util", "用指定元素替换此列表中指定位置的元素", ["index", "element"], "E", "Java-Stdlib", "8+"),
            FrameworkMethod("add", "List", "java.util", "将指定的元素添加到此列表的尾部", ["element"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("remove", "List", "java.util", "移除此列表中指定位置的元素", ["index"], "E", "Java-Stdlib", "8+"),
            FrameworkMethod("indexOf", "List", "java.util", "返回此列表中首次出现的指定元素的索引", ["element"], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("size", "List", "java.util", "返回此列表中的元素数", [], "int", "Java-Stdlib", "8+"),
            
            # String类方法
            FrameworkMethod("length", "String", "java.lang", "返回此字符串的长度", [], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("charAt", "String", "java.lang", "返回指定索引处的char值", ["index"], "char", "Java-Stdlib", "8+"),
            FrameworkMethod("substring", "String", "java.lang", "返回一个新的字符串，它是此字符串的一个子字符串", ["beginIndex"], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("indexOf", "String", "java.lang", "返回指定字符在此字符串中第一次出现处的索引", ["ch"], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("toLowerCase", "String", "java.lang", "使用默认语言环境的规则将此String中的所有字符都转换为小写", [], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("toUpperCase", "String", "java.lang", "使用默认语言环境的规则将此String中的所有字符都转换为大写", [], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("trim", "String", "java.lang", "返回字符串的副本，忽略前导空白和尾部空白", [], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("replace", "String", "java.lang", "返回一个新的字符串，它是通过用newChar替换此字符串中出现的所有oldChar得到的", ["oldChar", "newChar"], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("split", "String", "java.lang", "根据给定正则表达式的匹配拆分此字符串", ["regex"], "String[]", "Java-Stdlib", "8+"),
            FrameworkMethod("equals", "String", "java.lang", "将此字符串与指定的对象比较", ["anObject"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("equalsIgnoreCase", "String", "java.lang", "将此String与另一个String比较，不考虑大小写", ["anotherString"], "boolean", "Java-Stdlib", "8+"),
            
            # Object类方法
            FrameworkMethod("toString", "Object", "java.lang", "返回该对象的字符串表示", [], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("equals", "Object", "java.lang", "指示其他某个对象是否与此对象相等", ["obj"], "boolean", "Java-Stdlib", "8+"),
            FrameworkMethod("hashCode", "Object", "java.lang", "返回该对象的哈希码值", [], "int", "Java-Stdlib", "8+"),
            FrameworkMethod("getClass", "Object", "java.lang", "返回此Object的运行时类", [], "Class<?>", "Java-Stdlib", "8+"),
            
            # Class类方法
            FrameworkMethod("newInstance", "Class", "java.lang", "创建此Class对象所表示的类的一个新实例", [], "T", "Java-Stdlib", "8+"),
            FrameworkMethod("getName", "Class", "java.lang", "以String的形式返回此Class对象所表示的实体名称", [], "String", "Java-Stdlib", "8+"),
            FrameworkMethod("getSimpleName", "Class", "java.lang", "返回源代码中给出的底层类的简称", [], "String", "Java-Stdlib", "8+"),
        ]
        
        # 将方法添加到框架映射中
        if "MyBatis-Plus" not in self.framework_methods:
            self.framework_methods["MyBatis-Plus"] = {}
        
        if "ServiceImpl" not in self.framework_methods["MyBatis-Plus"]:
            self.framework_methods["MyBatis-Plus"]["ServiceImpl"] = []
        
        self.framework_methods["MyBatis-Plus"]["ServiceImpl"].extend(mybatis_plus_methods)
        
        if "Spring" not in self.framework_methods:
            self.framework_methods["Spring"] = {}
        
        for method in spring_methods:
            if method.class_name not in self.framework_methods["Spring"]:
                self.framework_methods["Spring"][method.class_name] = []
            self.framework_methods["Spring"][method.class_name].append(method)
        
        # 添加Java标准库方法
        if "Java-Stdlib" not in self.framework_methods:
            self.framework_methods["Java-Stdlib"] = {}
        
        for method in java_stdlib_methods:
            if method.class_name not in self.framework_methods["Java-Stdlib"]:
                self.framework_methods["Java-Stdlib"][method.class_name] = []
            self.framework_methods["Java-Stdlib"][method.class_name].append(method)
        
        # 设置继承关系
        self.inheritance_chains.update({
            "BaseServiceImpl": "ServiceImpl",
            "ServiceImpl": "IService",
            "BaseDatagridController": "BaseController",
        })
        
        logger.info(f"✅ 初始化框架映射完成: MyBatis-Plus({len(mybatis_plus_methods)}个方法), Spring({len(spring_methods)}个方法), Java-Stdlib({len(java_stdlib_methods)}个方法)")
    
    def resolve_method(self, class_name: str, method_name: str, context: Dict = None) -> Optional[FrameworkMethod]:
        """
        推理方法实现
        
        Args:
            class_name: 类名（可能是项目中的类或框架类）
            method_name: 方法名
            context: 上下文信息，包含继承关系、import信息等
        
        Returns:
            FrameworkMethod: 推理出的方法信息，如果无法推理则返回None
        """
        logger.debug(f"🔍 推理方法: {class_name}.{method_name}")
        
        # 1. 直接查找框架方法
        framework_method = self._find_direct_framework_method(class_name, method_name)
        if framework_method:
            logger.debug(f"✅ 直接找到框架方法: {framework_method.framework}")
            return framework_method
        
        # 2. 通过继承关系推理
        inherited_method = self._find_inherited_method(class_name, method_name, context)
        if inherited_method:
            logger.debug(f"✅ 通过继承推理找到方法: {inherited_method.parent_class}")
            return inherited_method
        
        # 3. 通过接口实现推理
        interface_method = self._find_interface_method(class_name, method_name, context)
        if interface_method:
            logger.debug(f"✅ 通过接口推理找到方法: {interface_method.framework}")
            return interface_method
        
        # 4. 通过命名模式推理
        pattern_method = self._infer_by_naming_pattern(class_name, method_name, context)
        if pattern_method:
            logger.debug(f"✅ 通过命名模式推理找到方法: {pattern_method.framework}")
            return pattern_method
        
        logger.debug(f"❌ 无法推理方法: {class_name}.{method_name}")
        return None
    
    def _find_direct_framework_method(self, class_name: str, method_name: str) -> Optional[FrameworkMethod]:
        """直接查找框架方法"""
        for framework, classes in self.framework_methods.items():
            if class_name in classes:
                for method in classes[class_name]:
                    if method.method_name == method_name:
                        return method
        return None
    
    def _find_inherited_method(self, class_name: str, method_name: str, context: Dict = None) -> Optional[FrameworkMethod]:
        """通过继承关系查找方法"""
        if not context:
            context = {}
        
        # 获取继承链
        inheritance_chain = self._get_inheritance_chain(class_name, context)
        
        for parent_class in inheritance_chain:
            # 在框架方法中查找父类方法
            framework_method = self._find_direct_framework_method(parent_class, method_name)
            if framework_method:
                # 创建继承的方法副本
                inherited_method = FrameworkMethod(
                    method_name=framework_method.method_name,
                    class_name=class_name,  # 使用当前类名
                    package=framework_method.package,
                    description=f"继承自{parent_class}: {framework_method.description}",
                    parameters=framework_method.parameters,
                    return_type=framework_method.return_type,
                    framework=framework_method.framework,
                    version=framework_method.version,
                    is_inherited=True,
                    parent_class=parent_class
                )
                return inherited_method
        
        return None
    
    def _get_inheritance_chain(self, class_name: str, context: Dict) -> List[str]:
        """获取类的继承链"""
        chain = []
        current_class = class_name
        
        # 从上下文中获取继承信息
        class_hierarchy = context.get('class_hierarchy', {})
        
        # 最多追溯10层继承，避免无限循环
        for _ in range(10):
            # 先从上下文中查找
            if current_class in class_hierarchy:
                parent = class_hierarchy[current_class].get('parent')
                if parent and parent not in chain:
                    chain.append(parent)
                    current_class = parent
                else:
                    break
            # 再从预定义的继承关系中查找
            elif current_class in self.inheritance_chains:
                parent = self.inheritance_chains[current_class]
                if parent and parent not in chain:
                    chain.append(parent)
                    current_class = parent
                else:
                    break
            else:
                break
        
        return chain
    
    def _find_interface_method(self, class_name: str, method_name: str, context: Dict = None) -> Optional[FrameworkMethod]:
        """通过接口实现查找方法"""
        if not context:
            return None
        
        # 获取类实现的接口
        class_hierarchy = context.get('class_hierarchy', {})
        if class_name not in class_hierarchy:
            return None
        
        interfaces = class_hierarchy[class_name].get('interfaces', [])
        
        for interface in interfaces:
            # 在框架方法中查找接口方法
            framework_method = self._find_direct_framework_method(interface, method_name)
            if framework_method:
                # 创建接口实现的方法副本
                interface_method = FrameworkMethod(
                    method_name=framework_method.method_name,
                    class_name=class_name,
                    package=framework_method.package,
                    description=f"实现接口{interface}: {framework_method.description}",
                    parameters=framework_method.parameters,
                    return_type=framework_method.return_type,
                    framework=framework_method.framework,
                    version=framework_method.version,
                    is_inherited=True,
                    parent_class=interface
                )
                return interface_method
        
        return None
    
    def _infer_by_naming_pattern(self, class_name: str, method_name: str, context: Dict = None) -> Optional[FrameworkMethod]:
        """通过命名模式推理方法"""
        
        # Java标准库模式推理
        if self._is_java_stdlib_class(class_name, context):
            return self._infer_java_stdlib_method(class_name, method_name)
        
        # MyBatis-Plus 模式推理
        if self._is_mybatis_plus_class(class_name, context):
            return self._infer_mybatis_plus_method(class_name, method_name)
        
        # Spring 模式推理
        if self._is_spring_class(class_name, context):
            return self._infer_spring_method(class_name, method_name)
        
        return None
    
    def _is_mybatis_plus_class(self, class_name: str, context: Dict = None) -> bool:
        """判断是否是MyBatis-Plus相关的类"""
        mybatis_plus_indicators = [
            "ServiceImpl", "BaseServiceImpl", "BaseMapper", "Mapper"
        ]
        
        # 检查类名模式
        if any(indicator in class_name for indicator in mybatis_plus_indicators):
            return True
        
        # 检查继承关系
        if context and 'class_hierarchy' in context:
            class_info = context['class_hierarchy'].get(class_name, {})
            parent = class_info.get('parent', '')
            if any(indicator in parent for indicator in mybatis_plus_indicators):
                return True
        
        # 检查import语句
        if context and 'imports' in context:
            imports = context['imports']
            mybatis_plus_imports = [
                'com.baomidou.mybatisplus',
                'com.baomidou.mybatisplus.service',
                'com.baomidou.mybatisplus.mapper'
            ]
            if any(any(mp_import in imp for mp_import in mybatis_plus_imports) for imp in imports):
                return True
        
        return False
    
    def _is_java_stdlib_class(self, class_name: str, context: Dict = None) -> bool:
        """判断是否是Java标准库类"""
        
        # 直接的Java标准库类名
        java_stdlib_classes = {
            "Map", "HashMap", "LinkedHashMap", "TreeMap", "ConcurrentHashMap",
            "List", "ArrayList", "LinkedList", "Vector",
            "Set", "HashSet", "LinkedHashSet", "TreeSet",
            "Collection", "Collections",
            "String", "StringBuilder", "StringBuffer",
            "Object", "Class",
            "Integer", "Long", "Double", "Float", "Boolean", "Character", "Byte", "Short",
            "Date", "Calendar", "LocalDate", "LocalDateTime",
            "Optional", "Stream"
        }
        
        # 检查简单类名
        simple_class_name = class_name.split('.')[-1] if '.' in class_name else class_name
        
        # 去掉泛型参数，如 Map<String,String> -> Map
        if '<' in simple_class_name:
            simple_class_name = simple_class_name.split('<')[0]
        
        if simple_class_name in java_stdlib_classes:
            return True
        
        # 检查完整包名
        if class_name.startswith('java.'):
            return True
        
        return False
    
    def _infer_java_stdlib_method(self, class_name: str, method_name: str) -> Optional[FrameworkMethod]:
        """推理Java标准库方法"""
        
        # 提取简单类名，去掉泛型参数
        simple_class_name = class_name.split('.')[-1] if '.' in class_name else class_name
        if '<' in simple_class_name:
            simple_class_name = simple_class_name.split('<')[0]
        
        # 在Java标准库方法中查找
        java_stdlib_framework = self.framework_methods.get("Java-Stdlib", {})
        
        # 直接匹配类名
        if simple_class_name in java_stdlib_framework:
            for method in java_stdlib_framework[simple_class_name]:
                if method.method_name == method_name:
                    # 创建推理结果，使用原始类名
                    return FrameworkMethod(
                        method_name=method.method_name,
                        class_name=class_name,  # 使用原始类名（可能包含泛型）
                        package=method.package,
                        description=method.description,
                        parameters=method.parameters,
                        return_type=method.return_type,
                        framework=method.framework,
                        version=method.version,
                        is_inherited=False,
                        parent_class=""
                    )
        
        # 尝试接口继承推理（如ArrayList实现List接口）
        interface_mappings = {
            "ArrayList": "List",
            "LinkedList": "List", 
            "Vector": "List",
            "HashSet": "Set",
            "LinkedHashSet": "Set",
            "TreeSet": "Set",
            "HashMap": "Map",
            "LinkedHashMap": "Map",
            "TreeMap": "Map",
            "ConcurrentHashMap": "Map"
        }
        
        if simple_class_name in interface_mappings:
            interface_name = interface_mappings[simple_class_name]
            if interface_name in java_stdlib_framework:
                for method in java_stdlib_framework[interface_name]:
                    if method.method_name == method_name:
                        return FrameworkMethod(
                            method_name=method.method_name,
                            class_name=class_name,
                            package=method.package,
                            description=f"继承自{interface_name}: {method.description}",
                            parameters=method.parameters,
                            return_type=method.return_type,
                            framework=method.framework,
                            version=method.version,
                            is_inherited=True,
                            parent_class=interface_name
                        )
        
        return None
        """判断是否是Spring相关的类"""
        spring_indicators = [
            "Controller", "Service", "Repository", "Component"
        ]
        
        # 检查类名模式
        if any(indicator in class_name for indicator in spring_indicators):
            return True
        
        # 检查import语句
        if context and 'imports' in context:
            imports = context['imports']
            spring_imports = [
                'org.springframework',
                'org.springframework.stereotype',
                'org.springframework.web.bind.annotation'
            ]
            if any(any(spring_import in imp for spring_import in spring_imports) for imp in imports):
                return True
        
        return False
    
    def _infer_mybatis_plus_method(self, class_name: str, method_name: str) -> Optional[FrameworkMethod]:
        """推理MyBatis-Plus方法"""
        
        # 常见的MyBatis-Plus方法模式
        mybatis_plus_patterns = {
            "insertOrUpdate": {
                "description": "插入或更新实体，根据主键判断",
                "parameters": ["entity"],
                "return_type": "boolean"
            },
            "selectById": {
                "description": "根据主键ID查询实体",
                "parameters": ["id"],
                "return_type": "T"
            },
            "selectList": {
                "description": "根据条件查询实体列表",
                "parameters": ["wrapper"],
                "return_type": "List<T>"
            },
            "selectOne": {
                "description": "根据条件查询单个实体",
                "parameters": ["wrapper"],
                "return_type": "T"
            },
            "insert": {
                "description": "插入实体",
                "parameters": ["entity"],
                "return_type": "boolean"
            },
            "updateById": {
                "description": "根据主键更新实体",
                "parameters": ["entity"],
                "return_type": "boolean"
            },
            "deleteById": {
                "description": "根据主键删除实体",
                "parameters": ["id"],
                "return_type": "boolean"
            },
            "selectPage": {
                "description": "分页查询",
                "parameters": ["page", "wrapper"],
                "return_type": "IPage<T>"
            },
            "count": {
                "description": "统计记录数",
                "parameters": ["wrapper"],
                "return_type": "int"
            },
            "baseListQuery": {
                "description": "基础列表查询（自定义方法）",
                "parameters": ["param"],
                "return_type": "List<T>"
            },
            "baseCountQuery": {
                "description": "基础计数查询（自定义方法）",
                "parameters": ["param"],
                "return_type": "int"
            }
        }
        
        if method_name in mybatis_plus_patterns:
            pattern = mybatis_plus_patterns[method_name]
            return FrameworkMethod(
                method_name=method_name,
                class_name=class_name,
                package="com.baomidou.mybatisplus.service.impl",
                description=pattern["description"],
                parameters=pattern["parameters"],
                return_type=pattern["return_type"],
                framework="MyBatis-Plus",
                version="3.x",
                is_inherited=True,
                parent_class="ServiceImpl"
            )
        
        return None
    
    def _is_spring_class(self, class_name: str, context: Dict = None) -> bool:
        """判断是否是Spring相关的类"""
        spring_indicators = [
            "Controller", "Service", "Repository", "Component"
        ]
        
        # 检查类名模式
        if any(indicator in class_name for indicator in spring_indicators):
            return True
        
        # 检查import语句
        if context and 'imports' in context:
            imports = context['imports']
            spring_imports = [
                'org.springframework',
                'org.springframework.stereotype',
                'org.springframework.web.bind.annotation'
            ]
            if any(any(spring_import in imp for spring_import in spring_imports) for imp in imports):
                return True
        
        return False
    
    def _infer_spring_method(self, class_name: str, method_name: str) -> Optional[FrameworkMethod]:
        """推理Spring方法"""
        
        # 常见的Spring方法模式
        spring_patterns = {
            "getBean": {
                "description": "从Spring容器获取Bean",
                "parameters": ["name"],
                "return_type": "Object"
            },
            "autowire": {
                "description": "自动装配Bean",
                "parameters": ["existingBean"],
                "return_type": "void"
            }
        }
        
        if method_name in spring_patterns:
            pattern = spring_patterns[method_name]
            return FrameworkMethod(
                method_name=method_name,
                class_name=class_name,
                package="org.springframework.context",
                description=pattern["description"],
                parameters=pattern["parameters"],
                return_type=pattern["return_type"],
                framework="Spring",
                version="5.x",
                is_inherited=False,
                parent_class=""
            )
        
        return None
    
    def get_framework_methods_for_class(self, class_name: str, context: Dict = None) -> List[FrameworkMethod]:
        """获取类的所有框架方法"""
        methods = []
        
        # 直接方法
        for framework, classes in self.framework_methods.items():
            if class_name in classes:
                methods.extend(classes[class_name])
        
        # 继承的方法
        if context:
            inheritance_chain = self._get_inheritance_chain(class_name, context)
            for parent_class in inheritance_chain:
                for framework, classes in self.framework_methods.items():
                    if parent_class in classes:
                        for method in classes[parent_class]:
                            inherited_method = FrameworkMethod(
                                method_name=method.method_name,
                                class_name=class_name,
                                package=method.package,
                                description=f"继承自{parent_class}: {method.description}",
                                parameters=method.parameters,
                                return_type=method.return_type,
                                framework=method.framework,
                                version=method.version,
                                is_inherited=True,
                                parent_class=parent_class
                            )
                            methods.append(inherited_method)
        
        return methods
    
    def save_framework_methods_config(self, config_path: str = "framework_methods.json"):
        """保存框架方法配置到文件"""
        try:
            # 转换FrameworkMethod对象为字典
            serializable_methods = {}
            for framework, classes in self.framework_methods.items():
                serializable_methods[framework] = {}
                for class_name, methods in classes.items():
                    serializable_methods[framework][class_name] = [
                        {
                            "method_name": m.method_name,
                            "class_name": m.class_name,
                            "package": m.package,
                            "description": m.description,
                            "parameters": m.parameters,
                            "return_type": m.return_type,
                            "framework": m.framework,
                            "version": m.version,
                            "is_inherited": m.is_inherited,
                            "parent_class": m.parent_class
                        } for m in methods
                    ]
            
            config_data = {
                "framework_methods": serializable_methods,
                "inheritance_chains": self.inheritance_chains,
                "interface_implementations": self.interface_implementations
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 框架方法配置已保存到: {config_path}")
            
        except Exception as e:
            logger.error(f"保存框架方法配置失败: {e}")


# 使用示例
def test_jar_method_resolver():
    """测试JAR方法推理器"""
    resolver = JarMethodResolver()
    
    # 测试MyBatis-Plus方法推理
    context = {
        'class_hierarchy': {
            'MaterialConfigServiceImpl': {
                'parent': 'BaseServiceImpl',
                'interfaces': ['MaterialConfigService']
            }
        },
        'imports': ['com.baomidou.mybatisplus.service.impl.ServiceImpl']
    }
    
    # 测试insertOrUpdate方法
    method = resolver.resolve_method('MaterialConfigServiceImpl', 'insertOrUpdate', context)
    if method:
        print(f"✅ 推理成功: {method.class_name}.{method.method_name}")
        print(f"   框架: {method.framework}")
        print(f"   描述: {method.description}")
        print(f"   继承自: {method.parent_class}")
    else:
        print("❌ 推理失败")
    
    # 保存配置
    resolver.save_framework_methods_config()


if __name__ == "__main__":
    test_jar_method_resolver()