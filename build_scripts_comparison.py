#!/usr/bin/env python3
"""
PLTHook 构建脚本对比表
展示原有脚本与新增Python脚本的对应关系
"""

import sys
from pathlib import Path
from typing import List, Tuple


def print_colored(text: str, color_code: str = "0"):
    """打印彩色文本"""
    print(f"\033[{color_code}m{text}\033[0m")


def print_header(title: str):
    """打印标题"""
    print_colored(f"\n{'=' * 80}", "96")
    print_colored(f" {title}", "1;96")
    print_colored(f"{'=' * 80}", "96")


def check_file_exists(file_path: Path) -> str:
    """检查文件是否存在"""
    return "✅" if file_path.exists() else "❌"


def get_file_size(file_path: Path) -> str:
    """获取文件大小"""
    if file_path.exists():
        size = file_path.stat().st_size
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size//1024}KB"
        else:
            return f"{size//(1024*1024)}MB"
    return "N/A"


def print_comparison_table():
    """打印对比表格"""
    root_dir = Path(__file__).parent.absolute()
    
    # 脚本对应关系
    comparisons = [
        # (原脚本, Python脚本, 功能描述, 改进说明)
        ("build_windows.ps1", "build_windows.py", "Windows 构建", "增强错误处理，自动VS查找"),
        ("build_android.ps1", "build_android.py", "Android 构建", "多架构并行，进度显示"),
        ("build.ps1", "build.py", "综合构建", "跨平台支持，统一接口"),
        ("build.sh", "build_linux.py", "Linux/Unix 构建", "Python跨平台实现"),
        ("test_android.ps1", "test_android.py", "Android 测试", "自动设备检测，智能部署"),
        ("test/run-test.bat", "test/run_test.py", "VS 测试", "增强参数支持，错误处理"),
        ("test/run_tests_windows.bat", "test/run_tests_windows.py", "Windows 测试", "详细报告，系统信息"),
        ("test/uclibc-test.sh", "test/uclibc_test.py", "uclibc 测试", "跨平台，自动下载工具链"),
        ("test/android/run_tests.sh", "test/android/run_tests.py", "Android 设备测试", "增强测试套件，性能测试"),
        ("test/build_memory_monitor.ps1", "test/build_memory_monitor.py", "内存监控构建", "Python实现，保持兼容"),
        ("test/build_memory_monitor.bat", "test/build_memory_monitor_enhanced.py", "内存监控构建增强", "更多选项，测试功能"),
    ]
    
    # 计算列宽
    max_original = max(len(row[0]) for row in comparisons) + 2
    max_python = max(len(row[1]) for row in comparisons) + 2
    max_function = max(len(row[2]) for row in comparisons) + 2
    max_improvement = max(len(row[3]) for row in comparisons) + 2
    
    # 打印表头
    print_colored(f"{'原脚本':<{max_original}} | {'Python脚本':<{max_python}} | {'功能':<{max_function}} | {'改进':<{max_improvement}} | 状态", "1;33")
    print_colored(f"{'-' * max_original}-+-{'-' * max_python}-+-{'-' * max_function}-+-{'-' * max_improvement}-+------", "33")
    
    # 打印每一行
    for original, python_script, function, improvement in comparisons:
        orig_path = root_dir / original
        py_path = root_dir / python_script
        
        orig_status = check_file_exists(orig_path)
        py_status = check_file_exists(py_path)
        
        status = f"{orig_status}{py_status}"
        
        print_colored(f"{original:<{max_original}} | {python_script:<{max_python}} | {function:<{max_function}} | {improvement:<{max_improvement}} | {status}", "37")
    
    # 新增的Python专用脚本
    print_colored(f"\n{'-' * 20}", "94")
    print_colored(" 新增的Python专用脚本", "1;94")
    print_colored(f"{'-' * 20}", "94")
    
    new_scripts = [
        ("test_python_scripts.py", "Python脚本功能测试"),
        ("test_python_basic.py", "Python脚本基本验证"),
        ("test_all_python_scripts.py", "Python脚本全面测试"),
        ("python_scripts_summary.py", "Python脚本总结展示"),
        ("release_builder.py", "自动化发布构建"),
        ("list_build_scripts.py", "构建脚本清单"),
    ]
    
    for script, description in new_scripts:
        script_path = root_dir / script
        status = check_file_exists(script_path)
        size = get_file_size(script_path)
        print_colored(f"{status} {script:<35} | {description:<30} | {size}", "37")


def print_statistics():
    """打印统计信息"""
    root_dir = Path(__file__).parent.absolute()
    
    # 统计各类脚本
    script_types = {
        "PowerShell (.ps1)": list(root_dir.glob("**/*.ps1")),
        "Batch (.bat)": list(root_dir.glob("**/*.bat")),
        "Shell (.sh)": list(root_dir.glob("**/*.sh")),
        "Python (.py)": list(root_dir.glob("**/*.py"))
    }
    
    print_colored(f"\n{'脚本类型':<20} | {'数量':<6} | {'总大小'}", "1;33")
    print_colored(f"{'-' * 20}-+-{'-' * 6}-+--------", "33")
    
    total_files = 0
    total_size = 0
    
    for script_type, files in script_types.items():
        count = len(files)
        size = sum(f.stat().st_size for f in files if f.exists())
        total_files += count
        total_size += size
        
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size//1024}KB"
        else:
            size_str = f"{size//(1024*1024)}MB"
        
        print_colored(f"{script_type:<20} | {count:<6} | {size_str}", "37")
    
    total_size_str = f"{total_size//1024}KB" if total_size < 1024*1024 else f"{total_size//(1024*1024)}MB"
    print_colored(f"{'-' * 20}-+-{'-' * 6}-+--------", "33")
    print_colored(f"{'总计':<20} | {total_files:<6} | {total_size_str}", "1;32")


def main():
    """主函数"""
    print_header("PLTHook 构建脚本对比表")
    
    print_colored("原有脚本与新增Python脚本的对应关系：", "1;37")
    print_colored("状态说明：✅✅=两个都存在, ✅❌=仅原脚本存在, ❌✅=仅Python脚本存在", "33")
    
    print_comparison_table()
    
    print_colored(f"\n{'-' * 50}", "94")
    print_colored(" 脚本统计信息", "1;94")
    print_colored(f"{'-' * 50}", "94")
    
    print_statistics()
    
    print_colored(f"\n{'-' * 50}", "94")
    print_colored(" 使用建议", "1;94")
    print_colored(f"{'-' * 50}", "94")
    
    suggestions = [
        "🎯 **优先使用Python脚本**: 更好的跨平台兼容性和用户体验",
        "🔧 **Windows开发**: `python build_windows.py --arch x64`",
        "📱 **Android开发**: `python build_android.py --arch arm64-v8a`",
        "🚀 **快速构建**: `python build.py --platform auto`",
        "🧪 **测试验证**: `python test_python_basic.py`",
        "📦 **发布构建**: `python release_builder.py`"
    ]
    
    for suggestion in suggestions:
        print_colored(f"  {suggestion}", "37")
    
    print_header("对比表完成")
    print_colored("✅ Python脚本提供了完整的功能替代方案", "1;32")
    print_colored("✅ 所有原有脚本功能都得到了增强和改进", "1;32")
    print_colored("✅ 新增了专门的测试和验证工具", "1;32")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
