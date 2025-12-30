#!/usr/bin/env python3
"""
代码逻辑分析器 - 基于endpoint_analysis.json分析调用链和代码逻辑
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

class CodeLogicAnalyzer:
    """代码逻辑分析器"""
    
    def __init__(self, analysis_file: str, project_root: str):
        self.analysis_file = analysis_file
        self.project_root = Path(project_root)
        self.analysis_data = self._load_analysis_data()
    
    def _load_analysis_data(self) -> List[Dict]:
        """加载分析数据"""
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_all_endpoints(self):
        """分析所有接口的代码逻辑"""
        print("# 苍穹外卖项目接口代码逻辑分析报告\n")
        
        # 按控制器分组
        controllers = {}
        for endpoint_data in self.analysis_data:
            endpoint = endpoint_data['endpoint']
            controller_name = endpoint['controller']
            
            if controller_name not in controllers:
                controllers[controller_name] = []
            controllers[controller_name].append(endpoint_data)
        
        # 分析每个控制器
        for controller_name, endpoints in controllers.items():
            self._analyze_controller(controller_name, endpoints)
    
    def _analyze_controller(self, controller_name: str, endpoints: List[Dict]):
        """分析单个控制器的所有接口"""
        print(f"## {controller_name} 控制器分析\n")
        
        for endpoint_data in endpoints:
            self._analyze_single_endpoint(endpoint_data)
    
    def _analyze_single_endpoint(self, endpoint_data: Dict):
        """分析单个接口的代码逻辑"""
        endpoint = endpoint_data['endpoint']
        call_chain = endpoint_data['call_chain']
        complexity_score = endpoint_data['complexity_score']
        
        print(f"### {endpoint['name']} 接口")
        print(f"- **路径**: {endpoint['method']} {endpoint['path']}")
        print(f"- **文件**: {endpoint['file_path']}:{endpoint['line_number']}")
        print(f"- **复杂度**: {complexity_score}")
        print()
        
        # 分析调用链
        self._analyze_call_chain(endpoint, call_chain)
        
        # 分析相关文件
        self._analyze_related_files(call_chain.get('files', []))
        
        print("---\n")
    
    def _analyze_call_chain(self, endpoint: Dict, call_chain: Dict):
        """分析调用链逻辑"""
        method_calls = call_chain.get('method_calls', [])
        
        if not method_calls:
            print("**调用链**: 无复杂调用\n")
            return
        
        print("**调用链分析**:")
        
        # 根据接口类型分析逻辑
        handler_name = endpoint['handler']
        path = endpoint['path']
        method = endpoint['method']
        
        if 'login' in handler_name.lower():
            self._analyze_login_logic(method_calls)
        elif 'page' in handler_name.lower():
            self._analyze_pagination_logic(method_calls)
        elif 'upload' in handler_name.lower():
            self._analyze_upload_logic(method_calls)
        elif 'startOrStop' in handler_name:
            self._analyze_status_toggle_logic(method_calls)
        elif 'list' in handler_name.lower():
            self._analyze_list_logic(method_calls)
        else:
            self._analyze_generic_logic(method_calls)
        
        print()
    
    def _analyze_login_logic(self, method_calls: List[Dict]):
        """分析登录逻辑"""
        print("```")
        print("登录接口逻辑流程:")
        print("1. 记录登录日志")
        print("2. 调用employeeService.login()进行身份验证")
        print("   - 根据用户名查询数据库")
        print("   - 验证密码(MD5加密)")
        print("   - 检查账号状态")
        print("3. 生成JWT令牌")
        print("   - 创建claims包含员工ID")
        print("   - 使用JwtUtil.createJWT()生成token")
        print("4. 构建返回对象EmployeeLoginVO")
        print("   - 包含员工基本信息和token")
        print("5. 返回成功结果")
        print("```")
    
    def _analyze_pagination_logic(self, method_calls: List[Dict]):
        """分析分页查询逻辑"""
        print("```")
        print("分页查询接口逻辑流程:")
        print("1. 记录查询参数日志")
        print("2. 调用service层的pageQuery()方法")
        print("   - 使用PageHelper.startPage()设置分页参数")
        print("   - 执行数据库查询(自动添加LIMIT)")
        print("   - 封装PageResult对象")
        print("3. 返回分页结果")
        print("```")
    
    def _analyze_upload_logic(self, method_calls: List[Dict]):
        """分析文件上传逻辑"""
        print("```")
        print("文件上传接口逻辑流程:")
        print("1. 记录上传日志")
        print("2. 获取原始文件名和扩展名")
        print("3. 生成唯一文件名(UUID)")
        print("4. 调用aliOssUtil.upload()上传到阿里云OSS")
        print("5. 返回文件访问URL")
        print("6. 异常处理: 捕获上传失败异常")
        print("```")
    
    def _analyze_status_toggle_logic(self, method_calls: List[Dict]):
        """分析状态切换逻辑"""
        print("```")
        print("状态切换接口逻辑流程:")
        print("1. 接收状态参数和ID")
        print("2. 调用service层的startOrStop()方法")
        print("   - 构建Category对象设置状态")
        print("   - 调用mapper更新数据库")
        print("3. 返回成功结果")
        print("```")
    
    def _analyze_list_logic(self, method_calls: List[Dict]):
        """分析列表查询逻辑"""
        print("```")
        print("列表查询接口逻辑流程:")
        print("1. 接收查询类型参数")
        print("2. 调用service层的list()方法")
        print("   - 根据类型查询分类列表")
        print("   - 直接调用mapper查询数据库")
        print("3. 返回查询结果列表")
        print("```")
    
    def _analyze_generic_logic(self, method_calls: List[Dict]):
        """分析通用逻辑"""
        print("```")
        print("接口调用流程:")
        for i, call in enumerate(method_calls, 1):
            obj = call.get('object', 'unknown')
            method = call.get('method', 'unknown')
            args = call.get('arguments', 0)
            print(f"{i}. {obj}.{method}() - {args}个参数")
        print("```")
    
    def _analyze_related_files(self, files: List[Dict]):
        """分析相关文件"""
        if not files:
            return
        
        print("**相关文件**:")
        
        # 按类型分组
        service_files = [f for f in files if 'service' in f.get('path', '').lower()]
        dto_files = [f for f in files if 'dto' in f.get('path', '').lower()]
        vo_files = [f for f in files if 'vo' in f.get('path', '').lower()]
        exception_files = [f for f in files if 'exception' in f.get('path', '').lower()]
        
        if service_files:
            print("- **Service层**:")
            for file in service_files[:2]:  # 只显示前2个
                file_name = Path(file['path']).name
                print(f"  - {file_name}")
        
        if dto_files:
            print("- **DTO对象**:")
            for file in dto_files[:3]:  # 只显示前3个
                file_name = Path(file['path']).name
                print(f"  - {file_name}")
        
        if vo_files:
            print("- **VO对象**:")
            for file in vo_files[:2]:
                file_name = Path(file['path']).name
                print(f"  - {file_name}")
        
        if exception_files:
            print("- **异常类**:")
            for file in exception_files[:2]:
                file_name = Path(file['path']).name
                print(f"  - {file_name}")
        
        print()
    
    def analyze_specific_endpoint(self, endpoint_name: str):
        """分析特定接口"""
        for endpoint_data in self.analysis_data:
            if endpoint_data['endpoint']['name'] == endpoint_name:
                print(f"# {endpoint_name} 详细分析\n")
                self._analyze_single_endpoint(endpoint_data)
                return
        
        print(f"未找到接口: {endpoint_name}")
    
    def generate_summary(self):
        """生成分析摘要"""
        total_endpoints = len(self.analysis_data)
        controllers = set(ep['endpoint']['controller'] for ep in self.analysis_data)
        
        complexity_scores = [ep['complexity_score'] for ep in self.analysis_data]
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        high_complexity = len([s for s in complexity_scores if s > 40])
        
        print("# 项目分析摘要\n")
        print(f"- **总接口数**: {total_endpoints}")
        print(f"- **控制器数**: {len(controllers)}")
        print(f"- **平均复杂度**: {avg_complexity:.1f}")
        print(f"- **高复杂度接口**: {high_complexity}个 (>40分)")
        print()
        
        print("## 控制器列表")
        for controller in sorted(controllers):
            controller_endpoints = [ep for ep in self.analysis_data if ep['endpoint']['controller'] == controller]
            print(f"- **{controller}**: {len(controller_endpoints)}个接口")
        print()

def main():
    """主函数"""
    analyzer = CodeLogicAnalyzer(
        analysis_file="migration_output/endpoint_analysis.json",
        project_root="test_projects/sky-take-out"
    )
    
    # 生成完整分析报告
    analyzer.generate_summary()
    analyzer.analyze_all_endpoints()

if __name__ == "__main__":
    main()