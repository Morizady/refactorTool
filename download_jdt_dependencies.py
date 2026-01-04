#!/usr/bin/env python3
"""
下载JDT 3.13及其完整依赖
"""

import os
import urllib.request
from pathlib import Path

def download_jdt_full_dependencies():
    """下载JDT 3.13的完整依赖"""
    print("📦 下载JDT 3.13完整依赖...")
    
    # 创建目录
    lib_dir = Path("lib/jdt")
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # JDT 3.13及其依赖的JAR文件列表
    dependencies = [
        {
            "name": "org.eclipse.jdt.core.jar",
            "group": "org.eclipse.jdt",
            "artifact": "org.eclipse.jdt.core",
            "version": "3.13.0"
        },
        {
            "name": "org.eclipse.core.runtime.jar", 
            "group": "org.eclipse.platform",
            "artifact": "org.eclipse.core.runtime",
            "version": "3.13.0"
        },
        {
            "name": "org.eclipse.core.resources.jar",
            "group": "org.eclipse.platform", 
            "artifact": "org.eclipse.core.resources",
            "version": "3.13.0"
        },
        {
            "name": "org.eclipse.equinox.common.jar",
            "group": "org.eclipse.platform",
            "artifact": "org.eclipse.equinox.common", 
            "version": "3.10.0"
        }
    ]
    
    success_count = 0
    
    for dep in dependencies:
        jar_path = lib_dir / dep["name"]
        
        # 构建Maven Central URL
        url = f"https://repo1.maven.org/maven2/{dep['group'].replace('.', '/')}/{dep['artifact']}/{dep['version']}/{dep['artifact']}-{dep['version']}.jar"
        
        try:
            print(f"📥 下载 {dep['name']}...")
            print(f"📍 URL: {url}")
            
            urllib.request.urlretrieve(url, jar_path)
            
            if jar_path.exists() and jar_path.stat().st_size > 10000:  # 至少10KB
                size_kb = jar_path.stat().st_size / 1024
                print(f"✅ {dep['name']} 下载成功: {size_kb:.1f}KB")
                success_count += 1
            else:
                print(f"❌ {dep['name']} 下载失败或文件损坏")
                
        except Exception as e:
            print(f"❌ 下载 {dep['name']} 失败: {e}")
    
    print(f"\n📊 下载结果: {success_count}/{len(dependencies)} 成功")
    return success_count == len(dependencies)

def try_alternative_jdt_version():
    """尝试下载更兼容的JDT版本"""
    print("\n🔄 尝试下载更兼容的JDT版本...")
    
    lib_dir = Path("lib/jdt")
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # 尝试JDT 3.18版本（更稳定）
    jdt_version = "3.18.0"
    jdt_url = f"https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/{jdt_version}/org.eclipse.jdt.core-{jdt_version}.jar"
    
    jdt_jar_path = lib_dir / "org.eclipse.jdt.core.jar"
    
    # 删除现有文件
    if jdt_jar_path.exists():
        jdt_jar_path.unlink()
    
    try:
        print(f"📥 下载JDT Core {jdt_version}...")
        urllib.request.urlretrieve(jdt_url, jdt_jar_path)
        
        if jdt_jar_path.exists() and jdt_jar_path.stat().st_size > 1000000:
            size_mb = jdt_jar_path.stat().st_size / (1024 * 1024)
            print(f"✅ JDT {jdt_version} 下载成功: {size_mb:.1f}MB")
            return True
        else:
            print(f"❌ JDT {jdt_version} 下载失败")
            return False
            
    except Exception as e:
        print(f"❌ 下载JDT {jdt_version} 失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 JDT完整依赖下载工具")
    print("=" * 50)
    
    # 首先尝试下载JDT 3.13的完整依赖
    if download_jdt_full_dependencies():
        print("\n✅ JDT 3.13完整依赖下载完成！")
    else:
        print("\n⚠️ JDT 3.13依赖下载不完整，尝试替代方案...")
        
        # 尝试更兼容的版本
        if try_alternative_jdt_version():
            print("\n✅ 替代JDT版本下载完成！")
        else:
            print("\n❌ 所有JDT版本下载失败")
    
    # 显示最终的JAR文件列表
    lib_dir = Path("lib/jdt")
    if lib_dir.exists():
        print(f"\n📁 JDT库目录内容:")
        for jar_file in lib_dir.glob("*.jar"):
            size_mb = jar_file.stat().st_size / (1024 * 1024)
            print(f"  - {jar_file.name}: {size_mb:.1f}MB")