"""
AI Helpers - 辅助工具函数

提供代码格式化、响应解析、日志设置等辅助功能。
"""

import re
import logging
from typing import Optional, Dict, Any, List
import json


def format_code_for_ai(code: str, 
                      language: str = "java", 
                      context: str = "",
                      max_length: int = 8000) -> str:
    """格式化代码用于AI分析
    
    Args:
        code: 源代码
        language: 编程语言
        context: 上下文信息
        max_length: 最大长度限制
        
    Returns:
        str: 格式化后的代码
    """
    formatted_parts = []
    
    # 添加上下文信息
    if context:
        formatted_parts.append(f"## 上下文信息\n{context}\n")
    
    # 添加代码块
    formatted_parts.append(f"## {language.upper()}代码\n")
    formatted_parts.append(f"```{language}")
    formatted_parts.append(code)
    formatted_parts.append("```")
    
    formatted_code = "\n".join(formatted_parts)
    
    # 长度限制
    if len(formatted_code) > max_length:
        # 截断代码但保留格式
        truncated_code = code[:max_length - 200]  # 预留格式化字符的空间
        formatted_parts = []
        
        if context:
            formatted_parts.append(f"## 上下文信息\n{context}\n")
        
        formatted_parts.append(f"## {language.upper()}代码（已截断）\n")
        formatted_parts.append(f"```{language}")
        formatted_parts.append(truncated_code)
        formatted_parts.append("\n... [代码已截断] ...")
        formatted_parts.append("```")
        
        formatted_code = "\n".join(formatted_parts)
    
    return formatted_code


def extract_code_from_response(response: str, language: str = None) -> List[str]:
    """从AI响应中提取代码块
    
    Args:
        response: AI响应文本
        language: 指定编程语言（可选）
        
    Returns:
        List[str]: 提取的代码块列表
    """
    code_blocks = []
    
    # 匹配代码块的正则表达式
    if language:
        # 匹配指定语言的代码块
        pattern = rf'```{re.escape(language)}\n(.*?)\n```'
    else:
        # 匹配所有代码块
        pattern = r'```(?:\w+)?\n(.*?)\n```'
    
    matches = re.findall(pattern, response, re.DOTALL)
    
    for match in matches:
        # 清理代码块
        cleaned_code = match.strip()
        if cleaned_code:
            code_blocks.append(cleaned_code)
    
    return code_blocks


def format_call_tree_for_ai(call_tree_data: Dict[str, Any]) -> str:
    """格式化调用树数据用于AI分析
    
    Args:
        call_tree_data: 调用树数据
        
    Returns:
        str: 格式化后的文本
    """
    formatted_parts = []
    
    # 基本信息
    if "statistics" in call_tree_data:
        stats = call_tree_data["statistics"]
        formatted_parts.append("## 调用树统计信息")
        formatted_parts.append(f"- 总调用数: {stats.get('total_calls', 0)}")
        formatted_parts.append(f"- 最大深度: {stats.get('max_depth', 0)}")
        formatted_parts.append(f"- 涉及类数: {stats.get('unique_classes', 0)}")
        formatted_parts.append("")
    
    # JAR推理信息
    if "jar_resolutions" in call_tree_data:
        jar_resolutions = call_tree_data["jar_resolutions"]
        if jar_resolutions:
            formatted_parts.append("## JAR方法推理结果")
            for resolution in jar_resolutions[:5]:  # 限制显示数量
                formatted_parts.append(f"- {resolution.get('original_call', '')} -> {resolution.get('framework', '')} 框架")
            formatted_parts.append("")
    
    # 调用链结构
    if "call_tree" in call_tree_data:
        formatted_parts.append("## 调用链结构")
        formatted_parts.append(_format_call_tree_node(call_tree_data["call_tree"], 0))
    
    return "\n".join(formatted_parts)


def _format_call_tree_node(node: Dict[str, Any], depth: int) -> str:
    """递归格式化调用树节点"""
    indent = "  " * depth
    method_name = node.get("method_name", "unknown")
    class_name = node.get("class_name", "unknown")
    call_type = node.get("call_type", "")
    
    # 构建节点描述
    node_desc = f"{indent}├── {class_name}.{method_name}()"
    
    if call_type:
        node_desc += f" [{call_type}]"
    
    result = [node_desc]
    
    # 递归处理子节点
    children = node.get("children", [])
    for child in children:
        result.append(_format_call_tree_node(child, depth + 1))
    
    return "\n".join(result)


def format_jar_resolutions_for_ai(jar_resolutions: List[Dict[str, Any]]) -> str:
    """格式化JAR推理结果用于AI分析
    
    Args:
        jar_resolutions: JAR推理结果列表
        
    Returns:
        str: 格式化后的文本
    """
    if not jar_resolutions:
        return "## JAR方法推理结果\n无推理结果"
    
    formatted_parts = ["## JAR方法推理结果"]
    
    # 按框架分组
    framework_groups = {}
    for resolution in jar_resolutions:
        framework = resolution.get("framework", "Unknown")
        if framework not in framework_groups:
            framework_groups[framework] = []
        framework_groups[framework].append(resolution)
    
    for framework, resolutions in framework_groups.items():
        formatted_parts.append(f"\n### {framework} 框架")
        for resolution in resolutions:
            original = resolution.get("original_call", "")
            resolved = resolution.get("resolved_method", "")
            description = resolution.get("description", "")
            
            formatted_parts.append(f"- **{original}**")
            formatted_parts.append(f"  - 推理结果: {resolved}")
            formatted_parts.append(f"  - 描述: {description}")
    
    return "\n".join(formatted_parts)


def setup_logging(level: str = "INFO", 
                 format_string: str = None,
                 log_file: str = None) -> logging.Logger:
    """设置日志配置
    
    Args:
        level: 日志级别
        format_string: 日志格式字符串
        log_file: 日志文件路径（可选）
        
    Returns:
        logging.Logger: 配置好的日志器
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format=format_string,
        handlers=[]
    )
    
    # 获取AI模块的日志器
    logger = logging.getLogger('ai_module')
    logger.setLevel(log_level)
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(format_string)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定了日志文件）
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(format_string)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")
    
    return logger


def parse_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """从AI响应中解析JSON数据
    
    Args:
        response: AI响应文本
        
    Returns:
        Optional[Dict[str, Any]]: 解析的JSON数据
    """
    try:
        # 尝试直接解析整个响应
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试从代码块中提取JSON
    json_pattern = r'```(?:json)?\n(.*?)\n```'
    matches = re.findall(json_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # 尝试查找JSON对象
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, response)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_response_text(text: str) -> str:
    """清理AI响应文本
    
    Args:
        text: 原始响应文本
        
    Returns:
        str: 清理后的文本
    """
    # 移除多余的空白字符
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # 移除行首行尾空白
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 移除首尾空白
    text = text.strip()
    
    return text