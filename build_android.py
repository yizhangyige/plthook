#!/usr/bin/env python3
"""
Android PLTHook 构建脚本 - Python 版本
支持多架构构建，包含详细的错误处理和输出信息
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
from typing import List, Optional

class Colors:
    """终端颜色定义"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text: str, color: str = Colors.ENDC):
    """打印彩色文本"""
    print(f"{color}{text}{Colors.ENDC}")

def find_ndk_build(ndk_path: str) -> Optional[str]:
    """查找 ndk-build 工具"""
    candidates = [
        "ndk-build.cmd",
        "ndk-build.exe", 
        "ndk-build"
    ]
    
    for candidate in candidates:
        ndk_build_path = os.path.join(ndk_path, candidate)
        if os.path.exists(ndk_build_path):
            return ndk_build_path
    
    return None

def run_command(cmd: str, description: str = "") -> bool:
    """运行命令并返回成功状态"""
    if description:
        print_colored(f"执行: {cmd}", Colors.GRAY)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=False, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"命令执行失败: {e}", Colors.RED)
        return False

def create_application_mk(android_dir: str, abi: str) -> None:
    """创建 Application.mk 文件"""
    app_mk_path = os.path.join(android_dir, "jni", "Application.mk")
    
    content = f"""APP_PLATFORM := android-21
APP_ABI := {abi}
APP_STL := c++_shared
APP_CPPFLAGS := -frtti -fexceptions -std=c++11 -D__ANDROID_API__=21
APP_OPTIM := release
"""
    
    with open(app_mk_path, 'w', encoding='utf-8') as f:
        f.write(content)

def copy_build_results(android_dir: str, output_dir: str, abi: str) -> bool:
    """复制构建结果到输出目录"""
    abi_output_dir = os.path.join(output_dir, abi)
    os.makedirs(abi_output_dir, exist_ok=True)
    
    libs_path = os.path.join(android_dir, "libs", abi)
    if not os.path.exists(libs_path):
        print_colored(f"警告: 构建输出目录不存在: {libs_path}", Colors.YELLOW)
        return False
    
    try:
        # 复制所有文件
        for item in os.listdir(libs_path):
            src = os.path.join(libs_path, item)
            dst = os.path.join(abi_output_dir, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        
        print_colored(f"复制文件到: {abi_output_dir}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"复制文件失败: {e}", Colors.RED)
        return False

def show_build_results(output_dir: str) -> None:
    """显示构建结果"""
    print()
    print_colored("构建结果:", Colors.YELLOW)
    
    if not os.path.exists(output_dir):
        print_colored("  无构建输出", Colors.GRAY)
        return
    
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(output_dir, '').count(os.sep)
        indent = '  ' * level
        rel_path = os.path.relpath(root, output_dir)
        
        if level == 0:
            continue
            
        if level == 1:
            print_colored(f"  📁 {os.path.basename(root)}/", Colors.CYAN)
        
        sub_indent = '  ' * (level + 1)
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size_kb = os.path.getsize(file_path) / 1024
                print_colored(f"    📄 {file} ({size_kb:.2f} KB)", Colors.GRAY)
            except:
                print_colored(f"    📄 {file}", Colors.GRAY)

def clean_build(android_dir: str, ndk_build_exe: str) -> bool:
    """清理构建"""
    print_colored("清理 Android 构建...", Colors.YELLOW)
    cmd = f'"{ndk_build_exe}" -C "{android_dir}" clean'
    return run_command(cmd, "清理构建")

def build_architecture(android_dir: str, ndk_build_exe: str, output_dir: str, abi: str) -> bool:
    """构建指定架构"""
    print()
    print_colored(f"构建 {abi} 架构...", Colors.CYAN)
    
    # 创建 Application.mk
    create_application_mk(android_dir, abi)
    
    # 执行构建
    cmd = f'"{ndk_build_exe}" -C "{android_dir}" -j4'
    success = run_command(cmd, f"构建 {abi}")
    
    if success:
        print_colored(f"✓ {abi} 架构构建成功", Colors.GREEN)
        
        # 复制构建结果
        copy_success = copy_build_results(android_dir, output_dir, abi)
        return copy_success
    else:
        print_colored(f"✗ {abi} 架构构建失败", Colors.RED)
        return False

def restore_original_application_mk(android_dir: str) -> None:
    """恢复原始 Application.mk"""
    original_content = """APP_PLATFORM := android-21
APP_ABI := arm64-v8a
APP_STL := c++_shared
APP_CPPFLAGS := -frtti -fexceptions -std=c++11 -D__ANDROID_API__=21
APP_OPTIM := release
"""
    
    app_mk_path = os.path.join(android_dir, "jni", "Application.mk")
    with open(app_mk_path, 'w', encoding='utf-8') as f:
        f.write(original_content)

def main():
    parser = argparse.ArgumentParser(description='Android PLTHook 构建脚本')
    parser.add_argument('--ndk-path', 
                       default=r'C:\Users\dong\tools\android-ndk\android-ndk-r27',
                       help='Android NDK 路径')
    parser.add_argument('--arch', 
                       choices=['arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86', 'all'],
                       default='all',
                       help='目标架构')
    parser.add_argument('--clean', action='store_true',
                       help='清理构建')
    
    args = parser.parse_args()
    
    print_colored("Android PLTHook Build Script", Colors.GREEN + Colors.BOLD)
    print_colored("============================", Colors.GREEN)
    
    # 设置路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    android_dir = os.path.join(script_dir, "test", "android")
    output_dir = os.path.join(script_dir, "output", "android")
    
    # 检查 NDK 路径
    if not os.path.exists(args.ndk_path):
        print_colored(f"错误: Android NDK 路径不存在: {args.ndk_path}", Colors.RED)
        sys.exit(1)
    
    # 查找 ndk-build 工具
    ndk_build_exe = find_ndk_build(args.ndk_path)
    if not ndk_build_exe:
        print_colored(f"错误: 未找到 ndk-build 工具在: {args.ndk_path}", Colors.RED)
        sys.exit(1)
    
    print_colored(f"使用 Android NDK: {args.ndk_path}", Colors.YELLOW)
    print_colored(f"NDK Build 工具: {ndk_build_exe}", Colors.YELLOW)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 清理构建
    if args.clean:
        success = clean_build(android_dir, ndk_build_exe)
        if success:
            print_colored("清理完成", Colors.GREEN)
        sys.exit(0 if success else 1)
    
    # 设置架构列表
    if args.arch == "all":
        abi_list = ["arm64-v8a", "armeabi-v7a", "x86_64"]
    else:
        abi_list = [args.arch]
    
    print_colored(f"构建目标架构: {', '.join(abi_list)}", Colors.YELLOW)
    
    # 构建每个架构
    build_results = {}
    for abi in abi_list:
        success = build_architecture(android_dir, ndk_build_exe, output_dir, abi)
        build_results[abi] = success
    
    # 恢复原始 Application.mk
    restore_original_application_mk(android_dir)
    
    print()
    print_colored("Android 构建完成!", Colors.GREEN)
    print_colored(f"输出目录: {output_dir}", Colors.GREEN)
    
    # 显示构建结果
    show_build_results(output_dir)
    
    # 显示使用说明
    print()
    print_colored("使用说明:", Colors.YELLOW)
    print_colored("1. 将对应架构的文件推送到 Android 设备:", Colors.GRAY)
    print_colored("   adb push output/android/arm64-v8a/* /data/local/tmp/", Colors.GRAY)
    print_colored("2. 在设备上运行测试:", Colors.GRAY)
    print_colored("   adb shell 'cd /data/local/tmp && ./run_tests.sh'", Colors.GRAY)
    
    # 检查是否有失败的构建
    failed_builds = [abi for abi, success in build_results.items() if not success]
    if failed_builds:
        print()
        print_colored(f"构建失败的架构: {', '.join(failed_builds)}", Colors.RED)
        sys.exit(1)
    else:
        print()
        print_colored("所有架构构建成功!", Colors.GREEN)

if __name__ == "__main__":
    main()
