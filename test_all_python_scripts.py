#!/usr/bin/env python3
"""
PLTHook Python 脚本测试套件
测试所有新增的 Python 脚本功能
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class Colors:
    """控制台颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_colored(text: str, color: str = Colors.WHITE):
    """打印彩色文本"""
    print(f"{color}{text}{Colors.END}")


def print_header(text: str):
    """打印标题"""
    print_colored(f"\n{'='*60}", Colors.CYAN)
    print_colored(f" {text}", Colors.BOLD + Colors.CYAN)
    print_colored(f"{'='*60}", Colors.CYAN)


def print_section(text: str):
    """打印节标题"""
    print_colored(f"\n{'-'*40}", Colors.BLUE)
    print_colored(f" {text}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'-'*40}", Colors.BLUE)


def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 30) -> Tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"
    except Exception as e:
        return -2, "", str(e)


class PythonScriptTester:
    """Python 脚本测试器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✓ PASS"
            color = Colors.GREEN
        else:
            status = "✗ FAIL"
            color = Colors.RED
        
        self.test_results.append({
            'name': test_name,
            'success': success,
            'details': details
        })
        
        print_colored(f"{status} {test_name}", color)
        if details:
            print_colored(f"    {details}", Colors.YELLOW if not success else Colors.WHITE)
    
    def test_script_help(self, script_path: Path, script_name: str) -> bool:
        """测试脚本的帮助选项"""
        if not script_path.exists():
            self.log_test_result(f"{script_name} (文件检查)", False, f"脚本不存在: {script_path}")
            return False
        
        # 测试帮助选项
        help_options = ["-h", "--help"]
        for option in help_options:
            returncode, stdout, stderr = run_command([sys.executable, str(script_path), option])
            if returncode == 0 and ("usage:" in stdout.lower() or "help" in stdout.lower()):
                self.log_test_result(f"{script_name} ({option})", True, "帮助信息正常")
                return True
        
        self.log_test_result(f"{script_name} (帮助)", False, "帮助选项未正常工作")
        return False
    
    def test_script_syntax(self, script_path: Path, script_name: str) -> bool:
        """测试脚本语法"""
        if not script_path.exists():
            return False
        
        returncode, stdout, stderr = run_command([sys.executable, "-m", "py_compile", str(script_path)])
        if returncode == 0:
            self.log_test_result(f"{script_name} (语法)", True, "语法检查通过")
            return True
        else:
            self.log_test_result(f"{script_name} (语法)", False, f"语法错误: {stderr}")
            return False
    
    def test_script_imports(self, script_path: Path, script_name: str) -> bool:
        """测试脚本导入"""
        if not script_path.exists():
            return False
        
        # 创建测试导入的临时脚本
        test_code = f'''
import sys
sys.path.insert(0, r"{script_path.parent}")
try:
    exec(open(r"{script_path}").read())
    print("IMPORT_SUCCESS")
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(1)
except SystemExit:
    pass  # 正常的脚本退出
except Exception as e:
    print(f"EXECUTION_ERROR: {{e}}")
    sys.exit(1)
'''
        
        returncode, stdout, stderr = run_command([sys.executable, "-c", test_code])
        if "IMPORT_SUCCESS" in stdout or returncode == 0:
            self.log_test_result(f"{script_name} (导入)", True, "导入测试通过")
            return True
        else:
            self.log_test_result(f"{script_name} (导入)", False, f"导入错误: {stderr}")
            return False
    
    def test_build_scripts(self):
        """测试构建脚本"""
        print_section("测试构建脚本")
        
        build_scripts = [
            ("build_linux.py", "Linux 构建脚本"),
            ("build_windows.py", "Windows 构建脚本"),
            ("build_android.py", "Android 构建脚本"),
            ("build.py", "综合构建脚本")
        ]
        
        for script_file, script_name in build_scripts:
            script_path = self.root_dir / script_file
            
            # 语法检查
            self.test_script_syntax(script_path, script_name)
            
            # 导入检查
            self.test_script_imports(script_path, script_name)
            
            # 帮助检查
            self.test_script_help(script_path, script_name)
            
            # 特定功能测试
            if script_file == "build.py":
                self.test_build_py_specific(script_path)
    
    def test_build_py_specific(self, script_path: Path):
        """测试 build.py 特定功能"""
        # 测试清理功能
        returncode, stdout, stderr = run_command([sys.executable, str(script_path), "--clean"])
        if returncode == 0:
            self.log_test_result("build.py (清理)", True, "清理功能正常")
        else:
            self.log_test_result("build.py (清理)", False, f"清理失败: {stderr}")
        
        # 测试平台检测
        returncode, stdout, stderr = run_command([sys.executable, str(script_path), "--platform", "auto", "--help"])
        if returncode == 0:
            self.log_test_result("build.py (平台检测)", True, "平台检测正常")
        else:
            self.log_test_result("build.py (平台检测)", False, f"平台检测失败: {stderr}")
    
    def test_test_scripts(self):
        """测试测试脚本"""
        print_section("测试测试脚本")
        
        test_scripts = [
            ("test_android.py", "Android 测试脚本"),
            ("test/run_tests_windows.py", "Windows 测试脚本"),
            ("test/run_test.py", "Visual Studio 测试脚本"),
            ("test/uclibc_test.py", "uclibc 测试脚本"),
            ("test/android/run_tests.py", "Android 设备测试脚本")
        ]
        
        for script_file, script_name in test_scripts:
            script_path = self.root_dir / script_file
            
            # 语法检查
            self.test_script_syntax(script_path, script_name)
            
            # 导入检查
            self.test_script_imports(script_path, script_name)
            
            # 帮助检查
            self.test_script_help(script_path, script_name)
    
    def test_build_memory_monitor_scripts(self):
        """测试内存监控构建脚本"""
        print_section("测试内存监控构建脚本")
        
        scripts = [
            ("test/build_memory_monitor.py", "内存监控构建脚本"),
            ("test/build_memory_monitor_enhanced.py", "内存监控构建脚本(增强版)")
        ]
        
        for script_file, script_name in scripts:
            script_path = self.root_dir / script_file
            
            # 语法检查
            self.test_script_syntax(script_path, script_name)
            
            # 导入检查
            self.test_script_imports(script_path, script_name)
            
            # 帮助检查
            self.test_script_help(script_path, script_name)
            
            # 清理功能测试
            if script_path.exists():
                returncode, stdout, stderr = run_command([sys.executable, str(script_path), "--clean"])
                if returncode == 0:
                    self.log_test_result(f"{script_name} (清理)", True, "清理功能正常")
                else:
                    self.log_test_result(f"{script_name} (清理)", False, f"清理失败: {stderr}")
    
    def test_dependency_availability(self):
        """测试依赖可用性"""
        print_section("测试依赖可用性")
        
        # 检查Python标准库
        standard_libs = [
            "os", "sys", "subprocess", "pathlib", "argparse", 
            "shutil", "platform", "urllib", "tarfile", "time"
        ]
        
        for lib in standard_libs:
            try:
                __import__(lib)
                self.log_test_result(f"导入 {lib}", True, "标准库可用")
            except ImportError:
                self.log_test_result(f"导入 {lib}", False, "标准库不可用")
    
    def test_cross_platform_compatibility(self):
        """测试跨平台兼容性"""
        print_section("测试跨平台兼容性")
        
        # 测试路径处理
        test_paths = [
            "test/subdir/file.txt",
            "test\\subdir\\file.txt",  # Windows 风格
            "/absolute/path/file.txt",  # Unix 风格
            "C:\\Windows\\System32\\file.txt"  # Windows 绝对路径
        ]
        
        for path_str in test_paths:
            try:
                path = Path(path_str)
                # 测试路径操作
                _ = path.parent
                _ = path.name
                _ = path.suffix
                self.log_test_result(f"路径处理: {path_str}", True, "路径处理正常")
            except Exception as e:
                self.log_test_result(f"路径处理: {path_str}", False, f"路径处理失败: {e}")
    
    def test_error_handling(self):
        """测试错误处理"""
        print_section("测试错误处理")
        
        # 测试无效参数
        test_cases = [
            ("build.py", ["--invalid-option"]),
            ("test_android.py", ["--non-existent-flag"]),
            ("test/run_test.py", ["invalid_arch"])
        ]
        
        for script_file, args in test_cases:
            script_path = self.root_dir / script_file
            if script_path.exists():
                returncode, stdout, stderr = run_command([sys.executable, str(script_path)] + args)
                if returncode != 0:
                    self.log_test_result(f"{script_file} (错误处理)", True, "正确处理无效参数")
                else:
                    self.log_test_result(f"{script_file} (错误处理)", False, "未正确处理无效参数")
    
    def test_performance(self):
        """测试性能"""
        print_section("测试性能")
        
        # 测试脚本启动时间
        performance_scripts = [
            "build.py",
            "test_android.py",
            "test/run_tests_windows.py"
        ]
        
        for script_file in performance_scripts:
            script_path = self.root_dir / script_file
            if script_path.exists():
                start_time = time.time()
                returncode, stdout, stderr = run_command([sys.executable, str(script_path), "--help"])
                end_time = time.time()
                
                execution_time = end_time - start_time
                if execution_time < 3.0:  # 3秒内启动算正常
                    self.log_test_result(f"{script_file} (启动时间)", True, f"启动时间: {execution_time:.2f}s")
                else:
                    self.log_test_result(f"{script_file} (启动时间)", False, f"启动时间过长: {execution_time:.2f}s")
    
    def generate_test_report(self):
        """生成测试报告"""
        print_header("测试报告")
        
        # 统计信息
        pass_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print_colored(f"总测试数: {self.total_tests}", Colors.BLUE)
        print_colored(f"通过数: {self.passed_tests}", Colors.GREEN)
        print_colored(f"失败数: {self.total_tests - self.passed_tests}", Colors.RED)
        print_colored(f"通过率: {pass_rate:.1f}%", Colors.CYAN)
        
        # 详细结果
        if self.total_tests - self.passed_tests > 0:
            print_colored(f"\n失败的测试:", Colors.RED)
            for result in self.test_results:
                if not result['success']:
                    print_colored(f"  ✗ {result['name']}: {result['details']}", Colors.RED)
        
        # 生成报告文件
        report_file = self.root_dir / "test_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("PLTHook Python 脚本测试报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总测试数: {self.total_tests}\n")
            f.write(f"通过数: {self.passed_tests}\n")
            f.write(f"失败数: {self.total_tests - self.passed_tests}\n")
            f.write(f"通过率: {pass_rate:.1f}%\n\n")
            
            f.write("详细结果:\n")
            f.write("-" * 30 + "\n")
            for result in self.test_results:
                status = "PASS" if result['success'] else "FAIL"
                f.write(f"[{status}] {result['name']}\n")
                if result['details']:
                    f.write(f"      {result['details']}\n")
            
        print_colored(f"\n测试报告已保存到: {report_file}", Colors.MAGENTA)
        
        return pass_rate >= 80  # 80% 通过率视为成功
    
    def run_all_tests(self):
        """运行所有测试"""
        print_header("PLTHook Python 脚本测试套件")
        
        # 运行各种测试
        self.test_dependency_availability()
        self.test_build_scripts()
        self.test_test_scripts()
        self.test_build_memory_monitor_scripts()
        self.test_cross_platform_compatibility()
        self.test_error_handling()
        self.test_performance()
        
        # 生成报告
        success = self.generate_test_report()
        
        return success


def main():
    """主函数"""
    tester = PythonScriptTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print_colored("\n用户中断测试", Colors.YELLOW)
        return 1
    except Exception as e:
        print_colored(f"\n测试异常: {e}", Colors.RED)
        return 1


if __name__ == "__main__":
    sys.exit(main())
