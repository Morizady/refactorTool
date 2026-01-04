#!/usr/bin/env python3
"""
下载JDT 3.13完整依赖包
"""

import os
import urllib.request
from pathlib import Path

def download_jdt_complete_dependencies():
    """下载JDT 3.13的完整依赖包"""
    print("📦 下载JDT 3.13完整依赖包...")
    
    # 创建目录
    lib_dir = Path("lib/jdt")
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # JDT 3.13完整依赖列表
    JDT_DEPS_8 = {
        "org.eclipse.jdt.core": "3.13.0",
        "org.eclipse.core.resources": "3.13.0", 
        "org.eclipse.core.runtime": "3.13.0",
        "org.eclipse.core.jobs": "3.10.0",
        "org.eclipse.equinox.common": "3.10.0",
        "org.eclipse.osgi": "3.13.0",
        "org.eclipse.text": "3.10.0",
        "org.eclipse.core.expressions": "3.6.0",
        "org.eclipse.core.filesystem": "1.7.0",
        "org.eclipse.core.contenttype": "3.7.0"
    }
    
    # Maven组映射
    group_mappings = {
        "org.eclipse.jdt.core": "org.eclipse.jdt",
        "org.eclipse.core.resources": "org.eclipse.platform",
        "org.eclipse.core.runtime": "org.eclipse.platform", 
        "org.eclipse.core.jobs": "org.eclipse.platform",
        "org.eclipse.equinox.common": "org.eclipse.platform",
        "org.eclipse.osgi": "org.eclipse.platform",
        "org.eclipse.text": "org.eclipse.platform",
        "org.eclipse.core.expressions": "org.eclipse.platform",
        "org.eclipse.core.filesystem": "org.eclipse.platform",
        "org.eclipse.core.contenttype": "org.eclipse.platform"
    }
    
    success_count = 0
    total_count = len(JDT_DEPS_8)
    
    print(f"📋 需要下载 {total_count} 个依赖包")
    print("=" * 60)
    
    for artifact, version in JDT_DEPS_8.items():
        jar_name = f"{artifact}.jar"
        jar_path = lib_dir / jar_name
        
        # 获取Maven组ID
        group_id = group_mappings.get(artifact, "org.eclipse.platform")
        
        # 构建Maven Central URL
        url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.jar"
        
        try:
            print(f"📥 下载 {jar_name} (版本 {version})...")
            print(f"📍 URL: {url}")
            
            # 如果文件已存在且大小合理，跳过下载
            if jar_path.exists() and jar_path.stat().st_size > 1000:
                size_kb = jar_path.stat().st_size / 1024
                print(f"⏭️  {jar_name} 已存在: {size_kb:.1f}KB")
                success_count += 1
                continue
            
            urllib.request.urlretrieve(url, jar_path)
            
            if jar_path.exists() and jar_path.stat().st_size > 1000:  # 至少1KB
                size_kb = jar_path.stat().st_size / 1024
                if size_kb > 1024:
                    size_str = f"{size_kb/1024:.1f}MB"
                else:
                    size_str = f"{size_kb:.1f}KB"
                print(f"✅ {jar_name} 下载成功: {size_str}")
                success_count += 1
            else:
                print(f"❌ {jar_name} 下载失败或文件损坏")
                
        except Exception as e:
            print(f"❌ 下载 {jar_name} 失败: {e}")
        
        print("-" * 40)
    
    print(f"\n📊 下载结果: {success_count}/{total_count} 成功")
    return success_count >= 8  # 至少需要8个核心依赖

def list_downloaded_jars():
    """列出已下载的JAR文件"""
    lib_dir = Path("lib/jdt")
    
    if not lib_dir.exists():
        print("❌ JDT库目录不存在")
        return
    
    jar_files = list(lib_dir.glob("*.jar"))
    
    if not jar_files:
        print("❌ 未找到JAR文件")
        return
    
    print(f"\n📁 JDT库目录内容 ({len(jar_files)} 个文件):")
    print("=" * 50)
    
    total_size = 0
    for jar_file in sorted(jar_files):
        size_bytes = jar_file.stat().st_size
        total_size += size_bytes
        
        if size_bytes > 1024 * 1024:
            size_str = f"{size_bytes/(1024*1024):.1f}MB"
        else:
            size_str = f"{size_bytes/1024:.1f}KB"
        
        print(f"  - {jar_file.name}: {size_str}")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"\n📊 总大小: {total_size_mb:.1f}MB")

def verify_critical_dependencies():
    """验证关键依赖是否存在"""
    lib_dir = Path("lib/jdt")
    
    critical_deps = [
        "org.eclipse.jdt.core.jar",
        "org.eclipse.core.runtime.jar", 
        "org.eclipse.core.resources.jar",
        "org.eclipse.equinox.common.jar"
    ]
    
    print(f"\n🔍 验证关键依赖:")
    print("=" * 30)
    
    missing_deps = []
    for dep in critical_deps:
        jar_path = lib_dir / dep
        if jar_path.exists() and jar_path.stat().st_size > 1000:
            size_kb = jar_path.stat().st_size / 1024
            print(f"✅ {dep}: {size_kb:.1f}KB")
        else:
            print(f"❌ {dep}: 缺失或损坏")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n⚠️  缺失关键依赖: {len(missing_deps)} 个")
        return False
    else:
        print(f"\n✅ 所有关键依赖都已就绪")
        return True

if __name__ == "__main__":
    print("🚀 JDT 3.13完整依赖下载工具")
    print("=" * 60)
    
    # 下载依赖
    if download_jdt_complete_dependencies():
        print("\n✅ JDT依赖下载完成！")
        
        # 列出下载的文件
        list_downloaded_jars()
        
        # 验证关键依赖
        if verify_critical_dependencies():
            print("\n🎉 JDT环境准备就绪！")
            print("现在可以尝试使用JDT进行Java代码解析")
        else:
            print("\n⚠️  部分关键依赖缺失，可能影响JDT功能")
    else:
        print("\n❌ JDT依赖下载不完整")
        print("请检查网络连接或手动下载缺失的依赖")