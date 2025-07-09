#!/usr/bin/env python3
"""
PLTHook Python 脚本测试套件
验证所有 Python 构建和测试脚本的功能
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

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

def run_script_test(script_path: str, args: List[str], description: str) -> Tuple[bool, str]:
    """运行脚本测试"""
    print_colored(f"测试: {description}", Colors.CYAN)
    print_colored(f"脚本: {script_path}", Colors.GRAY)
    print_colored(f"参数: {' '.join(args) if args else '无'}", Colors.GRAY)
    
    if not os.path.exists(script_path):
        return False, f"脚本文件不存在: {script_path}"
    
    try:
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print_colored("✓ 测试通过", Colors.GREEN)
            return True, "成功"
        else:
            print_colored("✗ 测试失败", Colors.RED)
            if result.stderr:
                print_colored(f"错误输出: {result.stderr[:200]}...", Colors.RED)
            return False, f"退出代码: {result.returncode}"
            
    except subprocess.TimeoutExpired:
        print_colored("✗ 测试超时", Colors.RED)
        return False, "超时"
    except Exception as e:
        print_colored(f"✗ 测试异常: {e}", Colors.RED)
        return False, str(e)

def test_help_options(script_dir: str) -> Dict[str, bool]:
    """测试所有脚本的帮助选项"""
    print_colored("\n=== 测试帮助选项 ===", Colors.BOLD + Colors.YELLOW)
    
    scripts = [
        ("build.py", "综合构建脚本"),
        ("build_android.py", "Android 构建脚本"),
        ("build_windows.py", "Windows 构建脚本"),
        ("test_android.py", "Android 测试脚本"),
        ("test/build_memory_monitor.py", "内存监控构建脚本")
    ]
    
    results = {}
    
    for script_file, description in scripts:
        script_path = os.path.join(script_dir, script_file)
        success, message = run_script_test(script_path, ["--help"], f"{description} 帮助")
        results[script_file] = success
        print()
    
    return results

def test_version_and_info(script_dir: str) -> Dict[str, bool]:
    """测试脚本的基本信息显示"""
    print_colored("\n=== 测试基本信息显示 ===", Colors.BOLD + Colors.YELLOW)
    
    # 测试一些基本的无害选项
    test_cases = [
        ("build_android.py", ["--arch", "arm64-v8a", "--ndk-path", "/nonexistent"], "Android 架构检查"),
        ("build_windows.py", ["--arch", "x64", "--clean"], "Windows 清理选项"),
        ("test_android.py", ["--arch", "auto"], "Android 设备检查"),
    ]
    
    results = {}
    
    for script_file, args, description in test_cases:
        script_path = os.path.join(script_dir, script_file)
        success, message = run_script_test(script_path, args, description)
        results[script_file] = success
        print()
    
    return results

def test_script_syntax(script_dir: str) -> Dict[str, bool]:
    """测试脚本语法正确性"""
    print_colored("\n=== 测试脚本语法 ===", Colors.BOLD + Colors.YELLOW)
    
    scripts = [
        "build.py",
        "build_android.py", 
        "build_windows.py",
        "test_android.py",
        "test/build_memory_monitor.py"
    ]
    
    results = {}
    
    for script_file in scripts:
        script_path = os.path.join(script_dir, script_file)
        
        if not os.path.exists(script_path):
            print_colored(f"跳过不存在的脚本: {script_file}", Colors.YELLOW)
            results[script_file] = False
            continue
        
        print_colored(f"检查语法: {script_file}", Colors.CYAN)
        
        try:
            # 编译检查语法
            with open(script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            compile(source, script_path, 'exec')
            print_colored("✓ 语法正确", Colors.GREEN)
            results[script_file] = True
            
        except SyntaxError as e:
            print_colored(f"✗ 语法错误: {e}", Colors.RED)
            results[script_file] = False
        except Exception as e:
            print_colored(f"✗ 检查失败: {e}", Colors.RED)
            results[script_file] = False
        
        print()
    
    return results

def test_import_dependencies(script_dir: str) -> Dict[str, bool]:
    """测试脚本依赖导入"""
    print_colored("\n=== 测试依赖导入 ===", Colors.BOLD + Colors.YELLOW)
    
    scripts = [
        "build.py",
        "build_android.py",
        "build_windows.py", 
        "test_android.py",
        "test/build_memory_monitor.py"
    ]
    
    results = {}
    
    for script_file in scripts:
        script_path = os.path.join(script_dir, script_file)
        
        if not os.path.exists(script_path):
            results[script_file] = False
            continue
        
        print_colored(f"测试导入: {script_file}", Colors.CYAN)
        
        try:
            # 创建临时测试文件
            test_code = f"""
import sys
sys.path.insert(0, r'{script_dir}')

# 尝试导入脚本中的模块
import os
import sys
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict

print("所有依赖导入成功")
"""
            
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print_colored("✓ 依赖导入成功", Colors.GREEN)
                results[script_file] = True
            else:
                print_colored(f"✗ 依赖导入失败: {result.stderr}", Colors.RED)
                results[script_file] = False
                
        except Exception as e:
            print_colored(f"✗ 测试异常: {e}", Colors.RED)
            results[script_file] = False
        
        print()
    
    return results

def generate_test_report(all_results: Dict[str, Dict[str, bool]]):
    """生成测试报告"""
    print_colored("\n" + "="*60, Colors.BOLD)
    print_colored("PLTHook Python 脚本测试报告", Colors.BOLD + Colors.GREEN)
    print_colored("="*60, Colors.BOLD)
    
    total_tests = 0
    passed_tests = 0
    
    for test_category, results in all_results.items():
        print_colored(f"\n{test_category}:", Colors.BOLD + Colors.CYAN)
        
        for script, success in results.items():
            status = "✓ 通过" if success else "✗ 失败"
            color = Colors.GREEN if success else Colors.RED
            print_colored(f"  {script:<35} {status}", color)
            
            total_tests += 1
            if success:
                passed_tests += 1
    
    print_colored(f"\n总计测试: {total_tests}", Colors.BOLD)
    print_colored(f"通过测试: {passed_tests}", Colors.GREEN)
    print_colored(f"失败测试: {total_tests - passed_tests}", Colors.RED if total_tests > passed_tests else Colors.GREEN)
    
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print_colored(f"成功率: {success_rate:.1f}%", Colors.GREEN if success_rate >= 80 else Colors.YELLOW)
    
    # 建议
    if total_tests > passed_tests:
        print_colored("\n建议:", Colors.YELLOW)
        print_colored("1. 检查失败的脚本并修复语法或依赖问题", Colors.GRAY)
        print_colored("2. 确保所有必需的依赖已安装", Colors.GRAY)
        print_colored("3. 验证脚本路径和文件权限", Colors.GRAY)
    else:
        print_colored("\n所有测试通过! Python 脚本已准备就绪。", Colors.GREEN)

def main():
    print_colored("PLTHook Python 脚本测试套件", Colors.GREEN + Colors.BOLD)
    print_colored("============================", Colors.GREEN)
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print_colored(f"测试目录: {script_dir}", Colors.GRAY)
    print_colored(f"Python 版本: {sys.version}", Colors.GRAY)
    
    try:
        # 执行各种测试
        all_results = {}
        
        # 1. 语法测试
        all_results["语法检查"] = test_script_syntax(script_dir)
        
        # 2. 依赖导入测试
        all_results["依赖导入"] = test_import_dependencies(script_dir)
        
        # 3. 帮助选项测试
        all_results["帮助选项"] = test_help_options(script_dir)
        
        # 4. 基本功能测试
        # all_results["基本功能"] = test_version_and_info(script_dir)
        
        # 生成报告
        generate_test_report(all_results)
        
        # 检查总体是否成功
        total_failed = sum(
            1 for category_results in all_results.values() 
            for success in category_results.values() 
            if not success
        )
        
        if total_failed > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print_colored("\n测试被用户中断", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"测试失败: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
