#!/usr/bin/env python3
"""
下载JDT 3.13版本
"""

import os
import urllib.request
from pathlib import Path

def download_jdt_3_13():
    """下载JDT 3.13版本"""
    print("📦 下载JDT 3.13版本...")
    
    # 创建目录
    lib_dir = Path("lib/jdt")
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # JDT 3.13版本下载URL
    jdt_version = "3.13.0"
    jdt_url = f"https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/{jdt_version}/org.eclipse.jdt.core-{jdt_version}.jar"
    
    jdt_jar_path = lib_dir / "org.eclipse.jdt.core.jar"
    
    # 如果文件已存在，先删除
    if jdt_jar_path.exists():
        print(f"🗑️ 删除现有文件: {jdt_jar_path}")
        jdt_jar_path.unlink()
    
    try:
        print(f"📥 下载JDT Core {jdt_version}...")
        print(f"📍 URL: {jdt_url}")
        print(f"💾 保存到: {jdt_jar_path}")
        
        urllib.request.urlretrieve(jdt_url, jdt_jar_path)
        
        # 验证下载
        if jdt_jar_path.exists() and jdt_jar_path.stat().st_size > 1000000:  # 至少1MB
            size_mb = jdt_jar_path.stat().st_size / (1024 * 1024)
            print(f"✅ JDT 3.13下载成功: {size_mb:.1f}MB")
            return True
        else:
            print("❌ JDT下载失败或文件损坏")
            return False
            
    except Exception as e:
        print(f"❌ 下载JDT失败: {e}")
        return False

def verify_jdt_version():
    """验证JDT版本"""
    jdt_jar_path = Path("lib/jdt/org.eclipse.jdt.core.jar")
    
    if not jdt_jar_path.exists():
        print("❌ JDT JAR文件不存在")
        return False
    
    size_mb = jdt_jar_path.stat().st_size / (1024 * 1024)
    print(f"📁 JDT JAR文件: {jdt_jar_path}")
    print(f"📊 文件大小: {size_mb:.1f}MB")
    
    # JDT 3.13的大小应该在7-8MB左右
    if 6 < size_mb < 10:
        print("✅ JDT文件大小正常")
        return True
    else:
        print("⚠️ JDT文件大小异常，可能版本不正确")
        return False

if __name__ == "__main__":
    print("🚀 JDT 3.13版本下载工具")
    print("=" * 40)
    
    if download_jdt_3_13():
        verify_jdt_version()
        print("\n✅ JDT 3.13下载完成！")
        print("现在可以使用JDT 3.13进行Java代码解析")
    else:
        print("\n❌ JDT 3.13下载失败")
        print("请检查网络连接或手动下载")