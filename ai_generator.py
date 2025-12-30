#!/usr/bin/env python3
"""
AI代码生成器 - 使用OpenAI API生成迁移代码
"""

import json
import re
from typing import Dict, List, Optional
import openai
from openai import OpenAI

class AIGenerator:
    """AI代码生成器"""
    
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
        self.model = model
        
        # 初始化OpenAI客户端
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            # 尝试从环境变量获取
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("需要提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
            self.client = OpenAI(api_key=api_key)
    
    def generate_migration_code(self, migration_context: Dict) -> Dict:
        """生成迁移代码"""
        # 构建提示词
        prompt = self._build_migration_prompt(migration_context)
        
        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            generated_content = response.choices[0].message.content
            
            # 解析生成的内容
            return self._parse_generated_content(generated_content)
            
        except Exception as e:
            return {
                "error": str(e),
                "raw_prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt
            }
    
    def _get_system_prompt(self) -> str:
        """系统提示词"""
        return """你是一个专业的代码迁移专家，擅长将旧系统代码迁移到新系统。
        新系统的技术栈是：Spring Boot + MyBatis Plus + 统一响应格式。
        
        请遵循以下规范：
        1. 使用新系统的命名规范（驼峰式）
        2. 使用新的包结构（com.newproject.*）
        3. 使用MyBatis Plus代替传统MyBatis
        4. 所有Controller方法返回统一的Response对象
        5. 使用新的字段命名（如：userId -> user_id，createTime -> created_at）
        6. 添加合适的日志和异常处理
        7. 遵循RESTful API设计规范
        
        请分析旧代码的逻辑，生成符合新系统规范的可运行代码。"""
    
    def _build_migration_prompt(self, context: Dict) -> str:
        """构建迁移提示词"""
        old_endpoint = context.get("old_endpoint", {})
        new_endpoint = context.get("new_endpoint", {})
        call_chain = context.get("call_chain", {})
        sql_mappings = context.get("sql_mappings", [])
        
        prompt = f"""
# 代码迁移任务

## 旧接口信息
- 路径: {old_endpoint.get('path', 'N/A')}
- 方法: {old_endpoint.get('method', 'N/A')}
- 控制器: {old_endpoint.get('controller', 'N/A')}
- 处理方法: {old_endpoint.get('handler', 'N/A')}
- 文件: {old_endpoint.get('file_path', 'N/A')}

## 新接口信息（目标）
- 路径: {new_endpoint.get('path', 'N/A')}
- 方法: {new_endpoint.get('method', 'N/A')}
- 控制器: {new_endpoint.get('controller', 'N/A')}
- 处理方法: {new_endpoint.get('handler', 'N/A')}

## 旧接口调用链分析
{json.dumps(call_chain, indent=2, ensure_ascii=False)}

## SQL映射信息
{json.dumps(sql_mappings, indent=2, ensure_ascii=False)}

## 相关文件内容（最多显示3个）
"""
        
        # 添加相关文件内容
        related_files = context.get("migration_context", {}).get("related_files", [])
        for i, file_info in enumerate(related_files[:3]):  # 限制数量避免token超限
            prompt += f"\n### 文件: {file_info.get('path', 'N/A')}\n"
            prompt += f"```\n{file_info.get('content', '')[:1000]}\n```\n"
        
        prompt += """
## 迁移要求
1. 分析旧接口的业务逻辑
2. 生成新接口的完整实现代码
3. 包括Controller、Service、Mapper（MyBatis Plus风格）
4. 注意字段名称的映射（参考新旧表结构映射）
5. 添加必要的参数校验和异常处理
6. 生成可编译的完整代码片段

请生成新接口的完整代码实现，包括：
1. Controller类和方法
2. Service接口和实现
3. Mapper接口（MyBatis Plus）
4. 必要的DTO和VO类
5. 字段映射说明

请用以下格式输出：
```json
{
  "controller_code": "...",
  "service_interface_code": "...",
  "service_impl_code": "...",
  "mapper_code": "...",
  "dto_code": "...",
  "vo_code": "...",
  "field_mappings": {
    "old_field": "new_field",
    ...
  },
  "notes": "迁移说明和建议"
}
```
"""
        return prompt

    def _parse_generated_content(self, content: str) -> Dict:
        """解析AI生成的内容"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # 如果没有找到JSON标记，尝试直接解析
            return json.loads(content)
            
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回原始内容
            return {
                "raw_output": content,
                "note": "AI响应格式不符合预期，请手动处理"
            }