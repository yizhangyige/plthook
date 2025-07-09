#!/usr/bin/env python3
"""
PLTHook 跨平台构建脚本 - Python实现
支持 Linux, macOS, Windows (WSL), Android
"""

import os
import sys
import argparse
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, List


class Colors:
    """控制台颜色输出"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def log_info(message: str):
    """信息日志"""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def log_success(message: str):
    """成功日志"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def log_warning(message: str):
    """警告日志"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def log_error(message: str):
    """错误日志"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


class PLTHookBuilder:
    """PLTHook 构建器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.build_dir = self.script_dir / "build"
        self.output_dir = self.script_dir / "output"
        self.test_dir = self.script_dir / "test"
        
    def detect_platform(self) -> str:
        """自动检测平台"""
        system = platform.system().lower()
        if system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        else:
            log_warning(f"未知平台: {system}, 默认使用 linux")
            return "linux"
    
    def detect_architecture(self) -> str:
        """自动检测架构"""
        machine = platform.machine().lower()
        if machine in ["x86_64", "amd64"]:
            return "x86_64"
        elif machine in ["aarch64", "arm64"]:
            return "arm64"
        elif machine.startswith("arm"):
            return "armv7"
        else:
            log_warning(f"未知架构: {machine}, 默认使用 x86_64")
            return "x86_64"
    
    def clean_build_directories(self):
        """清理构建目录"""
        log_info("清理构建目录...")
        
        # 清理构建和输出目录
        for directory in [self.build_dir, self.output_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                log_info(f"已删除: {directory}")
        
        # 清理测试目录中的构建产物
        test_patterns = ["*.dll", "*.exe", "*.lib", "*.exp", "*.obj", "*.so", "*.a", "*.o"]
        for pattern in test_patterns:
            for file_path in self.test_dir.glob(pattern):
                file_path.unlink()
                log_info(f"已删除: {file_path}")
        
        log_success("清理完成")
    
    def ensure_directories(self):
        """确保目录存在"""
        self.build_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
        """运行命令"""
        if cwd is None:
            cwd = self.script_dir
        
        log_info(f"执行命令: {' '.join(cmd)}")
        log_info(f"工作目录: {cwd}")
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                env=env, 
                check=False,
                capture_output=False
            )
            return result.returncode
        except Exception as e:
            log_error(f"命令执行失败: {e}")
            return 1
    
    def build_linux(self, arch: str, build_type: str) -> bool:
        """构建 Linux 版本"""
        log_info(f"构建 Linux {arch} 平台 ({build_type})...")
        
        platform_output_dir = self.output_dir / f"linux/{arch}"
        platform_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查编译工具
        if shutil.which("gcc") is None and shutil.which("clang") is None:
            log_error("未找到 GCC 或 Clang 编译器")
            return False
        
        # 构建
        os.chdir(self.test_dir)
        try:
            # 使用 Makefile 构建
            make_cmd = ["make", "clean"]
            if self.run_command(make_cmd) != 0:
                log_warning("清理失败，继续构建...")
            
            make_cmd = ["make", "all"]
            if arch == "arm64":
                make_cmd.extend(["CC=aarch64-linux-gnu-gcc"])
            elif arch == "armv7":
                make_cmd.extend(["CC=arm-linux-gnueabihf-gcc"])
            
            if self.run_command(make_cmd) != 0:
                log_error("Linux 构建失败")
                return False
            
            # 复制产物
            artifacts = ["libtest.so", "testprog"]
            for artifact in artifacts:
                src_path = self.test_dir / artifact
                if src_path.exists():
                    shutil.copy2(src_path, platform_output_dir)
                    log_info(f"已复制: {artifact} -> {platform_output_dir}")
            
            log_success(f"Linux {arch} 构建完成")
            log_info(f"输出目录: {platform_output_dir}")
            return True
            
        finally:
            os.chdir(self.script_dir)
    
    def build_macos(self, arch: str, build_type: str) -> bool:
        """构建 macOS 版本"""
        log_info(f"构建 macOS {arch} 平台 ({build_type})...")
        
        platform_output_dir = self.output_dir / f"macos/{arch}"
        platform_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查编译工具
        if shutil.which("clang") is None:
            log_error("未找到 Clang 编译器")
            return False
        
        # 构建
        os.chdir(self.test_dir)
        try:
            # 清理
            make_cmd = ["make", "clean"]
            if self.run_command(make_cmd) != 0:
                log_warning("清理失败，继续构建...")
            
            # 构建
            make_cmd = ["make", "all"]
            if arch == "arm64":
                make_cmd.extend(["CFLAGS=-arch arm64", "LDFLAGS=-arch arm64"])
            elif arch == "x86_64":
                make_cmd.extend(["CFLAGS=-arch x86_64", "LDFLAGS=-arch x86_64"])
            
            if self.run_command(make_cmd) != 0:
                log_error("macOS 构建失败")
                return False
            
            # 复制产物
            artifacts = ["libtest.dylib", "testprog"]
            for artifact in artifacts:
                src_path = self.test_dir / artifact
                if src_path.exists():
                    shutil.copy2(src_path, platform_output_dir)
                    log_info(f"已复制: {artifact} -> {platform_output_dir}")
            
            log_success(f"macOS {arch} 构建完成")
            log_info(f"输出目录: {platform_output_dir}")
            return True
            
        finally:
            os.chdir(self.script_dir)
    
    def build_android(self, arch: str, ndk_path: str, build_type: str) -> bool:
        """构建 Android 版本"""
        log_info(f"构建 Android {arch} 平台 ({build_type})...")
        
        if not ndk_path:
            # 尝试从环境变量获取
            ndk_path = os.environ.get("ANDROID_NDK_PATH", "")
            if not ndk_path:
                ndk_path = os.environ.get("NDK_ROOT", "")
            if not ndk_path:
                ndk_path = os.environ.get("ANDROID_NDK_ROOT", "")
        
        if not ndk_path or not Path(ndk_path).exists():
            log_error("Android NDK 路径未设置或不存在")
            log_error("请设置 ANDROID_NDK_PATH 环境变量或使用 --ndk-path 参数")
            return False
        
        # 调用 Android 构建脚本
        android_builder = self.script_dir / "build_android.py"
        if not android_builder.exists():
            log_error("Android 构建脚本不存在: build_android.py")
            return False
        
        cmd = [sys.executable, str(android_builder), "--arch", arch, "--ndk", ndk_path]
        if build_type.lower() == "debug":
            cmd.append("--debug")
        
        return self.run_command(cmd) == 0
    
    def run_tests(self, platform: str, arch: str) -> bool:
        """运行测试"""
        log_info(f"运行 {platform} {arch} 测试...")
        
        platform_output_dir = self.output_dir / f"{platform}/{arch}"
        if not platform_output_dir.exists():
            log_warning(f"构建产物目录不存在: {platform_output_dir}")
            return False
        
        os.chdir(platform_output_dir)
        try:
            if platform == "windows":
                test_prog = "testprog.exe"
            else:
                test_prog = "./testprog"
            
            if not Path(test_prog).exists():
                log_error(f"测试程序不存在: {test_prog}")
                return False
            
            # 运行基本测试
            tests = ["open", "open_by_handle"]
            for test in tests:
                log_info(f"运行测试: {test}")
                cmd = [test_prog, test] if platform == "windows" else [test_prog, test]
                if self.run_command(cmd) != 0:
                    log_error(f"测试失败: {test}")
                    return False
                log_success(f"测试通过: {test}")
            
            log_success(f"{platform} {arch} 所有测试通过")
            return True
            
        finally:
            os.chdir(self.script_dir)
    
    def build(self, platform: str, arch: str, ndk_path: str, build_type: str, run_tests: bool) -> bool:
        """执行构建"""
        self.ensure_directories()
        
        success = False
        if platform == "linux":
            success = self.build_linux(arch, build_type)
        elif platform == "macos":
            success = self.build_macos(arch, build_type)
        elif platform == "windows":
            # 调用 Windows 构建脚本
            windows_builder = self.script_dir / "build_windows.py"
            if windows_builder.exists():
                cmd = [sys.executable, str(windows_builder), "--arch", arch]
                if not run_tests:
                    cmd.append("--no-test")
                success = self.run_command(cmd) == 0
            else:
                log_error("Windows 构建脚本不存在: build_windows.py")
                return False
        elif platform == "android":
            success = self.build_android(arch, ndk_path, build_type)
        else:
            log_error(f"不支持的平台: {platform}")
            return False
        
        if success and run_tests and platform != "android":
            success = self.run_tests(platform, arch)
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="PLTHook 跨平台构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --platform linux --arch x86_64 --run-tests
  %(prog)s --platform android --ndk-path /path/to/ndk --arch arm64
  %(prog)s --platform auto --clean
        """
    )
    
    parser.add_argument(
        "-p", "--platform",
        choices=["linux", "macos", "windows", "android", "auto"],
        default="auto",
        help="目标平台 (默认: auto)"
    )
    
    parser.add_argument(
        "-a", "--arch",
        choices=["x86_64", "arm64", "armv7"],
        help="目标架构 (默认: 自动检测)"
    )
    
    parser.add_argument(
        "-n", "--ndk-path",
        help="Android NDK 路径"
    )
    
    parser.add_argument(
        "-t", "--build-type",
        choices=["Debug", "Release", "RelWithDebInfo"],
        default="Release",
        help="构建类型 (默认: Release)"
    )
    
    parser.add_argument(
        "-c", "--clean",
        action="store_true",
        help="清理构建目录"
    )
    
    parser.add_argument(
        "-r", "--run-tests",
        action="store_true",
        help="运行测试"
    )
    
    args = parser.parse_args()
    
    builder = PLTHookBuilder()
    
    if args.clean:
        builder.clean_build_directories()
        return 0
    
    # 自动检测平台和架构
    if args.platform == "auto":
        args.platform = builder.detect_platform()
        log_info(f"自动检测平台: {args.platform}")
    
    if args.arch is None:
        args.arch = builder.detect_architecture()
        log_info(f"自动检测架构: {args.arch}")
    
    log_info("PLTHook 构建脚本")
    log_info("================")
    log_info(f"平台: {args.platform}")
    log_info(f"架构: {args.arch}")
    log_info(f"构建类型: {args.build_type}")
    log_info(f"运行测试: {args.run_tests}")
    
    if args.platform == "android" and not args.ndk_path:
        log_info("Android 平台需要 NDK 路径")
    
    success = builder.build(
        args.platform,
        args.arch,
        args.ndk_path or "",
        args.build_type,
        args.run_tests
    )
    
    if success:
        log_success("\n构建完成!")
        log_info(f"输出目录: {builder.output_dir}")
        return 0
    else:
        log_error("\n构建失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
