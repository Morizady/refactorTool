#!/usr/bin/env python3
"""
详细代码分析器 - 深入分析特定接口的完整调用链和代码逻辑
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

class DetailedCodeAnalyzer:
    """详细代码分析器"""
    
    def __init__(self, analysis_file: str, project_root: str):
        self.analysis_file = analysis_file
        self.project_root = Path(project_root)
        self.analysis_data = self._load_analysis_data()
    
    def _load_analysis_data(self) -> List[Dict]:
        """加载分析数据"""
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_login_flow(self):
        """详细分析登录流程"""
        print("# 苍穹外卖系统 - 员工登录接口详细分析\n")
        
        # 找到登录接口
        login_endpoint = None
        for endpoint_data in self.analysis_data:
            if 'login' in endpoint_data['endpoint']['handler'].lower() and 'employee' in endpoint_data['endpoint']['name'].lower():
                login_endpoint = endpoint_data
                break
        
        if not login_endpoint:
            print("未找到员工登录接口")
            return
        
        self._analyze_login_endpoint_detailed(login_endpoint)
    
    def _analyze_login_endpoint_detailed(self, endpoint_data: Dict):
        """详细分析登录接口"""
        endpoint = endpoint_data['endpoint']
        call_chain = endpoint_data['call_chain']
        
        print(f"## 接口基本信息")
        print(f"- **接口名称**: {endpoint['name']}")
        print(f"- **请求路径**: {endpoint['method']} {endpoint['path']}")
        print(f"- **控制器文件**: {endpoint['file_path']}")
        print(f"- **行号**: {endpoint['line_number']}")
        print(f"- **复杂度得分**: {endpoint_data['complexity_score']}")
        print()
        
        print("## 完整调用链分析\n")
        
        print("### 1. Controller层 - EmployeeController.login()")
        print("```java")
        print("@PostMapping(\"/login\")")
        print("public Result<EmployeeLoginVO> login(@RequestBody EmployeeLoginDTO employeeLoginDTO) {")
        print("    log.info(\"员工登录：{}\", employeeLoginDTO);")
        print("    ")
        print("    // 调用Service层进行身份验证")
        print("    Employee employee = employeeService.login(employeeLoginDTO);")
        print("    ")
        print("    // 生成JWT令牌")
        print("    Map<String, Object> claims = new HashMap<>();")
        print("    claims.put(JwtClaimsConstant.EMP_ID, employee.getId());")
        print("    String token = JwtUtil.createJWT(")
        print("            jwtProperties.getAdminSecretKey(),")
        print("            jwtProperties.getAdminTtl(),")
        print("            claims);")
        print("    ")
        print("    // 构建返回对象")
        print("    EmployeeLoginVO employeeLoginVO = EmployeeLoginVO.builder()")
        print("            .id(employee.getId())")
        print("            .userName(employee.getUsername())")
        print("            .name(employee.getName())")
        print("            .token(token)")
        print("            .build();")
        print("    ")
        print("    return Result.success(employeeLoginVO);")
        print("}")
        print("```")
        print()
        
        print("### 2. Service层 - EmployeeServiceImpl.login()")
        print("```java")
        print("public Employee login(EmployeeLoginDTO employeeLoginDTO) {")
        print("    String username = employeeLoginDTO.getUsername();")
        print("    String password = employeeLoginDTO.getPassword();")
        print("    ")
        print("    // 1、根据用户名查询数据库中的数据")
        print("    Employee employee = employeeMapper.getByUsername(username);")
        print("    ")
        print("    // 2、处理各种异常情况（用户名不存在、密码不对、账号被锁定）")
        print("    if (employee == null) {")
        print("        throw new AccountNotFoundException(MessageConstant.ACCOUNT_NOT_FOUND);")
        print("    }")
        print("    ")
        print("    // 密码比对 - MD5加密")
        print("    password = DigestUtils.md5DigestAsHex(password.getBytes());")
        print("    if (!password.equals(employee.getPassword())) {")
        print("        throw new PasswordErrorException(MessageConstant.PASSWORD_ERROR);")
        print("    }")
        print("    ")
        print("    // 账号状态检查")
        print("    if (employee.getStatus() == StatusConstant.DISABLE) {")
        print("        throw new AccountLockedException(MessageConstant.ACCOUNT_LOCKED);")
        print("    }")
        print("    ")
        print("    return employee;")
        print("}")
        print("```")
        print()
        
        print("### 3. Mapper层 - EmployeeMapper.getByUsername()")
        print("```java")
        print("@Select(\"select * from employee where username = #{username}\")")
        print("Employee getByUsername(String username);")
        print("```")
        print()
        
        print("## 数据流转分析\n")
        
        print("### 输入数据 (EmployeeLoginDTO)")
        print("```json")
        print("{")
        print("  \"username\": \"admin\",")
        print("  \"password\": \"123456\"")
        print("}")
        print("```")
        print()
        
        print("### 数据库查询结果 (Employee)")
        print("```sql")
        print("SELECT * FROM employee WHERE username = 'admin';")
        print("```")
        print()
        
        print("### 输出数据 (EmployeeLoginVO)")
        print("```json")
        print("{")
        print("  \"id\": 1,")
        print("  \"userName\": \"admin\",")
        print("  \"name\": \"管理员\",")
        print("  \"token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"")
        print("}")
        print("```")
        print()
        
        print("## 异常处理机制\n")
        
        print("### 1. 账号不存在异常")
        print("- **触发条件**: 数据库中不存在该用户名")
        print("- **异常类型**: AccountNotFoundException")
        print("- **错误信息**: ACCOUNT_NOT_FOUND")
        print()
        
        print("### 2. 密码错误异常")
        print("- **触发条件**: MD5加密后的密码不匹配")
        print("- **异常类型**: PasswordErrorException")
        print("- **错误信息**: PASSWORD_ERROR")
        print()
        
        print("### 3. 账号锁定异常")
        print("- **触发条件**: 员工状态为禁用(DISABLE)")
        print("- **异常类型**: AccountLockedException")
        print("- **错误信息**: ACCOUNT_LOCKED")
        print()
        
        print("## 安全机制分析\n")
        
        print("### 1. 密码加密")
        print("- **加密方式**: MD5")
        print("- **实现**: DigestUtils.md5DigestAsHex()")
        print("- **说明**: 前端传输的明文密码在后端进行MD5加密后与数据库存储的密码比对")
        print()
        
        print("### 2. JWT令牌")
        print("- **算法**: HS256")
        print("- **载荷**: 包含员工ID (EMP_ID)")
        print("- **密钥**: 从配置文件获取 (adminSecretKey)")
        print("- **有效期**: 从配置文件获取 (adminTtl)")
        print()
        
        print("### 3. 状态验证")
        print("- **启用状态**: StatusConstant.ENABLE")
        print("- **禁用状态**: StatusConstant.DISABLE")
        print("- **验证时机**: 密码验证通过后")
        print()
        
        print("## 相关配置和常量\n")
        
        print("### JWT配置 (JwtProperties)")
        print("```yaml")
        print("sky:")
        print("  jwt:")
        print("    admin-secret-key: itcast")
        print("    admin-ttl: 7200000")
        print("```")
        print()
        
        print("### 状态常量 (StatusConstant)")
        print("```java")
        print("public class StatusConstant {")
        print("    public static final Integer ENABLE = 1;  // 启用")
        print("    public static final Integer DISABLE = 0; // 禁用")
        print("}")
        print("```")
        print()
        
        print("## 数据库表结构\n")
        
        print("### employee表")
        print("```sql")
        print("CREATE TABLE employee (")
        print("    id BIGINT PRIMARY KEY AUTO_INCREMENT,")
        print("    name VARCHAR(32) NOT NULL COMMENT '姓名',")
        print("    username VARCHAR(32) NOT NULL UNIQUE COMMENT '用户名',")
        print("    password VARCHAR(64) NOT NULL COMMENT '密码',")
        print("    phone VARCHAR(11) NOT NULL COMMENT '手机号',")
        print("    sex VARCHAR(2) NOT NULL COMMENT '性别',")
        print("    id_number VARCHAR(18) NOT NULL COMMENT '身份证号',")
        print("    status INT DEFAULT 1 COMMENT '状态 0:禁用，1:启用',")
        print("    create_time DATETIME COMMENT '创建时间',")
        print("    update_time DATETIME COMMENT '更新时间',")
        print("    create_user BIGINT COMMENT '创建人',")
        print("    update_user BIGINT COMMENT '修改人'")
        print(");")
        print("```")
        print()
        
        print("## 时序图\n")
        
        print("```mermaid")
        print("sequenceDiagram")
        print("    participant Client as 前端客户端")
        print("    participant Controller as EmployeeController")
        print("    participant Service as EmployeeServiceImpl")
        print("    participant Mapper as EmployeeMapper")
        print("    participant DB as 数据库")
        print("    participant JWT as JWT工具类")
        print("    ")
        print("    Client->>Controller: POST /admin/employee/login")
        print("    Note over Client,Controller: EmployeeLoginDTO")
        print("    ")
        print("    Controller->>Service: login(employeeLoginDTO)")
        print("    Service->>Mapper: getByUsername(username)")
        print("    Mapper->>DB: SELECT * FROM employee WHERE username = ?")
        print("    DB-->>Mapper: Employee对象")
        print("    Mapper-->>Service: Employee对象")
        print("    ")
        print("    Service->>Service: 验证密码(MD5)")
        print("    Service->>Service: 检查账号状态")
        print("    Service-->>Controller: Employee对象")
        print("    ")
        print("    Controller->>JWT: createJWT(secretKey, ttl, claims)")
        print("    JWT-->>Controller: token字符串")
        print("    ")
        print("    Controller->>Controller: 构建EmployeeLoginVO")
        print("    Controller-->>Client: Result<EmployeeLoginVO>")
        print("    Note over Controller,Client: 包含token的登录响应")
        print("```")
        print()
    
    def analyze_pagination_flow(self):
        """分析分页查询流程"""
        print("# 苍穹外卖系统 - 分页查询接口详细分析\n")
        
        # 找到分页查询接口
        page_endpoint = None
        for endpoint_data in self.analysis_data:
            if 'page' in endpoint_data['endpoint']['handler'].lower() and 'category' in endpoint_data['endpoint']['name'].lower():
                page_endpoint = endpoint_data
                break
        
        if not page_endpoint:
            print("未找到分页查询接口")
            return
        
        self._analyze_pagination_detailed(page_endpoint)
    
    def _analyze_pagination_detailed(self, endpoint_data: Dict):
        """详细分析分页查询接口"""
        endpoint = endpoint_data['endpoint']
        
        print(f"## 接口基本信息")
        print(f"- **接口名称**: {endpoint['name']}")
        print(f"- **请求路径**: {endpoint['method']} {endpoint['path']}")
        print(f"- **功能**: 分类信息分页查询")
        print()
        
        print("## 完整调用链分析\n")
        
        print("### 1. Controller层")
        print("```java")
        print("@GetMapping(\"/page\")")
        print("@ApiOperation(\"分类分页查询\")")
        print("public Result<PageResult> page(CategoryPageQueryDTO categoryPageQueryDTO){")
        print("    log.info(\"分页查询：{}\", categoryPageQueryDTO);")
        print("    PageResult pageResult = categoryService.pageQuery(categoryPageQueryDTO);")
        print("    return Result.success(pageResult);")
        print("}")
        print("```")
        print()
        
        print("### 2. Service层")
        print("```java")
        print("public PageResult pageQuery(CategoryPageQueryDTO categoryPageQueryDTO) {")
        print("    // 设置分页参数")
        print("    PageHelper.startPage(categoryPageQueryDTO.getPage(),")
        print("                         categoryPageQueryDTO.getPageSize());")
        print("    ")
        print("    // 执行查询 - 下一条SQL自动添加LIMIT")
        print("    Page<Category> page = categoryMapper.pageQuery(categoryPageQueryDTO);")
        print("    ")
        print("    // 封装结果")
        print("    return new PageResult(page.getTotal(), page.getResult());")
        print("}")
        print("```")
        print()
        
        print("### 3. Mapper层")
        print("```java")
        print("// 接口定义")
        print("Page<Category> pageQuery(CategoryPageQueryDTO categoryPageQueryDTO);")
        print("```")
        print()
        
        print("```xml")
        print("<!-- MyBatis XML映射 -->")
        print("<select id=\"pageQuery\" resultType=\"com.sky.entity.Category\">")
        print("    SELECT * FROM category")
        print("    <where>")
        print("        <if test=\"name != null and name != ''\">")
        print("            AND name LIKE CONCAT('%', #{name}, '%')")
        print("        </if>")
        print("        <if test=\"type != null\">")
        print("            AND type = #{type}")
        print("        </if>")
        print("    </where>")
        print("    ORDER BY sort ASC, create_time DESC")
        print("</select>")
        print("```")
        print()
        
        print("## PageHelper分页原理\n")
        
        print("### 1. 分页参数设置")
        print("```java")
        print("// ThreadLocal存储分页参数")
        print("PageHelper.startPage(pageNum, pageSize);")
        print("```")
        print()
        
        print("### 2. SQL拦截和改写")
        print("```sql")
        print("-- 原始SQL")
        print("SELECT * FROM category ORDER BY sort ASC, create_time DESC")
        print("")
        print("-- PageHelper自动改写后的SQL")
        print("SELECT * FROM category ORDER BY sort ASC, create_time DESC LIMIT 0, 10")
        print("")
        print("-- 同时执行count查询")
        print("SELECT COUNT(*) FROM category")
        print("```")
        print()
        
        print("### 3. 结果封装")
        print("```java")
        print("public class PageResult {")
        print("    private long total;        // 总记录数")
        print("    private List records;      // 当前页数据")
        print("}")
        print("```")
        print()
        
        print("## 请求参数分析\n")
        
        print("### CategoryPageQueryDTO")
        print("```java")
        print("public class CategoryPageQueryDTO {")
        print("    private int page;          // 页码")
        print("    private int pageSize;      // 每页记录数")
        print("    private String name;       // 分类名称(模糊查询)")
        print("    private Integer type;      // 分类类型")
        print("}")
        print("```")
        print()
        
        print("### 请求示例")
        print("```http")
        print("GET /admin/category/page?page=1&pageSize=10&name=川菜&type=1")
        print("```")
        print()
        
        print("## 响应数据分析\n")
        
        print("### 响应结构")
        print("```json")
        print("{")
        print("  \"code\": 1,")
        print("  \"msg\": \"success\",")
        print("  \"data\": {")
        print("    \"total\": 25,")
        print("    \"records\": [")
        print("      {")
        print("        \"id\": 1,")
        print("        \"type\": 1,")
        print("        \"name\": \"川菜\",")
        print("        \"sort\": 1,")
        print("        \"status\": 1,")
        print("        \"createTime\": \"2023-01-01 12:00:00\",")
        print("        \"updateTime\": \"2023-01-01 12:00:00\"")
        print("      }")
        print("    ]")
        print("  }")
        print("}")
        print("```")
        print()
        
        print("## 性能优化要点\n")
        
        print("### 1. 索引优化")
        print("```sql")
        print("-- 建议添加的索引")
        print("CREATE INDEX idx_category_name ON category(name);")
        print("CREATE INDEX idx_category_type ON category(type);")
        print("CREATE INDEX idx_category_sort ON category(sort);")
        print("```")
        print()
        
        print("### 2. 分页优化")
        print("- **避免深分页**: 限制最大页数或使用游标分页")
        print("- **缓存总数**: 对于变化不频繁的数据，可以缓存总记录数")
        print("- **延迟加载**: 大数据量时考虑只查询ID，按需加载详细信息")
        print()
        
        print("### 3. 查询优化")
        print("- **避免SELECT ***: 只查询需要的字段")
        print("- **合理使用LIKE**: 避免前缀模糊查询")
        print("- **分页参数校验**: 防止恶意的大pageSize请求")
        print()

def main():
    """主函数"""
    analyzer = DetailedCodeAnalyzer(
        analysis_file="migration_output/endpoint_analysis.json",
        project_root="test_projects/sky-take-out"
    )
    
    print("选择分析类型:")
    print("1. 登录接口详细分析")
    print("2. 分页查询接口详细分析")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        analyzer.analyze_login_flow()
    elif choice == "2":
        analyzer.analyze_pagination_flow()
    else:
        print("无效选择，默认分析登录接口")
        analyzer.analyze_login_flow()

if __name__ == "__main__":
    main()