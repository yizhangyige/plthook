#!/usr/bin/env python3
"""
Windows 平台 PLTHook 测试脚本 - Python实现
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional


def run_command(cmd: list, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {' '.join(cmd)}")
        print(f"错误代码: {e.returncode}")
        print(f"标准输出: {e.stdout}")
        print(f"错误输出: {e.stderr}")
        raise


def check_file_exists(file_path: Path, description: str) -> bool:
    """检查文件是否存在"""
    if not file_path.exists():
        print(f"错误: {description}不存在: {file_path}")
        return False
    return True


def get_system_info():
    """获取系统信息"""
    print("系统信息:")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  处理器架构: {platform.machine()}")
    print(f"  Python版本: {platform.python_version()}")
    
    # 尝试获取.NET Framework版本 (仅Windows)
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full") as key:
                release, _ = winreg.QueryValueEx(key, "Release")
                print(f"  .NET Framework Release: {release}")
        except Exception:
            print("  .NET Framework: 未检测到")
    
    print()


def run_basic_tests(test_prog: Path) -> bool:
    """运行基本测试"""
    tests = [
        ("open", "open 模式"),
        ("open_by_handle", "open_by_handle 模式")
    ]
    
    for test_mode, description in tests:
        print(f"测试: {description}")
        try:
            result = run_command([str(test_prog), test_mode], check=False)
            if result.returncode == 0:
                print(f"√ {description}测试通过")
                if result.stdout.strip():
                    print(f"  输出: {result.stdout.strip()}")
            else:
                print(f"X {description}测试失败")
                if result.stderr.strip():
                    print(f"  错误: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"X {description}测试异常: {e}")
            return False
        print()
    
    return True


def run_memory_monitor_test(script_dir: Path) -> bool:
    """运行内存监控测试"""
    memory_monitor = script_dir / "memory_monitor_win.exe"
    if not memory_monitor.exists():
        print("内存监控程序不存在，跳过内存监控测试")
        return True
    
    print("测试: 内存监控功能")
    print("运行内存监控测试 (10秒)...")
    
    try:
        # 启动内存监控进程
        monitor_process = subprocess.Popen(
            [str(memory_monitor), "10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待10秒
        stdout, stderr = monitor_process.communicate(timeout=15)
        
        if monitor_process.returncode == 0:
            print("√ 内存监控测试通过")
            if stdout.strip():
                # 只显示最后几行输出，避免过多信息
                lines = stdout.strip().split('\n')
                if len(lines) > 5:
                    print("  输出 (最后5行):")
                    for line in lines[-5:]:
                        print(f"    {line}")
                else:
                    print(f"  输出: {stdout.strip()}")
            return True
        else:
            print("X 内存监控测试失败")
            if stderr.strip():
                print(f"  错误: {stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("X 内存监控测试超时")
        monitor_process.kill()
        return False
    except Exception as e:
        print(f"X 内存监控测试异常: {e}")
        return False


def run_comprehensive_tests(script_dir: Path) -> bool:
    """运行综合测试"""
    print("测试: 综合功能测试")
    
    # 测试多次调用
    test_prog = script_dir / "testprog.exe"
    if not test_prog.exists():
        print("测试程序不存在，跳过综合测试")
        return True
    
    try:
        print("  多次调用测试...")
        for i in range(3):
            result = run_command([str(test_prog), "open"], check=False)
            if result.returncode != 0:
                print(f"X 第{i+1}次调用失败")
                return False
        
        print("√ 多次调用测试通过")
        return True
        
    except Exception as e:
        print(f"X 综合测试异常: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows 平台 PLTHook 测试脚本")
    parser.add_argument("--help-extended", action="store_true", help="显示扩展帮助信息")
    
    # 如果有命令行参数，解析它们
    if len(sys.argv) > 1:
        args = parser.parse_args()
        if hasattr(args, 'help_extended') and args.help_extended:
            print("Windows 平台 PLTHook 测试脚本扩展帮助")
            print("=" * 40)
            print("此脚本用于测试 PLTHook 在 Windows 平台的功能")
            print("确保 testprog.exe 和 libtest.dll 存在于当前目录")
            return 0
    
    print("PLTHook Windows 测试开始")
    print("========================")
    
    # 获取脚本目录
    script_dir = Path(__file__).parent.absolute()
    
    # 显示系统信息
    get_system_info()
    
    # 检查必要文件
    test_prog = script_dir / "testprog.exe"
    test_lib = script_dir / "libtest.dll"
    
    if not check_file_exists(test_prog, "测试程序"):
        return 1
    
    if not check_file_exists(test_lib, "测试库"):
        return 1
    
    # 运行测试
    success = True
    
    # 基本功能测试
    if not run_basic_tests(test_prog):
        success = False
    
    # 内存监控测试
    if not run_memory_monitor_test(script_dir):
        success = False
    
    # 综合测试
    if not run_comprehensive_tests(script_dir):
        success = False
    
    # 输出结果
    print("=" * 40)
    if success:
        print("✓ 所有测试通过!")
        print("PLTHook Windows 平台功能正常")
        return 0
    else:
        print("✗ 部分测试失败!")
        print("请检查构建或运行环境")
        return 1


if __name__ == "__main__":
    sys.exit(main())
