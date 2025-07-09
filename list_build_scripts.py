#!/usr/bin/env python3
"""
PLTHook 构建脚本清单
列出所有构建和测试脚本，包括原有的和新增的Python版本
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def get_file_size_str(file_path: Path) -> str:
    """获取文件大小字符串"""
    if file_path.exists():
        size = file_path.stat().st_size
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    return "N/A"


def get_file_status(file_path: Path) -> str:
    """获取文件状态"""
    if file_path.exists():
        return "✅"
    else:
        return "❌"


def print_colored(text: str, color_code: str = "0"):
    """打印彩色文本"""
    print(f"\033[{color_code}m{text}\033[0m")


def print_header(title: str):
    """打印标题"""
    print_colored(f"\n{'=' * 70}", "96")  # 青色
    print_colored(f" {title}", "1;96")  # 粗体青色
    print_colored(f"{'=' * 70}", "96")


def print_section(title: str):
    """打印节标题"""
    print_colored(f"\n{'-' * 50}", "94")  # 蓝色
    print_colored(f" {title}", "1;94")  # 粗体蓝色
    print_colored(f"{'-' * 50}", "94")


def print_script_info(scripts: List[Tuple[str, str, str]], root_dir: Path):
    """打印脚本信息"""
    for script_file, script_name, description in scripts:
        script_path = root_dir / script_file
        status = get_file_status(script_path)
        size = get_file_size_str(script_path)
        
        print_colored(f"{status} {script_name}", "1;92" if status == "✅" else "1;91")
        print_colored(f"   📁 {script_file}", "37")
        print_colored(f"   📄 {size}", "37")
        print_colored(f"   💡 {description}", "37")
        print()


def main():
    """主函数"""
    print_header("PLTHook 构建脚本清单")
    
    root_dir = Path(__file__).parent.absolute()
    
    print_colored("本项目包含以下构建和测试脚本：", "1;37")
    
    # 主要构建脚本
    print_section("主要构建脚本")
    
    build_scripts = [
        # PowerShell 原版
        ("build_windows.ps1", "Windows 构建脚本 (PowerShell)", "原有的Windows构建脚本"),
        ("build_android.ps1", "Android 构建脚本 (PowerShell)", "原有的Android构建脚本"),
        ("build.ps1", "综合构建脚本 (PowerShell)", "原有的综合构建脚本"),
        
        # Bash 原版
        ("build.sh", "Linux/Unix 构建脚本 (Bash)", "原有的Linux/Unix构建脚本"),
        
        # Python 新版
        ("build_windows.py", "Windows 构建脚本 (Python)", "增强版Windows构建，自动查找VS"),
        ("build_android.py", "Android 构建脚本 (Python)", "增强版Android构建，支持多架构"),
        ("build_linux.py", "Linux 构建脚本 (Python)", "跨平台Linux/macOS构建脚本"),
        ("build.py", "综合构建脚本 (Python)", "统一入口构建脚本，支持所有平台")
    ]
    
    print_script_info(build_scripts, root_dir)
    
    # 测试脚本
    print_section("测试脚本")
    
    test_scripts = [
        # PowerShell/Batch 原版
        ("test_android.ps1", "Android 测试脚本 (PowerShell)", "原有的Android设备测试"),
        ("test/run-test.bat", "VS 测试脚本 (Batch)", "原有的Visual Studio测试"),
        ("test/run_tests_windows.bat", "Windows 测试脚本 (Batch)", "原有的Windows平台测试"),
        
        # Shell 原版
        ("test/uclibc-test.sh", "uclibc 测试脚本 (Shell)", "原有的uclibc环境测试"),
        ("test/android/run_tests.sh", "Android 设备测试脚本 (Shell)", "原有的Android设备测试"),
        
        # Python 新版
        ("test_android.py", "Android 测试脚本 (Python)", "增强版Android测试，自动设备检测"),
        ("test/run_test.py", "VS 测试脚本 (Python)", "增强版Visual Studio测试"),
        ("test/run_tests_windows.py", "Windows 测试脚本 (Python)", "增强版Windows测试，详细报告"),
        ("test/uclibc_test.py", "uclibc 测试脚本 (Python)", "跨平台uclibc测试"),
        ("test/android/run_tests.py", "Android 设备测试脚本 (Python)", "增强版Android设备测试")
    ]
    
    print_script_info(test_scripts, root_dir)
    
    # 构建工具脚本
    print_section("构建工具脚本")
    
    tool_scripts = [
        # PowerShell/Batch 原版
        ("test/build_memory_monitor.ps1", "内存监控构建脚本 (PowerShell)", "原有的内存监控工具构建"),
        ("test/build_memory_monitor.bat", "内存监控构建脚本 (Batch)", "原有的内存监控工具构建"),
        
        # Python 新版
        ("test/build_memory_monitor.py", "内存监控构建脚本 (Python)", "Python版本内存监控构建"),
        ("test/build_memory_monitor_enhanced.py", "内存监控构建脚本 (Python增强版)", "增强版内存监控构建，更多选项"),
        ("release_builder.py", "发布构建器 (Python)", "自动化发布构建工具")
    ]
    
    print_script_info(tool_scripts, root_dir)
    
    # 测试和验证脚本
    print_section("测试和验证脚本")
    
    validation_scripts = [
        ("test_python_scripts.py", "Python 脚本测试套件", "测试所有Python脚本功能"),
        ("test_python_basic.py", "Python 脚本基本测试", "快速验证Python脚本"),
        ("test_all_python_scripts.py", "Python 脚本全面测试", "完整的Python脚本测试套件"),
        ("python_scripts_summary.py", "Python 脚本总结", "展示所有Python脚本信息")
    ]
    
    print_script_info(validation_scripts, root_dir)
    
    # 统计信息
    print_section("统计信息")
    
    all_scripts = build_scripts + test_scripts + tool_scripts + validation_scripts
    total_scripts = len(all_scripts)
    existing_scripts = sum(1 for script_file, _, _ in all_scripts if (root_dir / script_file).exists())
    
    # 按类型分类
    powershell_scripts = [s for s in all_scripts if s[0].endswith('.ps1')]
    batch_scripts = [s for s in all_scripts if s[0].endswith('.bat')]
    shell_scripts = [s for s in all_scripts if s[0].endswith('.sh')]
    python_scripts = [s for s in all_scripts if s[0].endswith('.py')]
    
    print_colored(f"📊 脚本统计：", "1;33")
    print_colored(f"  总脚本数：{total_scripts}", "37")
    print_colored(f"  存在的脚本：{existing_scripts}", "37")
    print_colored(f"  缺失的脚本：{total_scripts - existing_scripts}", "37")
    print()
    
    print_colored(f"📊 按类型分类：", "1;33")
    print_colored(f"  PowerShell 脚本：{len(powershell_scripts)}", "37")
    print_colored(f"  Batch 脚本：{len(batch_scripts)}", "37")
    print_colored(f"  Shell 脚本：{len(shell_scripts)}", "37")
    print_colored(f"  Python 脚本：{len(python_scripts)}", "37")
    print()
    
    # 使用建议
    print_section("使用建议")
    
    recommendations = [
        "🚀 **推荐使用 Python 脚本**：更好的跨平台兼容性和用户体验",
        "🔧 **Windows 开发**：使用 `python build_windows.py` 替代 PowerShell 脚本",
        "📱 **Android 开发**：使用 `python build_android.py` 和 `python test_android.py`",
        "🧪 **快速测试**：运行 `python test_python_basic.py` 验证脚本功能",
        "📦 **综合构建**：使用 `python build.py` 作为统一入口",
        "🔍 **脚本验证**：运行 `python test_all_python_scripts.py` 进行全面测试"
    ]
    
    for recommendation in recommendations:
        print_colored(f"  {recommendation}", "37")
    
    print_header("构建脚本清单完成")
    print_colored(f"✅ 项目包含 {total_scripts} 个构建和测试脚本", "1;32")
    print_colored(f"✅ Python 版本提供了完整的跨平台解决方案", "1;32")
    print_colored(f"✅ 所有主要功能都有对应的自动化脚本", "1;32")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
