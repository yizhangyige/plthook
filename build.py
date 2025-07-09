#!/usr/bin/env python3
"""
PLTHook 综合构建脚本 - Python 版本
支持 Windows 和 Android 平台的构建和测试
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

def run_script(script_path: str, args: List[str] = None) -> bool:
    """运行 Python 脚本"""
    if not os.path.exists(script_path):
        print_colored(f"错误: 脚本不存在: {script_path}", Colors.RED)
        return False
    
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    print_colored(f"执行: {' '.join(cmd)}", Colors.CYAN)
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_colored(f"脚本执行失败，退出代码: {e.returncode}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"执行脚本时出错: {e}", Colors.RED)
        return False

def clean_all_directories(root_dir: str) -> None:
    """清理所有构建目录"""
    print_colored("清理所有构建目录...", Colors.YELLOW)
    
    # 清理主构建目录
    dirs_to_clean = ["build", "output"]
    
    for dir_name in dirs_to_clean:
        dir_path = os.path.join(root_dir, dir_name)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print_colored(f"已删除: {dir_path}", Colors.GRAY)
            except Exception as e:
                print_colored(f"删除目录失败 {dir_path}: {e}", Colors.RED)
    
    # 清理测试目录中的构建产物
    test_dir = os.path.join(root_dir, "test")
    if os.path.exists(test_dir):
        patterns = ["*.dll", "*.exe", "*.lib", "*.exp", "*.obj", "*.so", "*.o"]
        
        for pattern in patterns:
            for file_path in Path(test_dir).rglob(pattern):
                try:
                    file_path.unlink()
                    print_colored(f"已删除: {file_path}", Colors.GRAY)
                except Exception as e:
                    print_colored(f"删除文件失败 {file_path}: {e}", Colors.RED)
    
    # 清理 Android 构建产物
    android_libs_dir = os.path.join(root_dir, "test", "android", "libs")
    android_obj_dir = os.path.join(root_dir, "test", "android", "obj")
    
    for android_dir in [android_libs_dir, android_obj_dir]:
        if os.path.exists(android_dir):
            try:
                shutil.rmtree(android_dir)
                print_colored(f"已删除: {android_dir}", Colors.GRAY)
            except Exception as e:
                print_colored(f"删除目录失败 {android_dir}: {e}", Colors.RED)
    
    print_colored("清理完成", Colors.GREEN)

def show_summary(root_dir: str) -> None:
    """显示构建总结"""
    print()
    print_colored("构建总结", Colors.GREEN + Colors.BOLD)
    print_colored("========", Colors.GREEN)
    
    output_dir = os.path.join(root_dir, "output")
    if not os.path.exists(output_dir):
        print_colored("无构建输出", Colors.GRAY)
        return
    
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(output_dir, '').count(os.sep)
        
        if level == 0:
            continue
            
        if level == 1:
            platform_name = os.path.basename(root)
            print_colored(f"📁 {platform_name}/", Colors.CYAN)
        elif level == 2:
            arch_name = os.path.basename(root)
            print_colored(f"  📁 {arch_name}/", Colors.CYAN)
        
        if level >= 2:
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    size_kb = file_size / 1024
                    total_files += 1
                    total_size += file_size
                    
                    indent = "    " if level == 2 else "      "
                    print_colored(f"{indent}📄 {file} ({size_kb:.2f} KB)", Colors.GRAY)
                except:
                    indent = "    " if level == 2 else "      "
                    print_colored(f"{indent}📄 {file}", Colors.GRAY)
    
    if total_files > 0:
        print()
        print_colored(f"总计: {total_files} 个文件, {total_size / (1024*1024):.2f} MB", Colors.GREEN)

def main():
    parser = argparse.ArgumentParser(description='PLTHook 综合构建脚本')
    parser.add_argument('--platform', 
                       choices=['windows', 'android', 'all'],
                       default='all',
                       help='构建平台')
    parser.add_argument('--arch', 
                       choices=['x86', 'x64', 'arm64', 'arm64-v8a', 'armeabi-v7a', 'x86_64', 'all'],
                       default='all',
                       help='目标架构')
    parser.add_argument('--ndk-path', 
                       default=r'C:\Users\dong\tools\android-ndk\android-ndk-r27',
                       help='Android NDK 路径')
    parser.add_argument('--clean', action='store_true',
                       help='清理所有构建目录')
    parser.add_argument('--no-test', action='store_true',
                       help='不运行测试')
    parser.add_argument('--deploy-android', action='store_true',
                       help='构建后自动部署到 Android 设备')
    
    args = parser.parse_args()
    
    print_colored("PLTHook 综合构建脚本", Colors.GREEN + Colors.BOLD)
    print_colored("===================", Colors.GREEN)
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 清理操作
        if args.clean:
            clean_all_directories(script_dir)
            return
        
        success = True
        
        # Windows 构建
        if args.platform in ['windows', 'all']:
            print()
            print_colored("开始 Windows 构建...", Colors.CYAN)
            
            windows_script = os.path.join(script_dir, "build_windows.py")
            windows_args = []
            
            if args.arch in ['x86', 'x64', 'arm64']:
                windows_args.extend(['--arch', args.arch])
            elif args.arch == 'all':
                # 为 Windows 构建所有支持的架构
                for arch in ['x86', 'x64', 'arm64']:
                    arch_args = ['--arch', arch]
                    if args.no_test:
                        arch_args.append('--no-test')
                    
                    print_colored(f"构建 Windows {arch}...", Colors.YELLOW)
                    arch_success = run_script(windows_script, arch_args)
                    success &= arch_success
                    
                    if not arch_success:
                        print_colored(f"Windows {arch} 构建失败", Colors.RED)
            else:
                windows_args.extend(['--arch', 'x64'])  # 默认架构
            
            if args.arch != 'all':
                if args.no_test:
                    windows_args.append('--no-test')
                
                windows_success = run_script(windows_script, windows_args)
                success &= windows_success
        
        # Android 构建
        if args.platform in ['android', 'all']:
            print()
            print_colored("开始 Android 构建...", Colors.CYAN)
            
            android_script = os.path.join(script_dir, "build_android.py")
            android_args = ['--ndk-path', args.ndk_path]
            
            if args.arch in ['arm64-v8a', 'armeabi-v7a', 'x86_64']:
                android_args.extend(['--arch', args.arch])
            elif args.arch == 'all':
                android_args.extend(['--arch', 'all'])
            else:
                android_args.extend(['--arch', 'all'])  # 默认构建所有 Android 架构
            
            android_success = run_script(android_script, android_args)
            success &= android_success
            
            # Android 自动部署
            if android_success and args.deploy_android:
                print()
                print_colored("自动部署到 Android 设备...", Colors.CYAN)
                
                test_script = os.path.join(script_dir, "test_android.py")
                test_args = ['--all']  # 部署并测试
                
                deploy_success = run_script(test_script, test_args)
                if not deploy_success:
                    print_colored("Android 部署失败", Colors.YELLOW)
        
        # 显示构建总结
        show_summary(script_dir)
        
        print()
        if success:
            print_colored("所有构建任务完成!", Colors.GREEN)
            
            # 显示后续操作建议
            if args.platform in ['android', 'all'] and not args.deploy_android:
                print()
                print_colored("后续操作建议:", Colors.YELLOW)
                print_colored("  # 部署到 Android 设备并测试", Colors.GRAY)
                print_colored("  python test_android.py --all", Colors.GRAY)
                print()
                print_colored("  # 仅部署文件", Colors.GRAY)
                print_colored("  python test_android.py --deploy", Colors.GRAY)
                print()
                print_colored("  # 仅运行测试", Colors.GRAY)
                print_colored("  python test_android.py --test", Colors.GRAY)
        else:
            print_colored("构建过程中有错误发生", Colors.RED)
            sys.exit(1)
        
    except KeyboardInterrupt:
        print_colored("\n构建被用户中断", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"构建失败: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
