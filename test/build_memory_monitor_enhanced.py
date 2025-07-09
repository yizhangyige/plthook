#!/usr/bin/env python3
"""
Windows 内存监控构建脚本 - Python实现 (增强版)
替代 build_memory_monitor.bat
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, List


def find_visual_studio() -> Optional[Path]:
    """查找 Visual Studio 安装路径"""
    # 查找 vswhere.exe
    vswhere_paths = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    ]
    
    vswhere_path = None
    for path in vswhere_paths:
        if path.exists():
            vswhere_path = path
            break
    
    if not vswhere_path:
        print("错误: 未找到 vswhere.exe")
        return None
    
    try:
        # 查找最新的 Visual Studio 安装
        result = subprocess.run(
            [
                str(vswhere_path),
                "-latest",
                "-products", "*",
                "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property", "installationPath"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        vs_path = result.stdout.strip()
        if vs_path and Path(vs_path).exists():
            return Path(vs_path)
        
    except subprocess.CalledProcessError:
        pass
    
    print("错误: 未找到有效的 Visual Studio 安装")
    return None


def setup_vs_environment(vs_path: Path, arch: str) -> Dict[str, str]:
    """设置 Visual Studio 环境变量"""
    vcvarsall_path = vs_path / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    
    if not vcvarsall_path.exists():
        raise FileNotFoundError(f"vcvarsall.bat 不存在: {vcvarsall_path}")
    
    # 创建临时批处理文件来设置环境
    temp_bat = Path("temp_setup_env.bat")
    
    try:
        with open(temp_bat, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'call "{vcvarsall_path}" {arch}\n')
            f.write('echo VS_SETUP_COMPLETE\n')
            f.write('set\n')  # 输出所有环境变量
        
        # 运行批处理文件
        result = subprocess.run(
            [str(temp_bat)],
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 解析环境变量
        env = os.environ.copy()
        lines = result.stdout.split('\n')
        found_setup = False
        
        for line in lines:
            if line.strip() == "VS_SETUP_COMPLETE":
                found_setup = True
                continue
            
            if found_setup and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    env[key] = value
        
        if not found_setup:
            raise RuntimeError("Visual Studio 环境设置失败")
        
        return env
        
    finally:
        if temp_bat.exists():
            temp_bat.unlink()


def check_compiler_in_path() -> bool:
    """检查编译器是否在 PATH 中"""
    return shutil.which("cl") is not None


def build_memory_monitor(
    arch: str = "x64",
    optimization: str = "O2",
    debug: bool = False,
    clean: bool = False,
    output_dir: Optional[Path] = None
) -> bool:
    """构建内存监控程序"""
    
    script_dir = Path(__file__).parent.absolute()
    
    # 清理模式
    if clean:
        print("清理构建产物...")
        patterns = ["*.exe", "*.obj", "*.pdb", "*.ilk"]
        for pattern in patterns:
            for file_path in script_dir.glob(pattern):
                file_path.unlink()
                print(f"已删除: {file_path}")
        print("清理完成")
        return True
    
    # 检查源文件
    memory_monitor_c = script_dir / "memory_monitor.c"
    plthook_win32_c = script_dir.parent / "plthook_win32.c"
    
    if not memory_monitor_c.exists():
        print(f"错误: 源文件不存在: {memory_monitor_c}")
        return False
    
    if not plthook_win32_c.exists():
        print(f"错误: 源文件不存在: {plthook_win32_c}")
        return False
    
    # 检查编译器
    if not check_compiler_in_path():
        print("Visual Studio 编译器未在 PATH 中找到，正在搜索安装...")
        
        vs_path = find_visual_studio()
        if not vs_path:
            return False
        
        print(f"找到 Visual Studio: {vs_path}")
        
        try:
            env = setup_vs_environment(vs_path, arch)
            print(f"已设置 {arch} 架构环境")
        except Exception as e:
            print(f"设置环境失败: {e}")
            return False
    else:
        print("Visual Studio 编译器已在 PATH 中")
        env = os.environ.copy()
    
    # 构建编译命令
    cmd = [
        "cl",
        "/nologo",
        f"/{optimization}",
        f"/I{script_dir.parent}",  # 包含父目录
        str(memory_monitor_c),
        str(plthook_win32_c),
        "/Fememory_monitor.exe",
        "dbghelp.lib",
        "psapi.lib",
        "kernel32.lib"
    ]
    
    if debug:
        cmd.extend(["/Zi", "/DEBUG"])
    
    # 添加更多优化选项
    if optimization == "O2":
        cmd.extend(["/Ot", "/Oi", "/GL"])  # 时间优化、内联、全局优化
    
    print("构建内存监控程序...")
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=script_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print("构建失败!")
            print(f"错误输出: {result.stderr}")
            return False
        
        print("构建成功!")
        
        # 复制到输出目录
        exe_path = script_dir / "memory_monitor.exe"
        if exe_path.exists():
            # 默认输出目录
            if output_dir is None:
                output_dir = script_dir.parent / "output" / "windows" / arch
            
            if output_dir.exists():
                shutil.copy2(exe_path, output_dir)
                print(f"已复制到输出目录: {output_dir}")
            else:
                print(f"输出目录不存在: {output_dir}")
                
            # 复制到测试目录
            test_output_dir = script_dir.parent / "test"
            if test_output_dir.exists():
                shutil.copy2(exe_path, test_output_dir / "memory_monitor_win.exe")
                print(f"已复制到测试目录: {test_output_dir}")
        
        return True
        
    except Exception as e:
        print(f"构建异常: {e}")
        return False


def show_usage():
    """显示使用示例"""
    print()
    print("使用示例:")
    print("  memory_monitor.exe -h                    显示帮助")
    print("  memory_monitor.exe -t -r 30              运行测试 30 秒")
    print("  memory_monitor.exe -i 10 -d              每 10 秒监控一次，详细日志")
    print("  memory_monitor.exe                       连续监控，每 5 秒一次")


def run_tests(test_duration: int = 10) -> bool:
    """运行内存监控测试"""
    script_dir = Path(__file__).parent.absolute()
    exe_path = script_dir / "memory_monitor.exe"
    
    if not exe_path.exists():
        print("错误: memory_monitor.exe 不存在，请先构建")
        return False
    
    print(f"运行内存监控测试 ({test_duration} 秒)...")
    
    try:
        # 运行内存监控程序
        result = subprocess.run(
            [str(exe_path), "-t", "-r", str(test_duration)],
            cwd=script_dir,
            timeout=test_duration + 5,  # 额外 5 秒超时
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print("✓ 内存监控测试通过")
            if result.stdout.strip():
                print("输出:")
                print(result.stdout)
            return True
        else:
            print("✗ 内存监控测试失败")
            if result.stderr.strip():
                print("错误:")
                print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 测试超时")
        return False
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Windows 内存监控构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 默认构建
  %(prog)s --arch x86               # 构建 x86 版本
  %(prog)s --debug                  # 构建调试版本
  %(prog)s --clean                  # 清理构建产物
  %(prog)s --test                   # 构建并测试
  %(prog)s --output-dir ./bin       # 指定输出目录
        """
    )
    
    parser.add_argument(
        "--arch",
        choices=["x86", "x64", "arm64"],
        default="x64",
        help="目标架构 (默认: x64)"
    )
    
    parser.add_argument(
        "--optimization",
        choices=["Od", "O1", "O2", "Ox"],
        default="O2",
        help="优化级别 (默认: O2)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="构建调试版本"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理构建产物"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="构建后运行测试"
    )
    
    parser.add_argument(
        "--test-duration",
        type=int,
        default=10,
        help="测试持续时间 (秒，默认: 10)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="输出目录"
    )
    
    args = parser.parse_args()
    
    print("Memory Monitor Build Script for Windows")
    print("========================================")
    
    if args.clean:
        return 0 if build_memory_monitor(clean=True) else 1
    
    print(f"架构: {args.arch}")
    print(f"优化级别: {args.optimization}")
    print(f"调试模式: {args.debug}")
    if args.output_dir:
        print(f"输出目录: {args.output_dir}")
    
    # 构建
    success = build_memory_monitor(
        arch=args.arch,
        optimization=args.optimization,
        debug=args.debug,
        output_dir=args.output_dir
    )
    
    if not success:
        return 1
    
    # 运行测试
    if args.test:
        print("\n" + "=" * 40)
        print("运行测试")
        print("=" * 40)
        if not run_tests(args.test_duration):
            return 1
    
    # 显示使用示例
    show_usage()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
