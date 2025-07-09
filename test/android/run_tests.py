#!/usr/bin/env python3
"""
Android 设备测试脚本 - Python实现
在 Android 设备上运行 PLTHook 测试
"""

import os
import sys
import subprocess
import shlex
from pathlib import Path
from typing import List, Optional


def run_shell_command(cmd: str, description: str = "") -> int:
    """运行 shell 命令"""
    if description:
        print(f"{description}")
    
    print(f"执行: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=False
        )
        return result.returncode
    except Exception as e:
        print(f"命令执行失败: {e}")
        return 1


def check_file_and_set_permission(file_path: str, description: str) -> bool:
    """检查文件并设置执行权限"""
    if not Path(file_path).exists():
        print(f"程序不存在: {description} ({file_path})")
        return False
    
    # 设置执行权限
    result = run_shell_command(f"chmod +x {shlex.quote(file_path)}")
    if result == 0:
        print(f"已设置执行权限: {description}")
        return True
    else:
        print(f"设置权限失败: {description}")
        return False


def run_basic_tests(script_dir: str) -> bool:
    """运行基本测试"""
    test_prog = f"{script_dir}/testprog"
    lib_file = f"{script_dir}/libtest.so"
    
    # 检查必要文件
    if not Path(test_prog).exists():
        print(f"错误: 测试程序不存在: {test_prog}")
        return False
    
    if not Path(lib_file).exists():
        print(f"错误: 测试库不存在: {lib_file}")
        return False
    
    # 运行基本测试
    tests = [
        ("open", "基本 open 测试"),
        ("open_by_handle", "handle 模式测试")
    ]
    
    for test_mode, description in tests:
        print(f"\n测试: {description}")
        cmd = f"cd {shlex.quote(script_dir)} && LD_LIBRARY_PATH={shlex.quote(script_dir)} {shlex.quote(test_prog)} {test_mode}"
        result = run_shell_command(cmd, f"运行 {description}")
        
        if result != 0:
            print(f"✗ {description} 失败")
            return False
        else:
            print(f"✓ {description} 通过")
    
    return True


def run_advanced_tests(script_dir: str) -> bool:
    """运行高级测试"""
    # 高级测试程序列表
    advanced_tests = [
        ("android_simple_test", "简单 Android 测试"),
        ("multithread_memory_test", "多线程内存测试"),
        ("multithread_memory_test_cpp", "C++ 多线程内存测试"),
        ("memory_stress_test", "内存压力测试"),
        ("advanced_memory_test", "高级内存测试")
    ]
    
    success_count = 0
    total_count = 0
    
    for prog_name, description in advanced_tests:
        prog_path = f"{script_dir}/{prog_name}"
        
        if not Path(prog_path).exists():
            print(f"跳过: {description} (程序不存在)")
            continue
        
        total_count += 1
        print(f"\n测试: {description}")
        
        cmd = f"cd {shlex.quote(script_dir)} && LD_LIBRARY_PATH={shlex.quote(script_dir)} {shlex.quote(prog_path)}"
        result = run_shell_command(cmd, f"运行 {description}")
        
        if result == 0:
            print(f"✓ {description} 通过")
            success_count += 1
        else:
            print(f"✗ {description} 失败")
    
    if total_count == 0:
        print("没有高级测试程序可运行")
        return True
    
    print(f"\n高级测试结果: {success_count}/{total_count} 通过")
    return success_count == total_count


def run_performance_tests(script_dir: str) -> bool:
    """运行性能测试"""
    print("\n性能测试:")
    
    test_prog = f"{script_dir}/testprog"
    if not Path(test_prog).exists():
        print("跳过性能测试 (testprog 不存在)")
        return True
    
    # 多次运行测试以检查性能
    iterations = 10
    success_count = 0
    
    print(f"运行 {iterations} 次性能测试...")
    
    for i in range(iterations):
        cmd = f"cd {shlex.quote(script_dir)} && LD_LIBRARY_PATH={shlex.quote(script_dir)} {shlex.quote(test_prog)} open"
        result = run_shell_command(cmd, f"性能测试 {i+1}/{iterations}")
        
        if result == 0:
            success_count += 1
            print(".", end="", flush=True)
        else:
            print("X", end="", flush=True)
    
    print()  # 换行
    
    success_rate = (success_count / iterations) * 100
    print(f"性能测试结果: {success_count}/{iterations} 通过 ({success_rate:.1f}%)")
    
    return success_rate >= 90  # 90% 通过率视为成功


def show_system_info():
    """显示系统信息"""
    print("Android 系统信息:")
    
    info_commands = [
        ("getprop ro.build.version.release", "Android 版本"),
        ("getprop ro.product.cpu.abi", "CPU 架构"),
        ("getprop ro.product.model", "设备型号"),
        ("getprop ro.build.version.sdk", "SDK 版本"),
        ("uname -a", "内核信息"),
        ("cat /proc/meminfo | head -3", "内存信息"),
        ("cat /proc/cpuinfo | grep processor | wc -l", "CPU 核心数")
    ]
    
    for cmd, desc in info_commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"  {desc}: {result.stdout.strip()}")
            else:
                print(f"  {desc}: 获取失败")
        except Exception:
            print(f"  {desc}: 获取失败")
    
    print()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Android 设备测试脚本")
    parser.add_argument("--help-extended", action="store_true", help="显示扩展帮助信息")
    
    # 如果有命令行参数，解析它们
    if len(sys.argv) > 1:
        try:
            args = parser.parse_args()
            if hasattr(args, 'help_extended') and args.help_extended:
                print("Android 设备测试脚本扩展帮助")
                print("=" * 40)
                print("此脚本在 Android 设备上运行 PLTHook 测试")
                print("需要确保测试程序和库文件存在于脚本目录")
                return 0
        except SystemExit:
            # argparse 遇到 --help 会调用 sys.exit()
            return 0
    
    print("PLTHook Android 测试开始")
    print("========================")
    
    # 获取脚本目录
    script_dir = str(Path(__file__).parent.absolute())
    
    print("调试信息:")
    print(f"  脚本目录: {script_dir}")
    print(f"  测试程序: {script_dir}/testprog")
    print(f"  库目录: {script_dir}")
    print()
    
    # 显示当前目录内容
    print("当前目录内容:")
    run_shell_command(f"ls -la {shlex.quote(script_dir)}")
    print()
    
    # 显示系统信息
    show_system_info()
    
    # 检查并设置程序权限
    test_programs = [
        "testprog",
        "android_simple_test", 
        "multithread_memory_test",
        "multithread_memory_test_cpp",
        "memory_stress_test",
        "advanced_memory_test"
    ]
    
    print("设置程序权限:")
    for prog in test_programs:
        prog_path = f"{script_dir}/{prog}"
        check_file_and_set_permission(prog_path, prog)
    
    print()
    
    # 运行测试
    all_success = True
    
    # 基本功能测试
    print("=" * 40)
    print("基本功能测试")
    print("=" * 40)
    if not run_basic_tests(script_dir):
        all_success = False
    
    # 高级功能测试
    print("\n" + "=" * 40)
    print("高级功能测试")
    print("=" * 40)
    if not run_advanced_tests(script_dir):
        all_success = False
    
    # 性能测试
    print("\n" + "=" * 40)
    print("性能测试")
    print("=" * 40)
    if not run_performance_tests(script_dir):
        all_success = False
    
    # 输出最终结果
    print("\n" + "=" * 50)
    if all_success:
        print("✓ 所有测试通过!")
        print("PLTHook Android 平台功能正常")
        return 0
    else:
        print("✗ 部分测试失败!")
        print("请检查构建或运行环境")
        return 1


if __name__ == "__main__":
    sys.exit(main())
