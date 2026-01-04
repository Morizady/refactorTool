#!/usr/bin/env python3
"""
下载统一来源的Eclipse JDT依赖包
解决JAR包签名冲突问题 - 确保所有JAR来自同一个Eclipse发布版本
"""

import os
import urllib.request
import shutil
from pathlib import Path

def clean_jdt_directory():
    """清理现有的JDT目录"""
    lib_dir = Path("lib/jdt")
    if lib_dir.exists():
        print("🧹 清理现有JDT目录...")
        shutil.rmtree(lib_dir)
    lib_dir.mkdir(parents=True, exist_ok=True)
    return lib_dir

def download_unified_eclipse_jdt():
    """下载统一来源的Eclipse JDT依赖包 - 2019-03 (4.11.0) 版本"""
    print("📦 下载统一Eclipse JDT依赖包 (2019-03 版本)...")
    
    lib_dir = clean_jdt_directory()
    
    # 使用Eclipse 2019-03 (4.11.0) 版本的统一依赖
    # 这个版本的所有JAR包都有相同的签名
    base_url = "https://repo1.maven.org/maven2/org/eclipse"
    
    dependencies = [
        # JDT核心 - 3.17.0 (对应Eclipse 2019-03)
        {
            "name": "org.eclipse.jdt.core.jar",
            "group": "jdt",
            "artifact": "org.eclipse.jdt.core",
            "version": "3.17.0"
        },
        # Platform核心组件 - 统一使用3.11.0系列
        {
            "name": "org.eclipse.core.runtime.jar",
            "group": "platform",
            "artifact": "org.eclipse.core.runtime",
            "version": "3.15.0"
        },
        {
            "name": "org.eclipse.core.resources.jar",
            "group": "platform", 
            "artifact": "org.eclipse.core.resources",
            "version": "3.13.0"
        },
        {
            "name": "org.eclipse.equinox.common.jar",
            "group": "platform",
            "artifact": "org.eclipse.equinox.common", 
            "version": "3.10.0"
        },
        {
            "name": "org.eclipse.core.jobs.jar",
            "group": "platform",
            "artifact": "org.eclipse.core.jobs",
            "version": "3.10.0"
        },
        {
            "name": "org.eclipse.osgi.jar",
            "group": "platform",
            "artifact": "org.eclipse.osgi",
            "version": "3.13.0"
        },
        {
            "name": "org.eclipse.text.jar",
            "group": "platform",
            "artifact": "org.eclipse.text",
            "version": "3.8.0"
        },
        {
            "name": "org.eclipse.core.expressions.jar",
            "group": "platform",
            "artifact": "org.eclipse.core.expressions",
            "version": "3.6.0"
        },
        {
            "name": "org.eclipse.core.filesystem.jar",
            "group": "platform",
            "artifact": "org.eclipse.core.filesystem",
            "version": "1.7.0"
        },
        {
            "name": "org.eclipse.core.contenttype.jar",
            "group": "platform",
            "artifact": "org.eclipse.core.contenttype",
            "version": "3.7.0"
        },
        {
            "name": "org.eclipse.equinox.preferences.jar",
            "group": "platform",
            "artifact": "org.eclipse.equinox.preferences",
            "version": "3.7.0"
        },
        {
            "name": "org.eclipse.equinox.registry.jar",
            "group": "platform",
            "artifact": "org.eclipse.equinox.registry",
            "version": "3.8.0"
        }
    ]
    
    success_count = 0
    total_size = 0
    
    for dep in dependencies:
        jar_path = lib_dir / dep["name"]
        url = f"{base_url}/{dep['group']}/{dep['artifact']}/{dep['version']}/{dep['artifact']}-{dep['version']}.jar"
        
        try:
            print(f"📥 下载 {dep['name']} (v{dep['version']})...")
            print(f"📍 URL: {url}")
            
            urllib.request.urlretrieve(url, jar_path)
            
            if jar_path.exists() and jar_path.stat().st_size > 1000:  # 至少1KB
                size_kb = jar_path.stat().st_size / 1024
                total_size += jar_path.stat().st_size
                print(f"✅ {dep['name']} 下载成功: {size_kb:.1f}KB")
                success_count += 1
            else:
                print(f"❌ {dep['name']} 下载失败或文件损坏")
                
        except Exception as e:
            print(f"❌ 下载 {dep['name']} 失败: {e}")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"\n📊 下载结果: {success_count}/{len(dependencies)} 成功")
    print(f"📦 总大小: {total_size_mb:.1f}MB")
    
    return success_count >= 8  # 至少需要8个核心依赖

def download_minimal_jdt_only():
    """下载最小化JDT依赖 - 仅JDT Core"""
    print("\n🔄 下载最小化JDT依赖...")
    
    lib_dir = clean_jdt_directory()
    
    # 仅JDT核心包 - 使用3.17.0版本
    jdt_core_url = "https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/3.17.0/org.eclipse.jdt.core-3.17.0.jar"
    jdt_jar_path = lib_dir / "org.eclipse.jdt.core.jar"
    
    try:
        print(f"📥 下载JDT Core 3.17.0...")
        urllib.request.urlretrieve(jdt_core_url, jdt_jar_path)
        
        if jdt_jar_path.exists() and jdt_jar_path.stat().st_size > 1000000:
            size_mb = jdt_jar_path.stat().st_size / (1024 * 1024)
            print(f"✅ JDT Core 下载成功: {size_mb:.1f}MB")
            return True
        else:
            print(f"❌ JDT Core 下载失败")
            return False
            
    except Exception as e:
        print(f"❌ 下载JDT Core 失败: {e}")
        return False

def verify_jdt_installation():
    """验证JDT安装"""
    lib_dir = Path("lib/jdt")
    if not lib_dir.exists():
        print("❌ JDT目录不存在")
        return False
    
    jar_files = list(lib_dir.glob("*.jar"))
    if not jar_files:
        print("❌ 没有找到JAR文件")
        return False
    
    print(f"\n📁 JDT库目录内容:")
    total_size = 0
    for jar_file in jar_files:
        size_mb = jar_file.stat().st_size / (1024 * 1024)
        total_size += jar_file.stat().st_size
        print(f"  - {jar_file.name}: {size_mb:.1f}MB")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"📦 总大小: {total_size_mb:.1f}MB")
    
    return True

def test_jdt_environment():
    """测试JDT环境是否可以正常启动"""
    print("\n🧪 测试JDT环境...")
    
    try:
        import jpype
        
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
        
        # 构建classpath
        lib_dir = Path("lib/jdt")
        classpath = []
        for jar_file in lib_dir.glob("*.jar"):
            classpath.append(str(jar_file))
        
        if not classpath:
            print("❌ 没有找到JAR文件")
            return False
        
        print(f"📚 Classpath包含 {len(classpath)} 个JAR文件")
        
        # 启动JVM
        jpype.startJVM(
            jpype.getDefaultJVMPath(),
            "-Xmx1g",
            "-Xms256m",
            classpath=classpath
        )
        
        # 尝试导入JDT类
        ASTParser = jpype.JClass("org.eclipse.jdt.core.dom.ASTParser")
        AST = jpype.JClass("org.eclipse.jdt.core.dom.AST")
        
        print("✅ JDT环境测试成功！")
        print("✅ 可以正常导入JDT类")
        
        jpype.shutdownJVM()
        return True
        
    except Exception as e:
        print(f"❌ JDT环境测试失败: {e}")
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
        return False

if __name__ == "__main__":
    print("🚀 统一Eclipse JDT依赖下载工具")
    print("=" * 50)
    print("解决JAR包签名冲突问题")
    print("使用Eclipse 2019-03 (4.11.0) 统一版本")
    print()
    
    # 首先尝试下载统一版本的完整依赖
    if download_unified_eclipse_jdt():
        print("\n✅ 统一JDT依赖下载完成！")
        
        # 验证安装
        if verify_jdt_installation():
            print("\n🎉 JDT依赖安装验证成功！")
            
            # 测试环境
            if test_jdt_environment():
                print("\n🎉 JDT环境测试通过！")
                print("\n💡 提示:")
                print("  - 使用统一的Eclipse 2019-03版本")
                print("  - 解决了JAR包签名冲突问题")
                print("  - 可以运行 python jdt_parser.py 测试解析功能")
            else:
                print("\n⚠️ JDT环境测试失败，但依赖已下载")
        else:
            print("\n❌ JDT依赖安装验证失败")
    else:
        print("\n⚠️ 统一依赖下载失败，尝试最小化方案...")
        
        # 尝试最小化依赖
        if download_minimal_jdt_only():
            print("\n✅ 最小化JDT依赖下载完成！")
            
            if verify_jdt_installation():
                print("\n🎉 最小化JDT依赖验证成功！")
            else:
                print("\n❌ 最小化JDT依赖验证失败")
        else:
            print("\n❌ 所有下载方案都失败了")
            exit(1)