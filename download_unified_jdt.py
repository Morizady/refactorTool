#!/usr/bin/env python3
"""
下载统一来源的JDT 3.13依赖包，避免签名冲突
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

def download_eclipse_2018_12_jdt():
    """下载Eclipse 2018-12 (4.10) 版本的统一JDT依赖"""
    print("📦 下载Eclipse 2018-12统一JDT依赖...")
    
    lib_dir = clean_jdt_directory()
    
    # Eclipse 2018-12 (4.10) 版本的统一依赖
    # 这个版本的所有JAR包都有相同的签名
    eclipse_version = "2018-12"
    base_url = "https://download.eclipse.org/eclipse/downloads/drops4/R-4.10-201812060815"
    
    # 核心JDT依赖 - 来自同一个Eclipse发布
    dependencies = [
        {
            "name": "org.eclipse.jdt.core_3.16.0.v20181130-1748.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/3.16.0/org.eclipse.jdt.core-3.16.0.jar",
            "local_name": "org.eclipse.jdt.core.jar"
        },
        {
            "name": "org.eclipse.core.runtime_3.15.100.v20180817-1401.jar", 
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.runtime/3.15.100/org.eclipse.core.runtime-3.15.100.jar",
            "local_name": "org.eclipse.core.runtime.jar"
        },
        {
            "name": "org.eclipse.core.resources_3.13.200.v20181028-1938.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.resources/3.13.200/org.eclipse.core.resources-3.13.200.jar", 
            "local_name": "org.eclipse.core.resources.jar"
        },
        {
            "name": "org.eclipse.equinox.common_3.10.200.v20181021-1645.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.equinox.common/3.10.200/org.eclipse.equinox.common-3.10.200.jar",
            "local_name": "org.eclipse.equinox.common.jar"
        },
        {
            "name": "org.eclipse.core.jobs_3.10.200.v20180817-1401.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.jobs/3.10.200/org.eclipse.core.jobs-3.10.200.jar",
            "local_name": "org.eclipse.core.jobs.jar"
        },
        {
            "name": "org.eclipse.osgi_3.13.300.v20181030-1125.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.osgi/3.13.300/org.eclipse.osgi-3.13.300.jar",
            "local_name": "org.eclipse.osgi.jar"
        },
        {
            "name": "org.eclipse.text_3.8.100.v20180817-1401.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.text/3.8.100/org.eclipse.text-3.8.100.jar",
            "local_name": "org.eclipse.text.jar"
        },
        {
            "name": "org.eclipse.core.expressions_3.6.200.v20180817-1401.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.expressions/3.6.200/org.eclipse.core.expressions-3.6.200.jar",
            "local_name": "org.eclipse.core.expressions.jar"
        },
        {
            "name": "org.eclipse.core.filesystem_1.7.200.v20180817-1401.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.filesystem/1.7.200/org.eclipse.core.filesystem-1.7.200.jar",
            "local_name": "org.eclipse.core.filesystem.jar"
        },
        {
            "name": "org.eclipse.core.contenttype_3.7.200.v20180817-1401.jar",
            "url": f"https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.contenttype/3.7.200/org.eclipse.core.contenttype-3.7.200.jar",
            "local_name": "org.eclipse.core.contenttype.jar"
        }
    ]
    
    success_count = 0
    total_size = 0
    
    for dep in dependencies:
        jar_path = lib_dir / dep["local_name"]
        
        try:
            print(f"📥 下载 {dep['local_name']}...")
            print(f"📍 URL: {dep['url']}")
            
            urllib.request.urlretrieve(dep["url"], jar_path)
            
            if jar_path.exists() and jar_path.stat().st_size > 10000:  # 至少10KB
                size_kb = jar_path.stat().st_size / 1024
                total_size += jar_path.stat().st_size
                print(f"✅ {dep['local_name']} 下载成功: {size_kb:.1f}KB")
                success_count += 1
            else:
                print(f"❌ {dep['local_name']} 下载失败或文件损坏")
                
        except Exception as e:
            print(f"❌ 下载 {dep['local_name']} 失败: {e}")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"\n📊 下载结果: {success_count}/{len(dependencies)} 成功")
    print(f"📦 总大小: {total_size_mb:.1f}MB")
    
    return success_count == len(dependencies)

def download_minimal_jdt():
    """下载最小化的JDT依赖（仅核心包）"""
    print("\n🔄 尝试下载最小化JDT依赖...")
    
    lib_dir = clean_jdt_directory()
    
    # 仅下载JDT核心包
    jdt_core_url = "https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/3.16.0/org.eclipse.jdt.core-3.16.0.jar"
    jdt_jar_path = lib_dir / "org.eclipse.jdt.core.jar"
    
    try:
        print(f"📥 下载JDT Core 3.16.0...")
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

if __name__ == "__main__":
    print("🚀 统一JDT依赖下载工具")
    print("=" * 50)
    print("解决JAR包签名冲突问题")
    print()
    
    # 首先尝试下载Eclipse 2018-12的统一依赖
    if download_eclipse_2018_12_jdt():
        print("\n✅ Eclipse 2018-12统一JDT依赖下载完成！")
    else:
        print("\n⚠️ 统一依赖下载失败，尝试最小化方案...")
        
        # 尝试最小化依赖
        if download_minimal_jdt():
            print("\n✅ 最小化JDT依赖下载完成！")
        else:
            print("\n❌ 所有下载方案都失败了")
            exit(1)
    
    # 验证安装
    if verify_jdt_installation():
        print("\n🎉 JDT依赖安装验证成功！")
        print("\n💡 提示:")
        print("  - 所有JAR包来自同一个Eclipse版本，避免签名冲突")
        print("  - 可以运行 python test_jdt_environment.py 测试环境")
    else:
        print("\n❌ JDT依赖安装验证失败")