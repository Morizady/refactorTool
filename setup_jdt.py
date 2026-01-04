#!/usr/bin/env python3
"""
JDT环境设置脚本
自动安装和配置JPype和Eclipse JDT依赖
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
from pathlib import Path
import yaml
import platform

def check_java_installation():
    """检查Java安装"""
    print("🔍 检查Java环境...")
    
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        print(f"✅ 找到JAVA_HOME: {java_home}")
        return java_home
    
    # 尝试通过java命令查找
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 找到Java命令")
            # 尝试找到JAVA_HOME
            if platform.system() == "Windows":
                # Windows下尝试常见路径
                common_paths = [
                    "C:/Program Files/Java/jdk-11.0.16",
                    "C:/Program Files/Java/jdk-17.0.2",
                    "C:/Program Files/Java/jdk1.8.0_301",
                    "C:/Program Files/OpenJDK/openjdk-11.0.2"
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        print(f"✅ 推测JAVA_HOME: {path}")
                        return path
            else:
                # Linux/macOS
                try:
                    result = subprocess.run(['which', 'java'], capture_output=True, text=True)
                    if result.returncode == 0:
                        java_path = result.stdout.strip()
                        # 从java路径推测JAVA_HOME
                        java_home = os.path.dirname(os.path.dirname(java_path))
                        print(f"✅ 推测JAVA_HOME: {java_home}")
                        return java_home
                except:
                    pass
    except FileNotFoundError:
        pass
    
    print("❌ 未找到Java环境")
    print("请安装Java 8或更高版本，并设置JAVA_HOME环境变量")
    return None

def install_jpype():
    """安装JPype"""
    print("📦 安装JPype...")
    
    try:
        import jpype
        print("✅ JPype已安装")
        return True
    except ImportError:
        pass
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'JPype1'], check=True)
        print("✅ JPype安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ JPype安装失败: {e}")
        return False

def download_jdt_dependencies():
    """下载JDT依赖"""
    print("📦 下载Eclipse JDT依赖...")
    
    lib_dir = Path("lib/jdt")
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    jdt_jar = lib_dir / "org.eclipse.jdt.core.jar"
    
    if jdt_jar.exists():
        print("✅ JDT依赖已存在")
        return True
    
    try:
        # JDT Core JAR下载URL
        jdt_version = "3.13.0"  # 修改为3.13版本
        jdt_url = f"https://repo1.maven.org/maven2/org/eclipse/jdt/org.eclipse.jdt.core/{jdt_version}/org.eclipse.jdt.core-{jdt_version}.jar"
        
        print(f"📥 下载JDT Core {jdt_version}...")
        urllib.request.urlretrieve(jdt_url, jdt_jar)
        
        if jdt_jar.exists() and jdt_jar.stat().st_size > 1000000:
            print("✅ JDT依赖下载成功")
            return True
        else:
            print("❌ JDT依赖下载失败")
            return False
            
    except Exception as e:
        print(f"❌ 下载JDT依赖失败: {e}")
        return False

def install_other_dependencies():
    """安装其他Python依赖"""
    print("📦 安装其他Python依赖...")
    
    dependencies = [
        'pyyaml',
        'pathlib',
        'dataclasses; python_version<"3.7"'
    ]
    
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], check=True)
            print(f"✅ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ {dep} 安装失败: {e}")
            return False
    
    return True

def update_config(java_home):
    """更新配置文件"""
    print("⚙️ 更新配置文件...")
    
    config_file = Path("config.yml")
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # 更新Java配置
    if 'java' not in config:
        config['java'] = {}
    
    config['java']['java_home'] = java_home
    config['java']['jdt_lib_dir'] = "./lib/jdt"
    config['java']['auto_download_jdt'] = True
    
    # 确保其他配置存在
    if 'parsing' not in config:
        config['parsing'] = {
            'method': 'jdt',
            'source_encoding': 'UTF-8',
            'java_version': '11',
            'include_tests': False
        }
    else:
        config['parsing']['method'] = 'jdt'  # 设置默认使用JDT
    
    # 保存配置
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print("✅ 配置文件更新完成")

def test_jdt_setup():
    """测试JDT设置"""
    print("🧪 测试JDT设置...")
    
    try:
        from jdt_parser import JDTParser
        
        parser = JDTParser()
        if parser.initialize_jdt():
            print("✅ JDT环境测试成功")
            parser.shutdown()
            return True
        else:
            print("❌ JDT环境测试失败")
            return False
            
    except Exception as e:
        print(f"❌ JDT测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始设置JDT环境...")
    print("=" * 50)
    
    # 1. 检查Java环境
    java_home = check_java_installation()
    if not java_home:
        print("\n❌ Java环境检查失败")
        print("请按照以下步骤安装Java:")
        print("1. 下载并安装Java 8或更高版本")
        print("2. 设置JAVA_HOME环境变量")
        print("3. 重新运行此脚本")
        return False
    
    # 2. 安装JPype
    if not install_jpype():
        print("\n❌ JPype安装失败")
        return False
    
    # 3. 下载JDT依赖
    if not download_jdt_dependencies():
        print("\n❌ JDT依赖下载失败")
        return False
    
    # 4. 安装其他依赖
    if not install_other_dependencies():
        print("\n❌ Python依赖安装失败")
        return False
    
    # 5. 更新配置文件
    update_config(java_home)
    
    # 6. 测试设置
    if not test_jdt_setup():
        print("\n❌ JDT环境测试失败")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 JDT环境设置完成!")
    print("\n现在您可以使用以下命令:")
    print("  python main.py --single /path/to/project --parse-method jdt")
    print("  python main.py --call-tree /api/endpoint --parse-method jdt")
    print("\n配置文件: config.yml")
    print("JDT库目录: lib/jdt/")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)