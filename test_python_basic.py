#!/usr/bin/env python3
"""
简化的 Python 脚本功能测试
验证所有 Python 脚本的基本功能
"""

import sys
import subprocess
from pathlib import Path


def test_script_help(script_path, script_name):
    """测试脚本帮助功能"""
    if not script_path.exists():
        print(f"❌ {script_name}: 脚本不存在")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and "usage:" in result.stdout.lower():
            print(f"✅ {script_name}: 帮助功能正常")
            return True
        else:
            print(f"❌ {script_name}: 帮助功能异常")
            return False
    except Exception as e:
        print(f"❌ {script_name}: 测试异常 - {e}")
        return False


def main():
    """主函数"""
    print("PLTHook Python 脚本基本功能测试")
    print("=" * 40)
    
    root_dir = Path(__file__).parent
    
    # 要测试的脚本列表
    scripts = [
        ("build_linux.py", "Linux 构建脚本"),
        ("build_windows.py", "Windows 构建脚本"),
        ("build_android.py", "Android 构建脚本"),
        ("build.py", "综合构建脚本"),
        ("test_android.py", "Android 测试脚本"),
        ("test/run_tests_windows.py", "Windows 测试脚本"),
        ("test/run_test.py", "VS 测试脚本"),
        ("test/build_memory_monitor.py", "内存监控构建脚本"),
        ("test/build_memory_monitor_enhanced.py", "内存监控构建脚本(增强版)"),
        ("test/uclibc_test.py", "uclibc 测试脚本"),
        ("test/android/run_tests.py", "Android 设备测试脚本")
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for script_file, script_name in scripts:
        script_path = root_dir / script_file
        total_tests += 1
        
        if test_script_help(script_path, script_name):
            passed_tests += 1
    
    print("\n" + "=" * 40)
    print(f"测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有 Python 脚本功能正常！")
        return 0
    else:
        print("⚠️  部分脚本存在问题，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
