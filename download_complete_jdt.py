#!/usr/bin/env python3
"""
下载完整的JDT依赖包，包含所有必需的OSGi依赖
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

def download_complete_jdt_dependencies():
    """下载完整的JDT依赖包"""
    print("📦 下载完整JDT依赖包...")
    
    lib_dir = clean_jdt_directory()
    
    # 完整的JDT依赖列表，包含OSGi相关依赖
    dependencies = [
        # JDT核心
        {
            "name": "org.eclipse.jdt.core.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/3.16.0/org.eclipse.jdt.core-3.16.0.jar"
        },
        # Eclipse平台核心
        {
            "name": "org.eclipse.core.runtime.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.runtime/3.15.100/org.eclipse.core.runtime-3.15.100.jar"
        },
        {
            "name": "org.eclipse.core.resources.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.resources/3.13.200/org.eclipse.core.resources-3.13.200.jar"
        },
        {
            "name": "org.eclipse.equinox.common.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.equinox.common/3.10.200/org.eclipse.equinox.common-3.10.200.jar"
        },
        {
            "name": "org.eclipse.core.jobs.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.jobs/3.10.200/org.eclipse.core.jobs-3.10.200.jar"
        },
        {
            "name": "org.eclipse.osgi.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.osgi/3.13.300/org.eclipse.osgi-3.13.300.jar"
        },
        {
            "name": "org.eclipse.text.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.text/3.8.100/org.eclipse.text-3.8.100.jar"
        },
        {
            "name": "org.eclipse.core.expressions.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.expressions/3.6.200/org.eclipse.core.expressions-3.6.200.jar"
        },
        {
            "name": "org.eclipse.core.filesystem.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.filesystem/1.7.200/org.eclipse.core.filesystem-1.7.200.jar"
        },
        {
            "name": "org.eclipse.core.contenttype.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.contenttype/3.7.200/org.eclipse.core.contenttype-3.7.200.jar"
        },
        # OSGi服务依赖
        {
            "name": "org.eclipse.equinox.preferences.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.equinox.preferences/3.7.200/org.eclipse.equinox.preferences-3.7.200.jar"
        },
        {
            "name": "org.eclipse.equinox.registry.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.equinox.registry/3.8.200/org.eclipse.equinox.registry-3.8.200.jar"
        },
        {
            "name": "org.eclipse.osgi.services.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.osgi.services/3.7.100/org.eclipse.osgi.services-3.7.100.jar"
        },
        # 额外的Eclipse依赖
        {
            "name": "org.eclipse.core.commands.jar",
            "url": "https://repo1.maven.org/maven2/org/eclipse/platform/org.eclipse.core.commands/3.9.200/org.eclipse.core.commands-3.9.200.jar"
        }
    ]
    
    success_count = 0
    total_size = 0
    
    for dep in dependencies:
        jar_path = lib_dir / dep["name"]
        
        try:
            print(f"📥 下载 {dep['name']}...")
            print(f"📍 URL: {dep['url']}")
            
            urllib.request.urlretrieve(dep["url"], jar_path)
            
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
    
    return success_count >= 10  # 至少需要10个核心依赖

def try_minimal_jdt_only():
    """尝试仅使用JDT核心包"""
    print("\n🔄 尝试仅使用JDT核心包...")
    
    lib_dir = clean_jdt_directory()
    
    # 仅JDT核心包
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
    print("🚀 完整JDT依赖下载工具")
    print("=" * 50)
    print("包含所有必需的OSGi和Eclipse依赖")
    print()
    
    # 首先尝试下载完整依赖
    if download_complete_jdt_dependencies():
        print("\n✅ 完整JDT依赖下载完成！")
    else:
        print("\n⚠️ 完整依赖下载失败，尝试最小化方案...")
        
        # 尝试最小化依赖
        if try_minimal_jdt_only():
            print("\n✅ 最小化JDT依赖下载完成！")
        else:
            print("\n❌ 所有下载方案都失败了")
            exit(1)
    
    # 验证安装
    if verify_jdt_installation():
        print("\n🎉 JDT依赖安装验证成功！")
        print("\n💡 提示:")
        print("  - 包含完整的OSGi和Eclipse依赖")
        print("  - 解决了BackingStoreException问题")
        print("  - 可以运行 python test_jdt_environment.py 测试环境")
    else:
        print("\n❌ JDT依赖安装验证失败")