#!/usr/bin/env python3
"""
Android 设备测试部署脚本 - Python 版本
支持自动设备架构检测、文件部署和测试运行
"""

import os
import sys
import subprocess
import argparse
import glob
from pathlib import Path
from typing import Optional, List

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

def run_adb_command(cmd: List[str]) -> Optional[str]:
    """运行 ADB 命令并返回输出"""
    try:
        result = subprocess.run(['adb'] + cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_colored(f"ADB 命令失败: {' '.join(cmd)}", Colors.RED)
        print_colored(f"错误: {e.stderr.strip()}", Colors.RED)
        return None
    except FileNotFoundError:
        print_colored("错误: ADB 未找到或不在 PATH 中", Colors.RED)
        print_colored("请确保 Android SDK 已安装并且 ADB 在 PATH 中", Colors.RED)
        return None

def check_adb_available() -> bool:
    """检查 ADB 是否可用"""
    result = run_adb_command(['version'])
    return result is not None

def check_device_connected() -> bool:
    """检查设备是否连接"""
    print_colored("检查 Android 设备连接...", Colors.YELLOW)
    result = run_adb_command(['devices'])
    
    if result and 'device' in result and '\tdevice' in result:
        print_colored("✓ 检测到 Android 设备", Colors.GREEN)
        return True
    else:
        print_colored("错误: 未检测到 Android 设备", Colors.RED)
        print_colored("请确保设备已连接并启用 USB 调试", Colors.RED)
        return False

def detect_device_architecture() -> str:
    """自动检测设备架构"""
    print_colored("自动检测设备架构...", Colors.YELLOW)
    
    device_abi = run_adb_command(['shell', 'getprop', 'ro.product.cpu.abi'])
    if not device_abi:
        print_colored("警告: 无法检测设备架构，使用默认 arm64-v8a", Colors.YELLOW)
        return "arm64-v8a"
    
    device_abi = device_abi.strip()
    
    if "arm64-v8a" in device_abi:
        return "arm64-v8a"
    elif "armeabi-v7a" in device_abi:
        return "armeabi-v7a"
    elif "x86_64" in device_abi:
        return "x86_64"
    else:
        print_colored(f"警告: 未识别的设备架构: {device_abi}，使用 arm64-v8a", Colors.YELLOW)
        return "arm64-v8a"

def get_device_info() -> dict:
    """获取设备信息"""
    info = {}
    
    model = run_adb_command(['shell', 'getprop', 'ro.product.model'])
    android_version = run_adb_command(['shell', 'getprop', 'ro.build.version.release'])
    api_level = run_adb_command(['shell', 'getprop', 'ro.build.version.sdk'])
    cpu_abi = run_adb_command(['shell', 'getprop', 'ro.product.cpu.abi'])
    
    info['model'] = model.strip() if model else "Unknown"
    info['android_version'] = android_version.strip() if android_version else "Unknown"
    info['api_level'] = api_level.strip() if api_level else "Unknown"
    info['cpu_abi'] = cpu_abi.strip() if cpu_abi else "Unknown"
    
    return info

def deploy_files(source_dir: str, arch: str) -> bool:
    """部署文件到设备"""
    print()
    print_colored("部署文件到设备...", Colors.CYAN)
    
    # 检查源目录
    if not os.path.exists(source_dir):
        print_colored(f"错误: 构建输出目录不存在: {source_dir}", Colors.RED)
        print_colored("请先运行 python build_android.py 构建 Android 版本", Colors.RED)
        return False
    
    # 创建目标目录
    result = run_adb_command(['shell', 'mkdir', '-p', '/data/local/tmp/plthook'])
    if result is None:
        return False
    
    # 推送构建文件
    print_colored("推送构建文件...", Colors.YELLOW)
    build_files = glob.glob(os.path.join(source_dir, "*"))
    
    for file_path in build_files:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            print_colored(f"  推送: {file_name}", Colors.GRAY)
            result = run_adb_command(['push', file_path, '/data/local/tmp/plthook/'])
            if result is None:
                return False
    
    # 推送测试脚本
    script_dir = os.path.dirname(os.path.abspath(__file__))
    run_tests_script = os.path.join(script_dir, "test", "android", "run_tests.sh")
    
    if os.path.exists(run_tests_script):
        print_colored("推送测试脚本...", Colors.YELLOW)
        result = run_adb_command(['push', run_tests_script, '/data/local/tmp/plthook/'])
        if result is None:
            return False
    
    # 设置执行权限
    print_colored("设置执行权限...", Colors.YELLOW)
    executables = [
        'testprog', 'memory_monitor', 'android_simple_test',
        'multithread_memory_test', 'multithread_memory_test_cpp',
        'memory_stress_test', 'advanced_memory_test', 'run_tests.sh'
    ]
    
    for exe in executables:
        run_adb_command(['shell', 'chmod', '+x', f'/data/local/tmp/plthook/{exe}'])
    
    # 验证文件部署
    print_colored("验证文件部署...", Colors.YELLOW)
    result = run_adb_command(['shell', 'ls', '-la', '/data/local/tmp/plthook/'])
    if result:
        print(result)
    
    print_colored("✓ 文件部署完成", Colors.GREEN)
    return True

def run_tests() -> bool:
    """运行测试"""
    print()
    print_colored("运行 Android 测试...", Colors.CYAN)
    
    # 设置环境并运行测试
    test_commands = [
        'cd /data/local/tmp/plthook',
        'export LD_LIBRARY_PATH=/data/local/tmp/plthook:$LD_LIBRARY_PATH',
        './run_tests.sh'
    ]
    
    test_command = ' && '.join(test_commands)
    
    print_colored("执行测试命令...", Colors.YELLOW)
    
    try:
        # 使用 subprocess 直接运行，显示实时输出
        result = subprocess.run(['adb', 'shell', test_command], check=True)
        
        if result.returncode == 0:
            print_colored("✓ Android 测试完成", Colors.GREEN)
            return True
        else:
            print_colored("✗ Android 测试失败", Colors.RED)
            return False
            
    except subprocess.CalledProcessError as e:
        print_colored(f"✗ Android 测试失败，退出代码: {e.returncode}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"✗ 运行测试时出错: {e}", Colors.RED)
        return False

def show_usage():
    """显示使用说明"""
    print()
    print_colored("使用方法:", Colors.YELLOW)
    print_colored("  python test_android.py --deploy     # 部署文件到设备", Colors.GRAY)
    print_colored("  python test_android.py --test       # 运行测试", Colors.GRAY)
    print_colored("  python test_android.py --all        # 部署并测试", Colors.GRAY)
    print_colored("  python test_android.py --all --arch arm64-v8a  # 指定架构", Colors.GRAY)
    print()
    print_colored("手动操作命令:", Colors.YELLOW)
    print_colored("  adb push output/android/arm64-v8a/* /data/local/tmp/plthook/", Colors.GRAY)
    print_colored("  adb shell 'cd /data/local/tmp/plthook && ./run_tests.sh'", Colors.GRAY)

def main():
    parser = argparse.ArgumentParser(description='Android 设备测试部署脚本')
    parser.add_argument('--arch', 
                       choices=['arm64-v8a', 'armeabi-v7a', 'x86_64', 'auto'],
                       default='auto',
                       help='目标架构')
    parser.add_argument('--deploy', action='store_true',
                       help='部署文件到设备')
    parser.add_argument('--test', action='store_true',
                       help='运行测试')
    parser.add_argument('--all', action='store_true',
                       help='部署并测试')
    
    args = parser.parse_args()
    
    print_colored("Android 设备测试部署脚本", Colors.GREEN + Colors.BOLD)
    print_colored("========================", Colors.GREEN)
    
    # 检查 ADB
    if not check_adb_available():
        sys.exit(1)
    
    # 检查设备连接
    if not check_device_connected():
        sys.exit(1)
    
    # 获取设备架构
    if args.arch == "auto":
        architecture = detect_device_architecture()
    else:
        architecture = args.arch
    
    print_colored(f"使用架构: {architecture}", Colors.YELLOW)
    
    # 获取设备信息
    device_info = get_device_info()
    print()
    print_colored("设备信息:", Colors.CYAN)
    print_colored(f"  设备型号: {device_info['model']}", Colors.GRAY)
    print_colored(f"  Android 版本: {device_info['android_version']}", Colors.GRAY)
    print_colored(f"  API 级别: {device_info['api_level']}", Colors.GRAY)
    print_colored(f"  架构: {device_info['cpu_abi']}", Colors.GRAY)
    
    # 设置路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output", "android")
    source_dir = os.path.join(output_dir, architecture)
    
    success = True
    
    # 执行操作
    if args.all or args.deploy:
        success &= deploy_files(source_dir, architecture)
    
    if args.all or args.test:
        if success:  # 只有在部署成功时才运行测试
            success &= run_tests()
    
    # 如果没有指定任何操作，显示使用说明
    if not args.deploy and not args.test and not args.all:
        show_usage()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
