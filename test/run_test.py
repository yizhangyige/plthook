#!/usr/bin/env python3
"""
Windows Visual Studio 测试脚本 - Python实现
替代 run-test.bat 的功能
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


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


def setup_vs_environment(vs_path: Path, arch: str) -> Dict[str, Any]:
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


def run_make_command(arch: str, dll_cflags: str = "", exe_cflags: str = "") -> int:
    """运行 nmake 命令"""
    # 查找 Visual Studio
    vs_path = find_visual_studio()
    if not vs_path:
        return 1
    
    print(f"找到 Visual Studio: {vs_path}")
    
    try:
        # 设置 VS 环境
        env = setup_vs_environment(vs_path, arch)
        print(f"已设置 {arch} 架构环境")
        
        # 构建 nmake 命令
        cmd = ["nmake", "/f", "Makefile.win32", "check", "clean"]
        
        if dll_cflags:
            cmd.append(f"DLL_CFLAGS={dll_cflags}")
        
        if exe_cflags:
            cmd.append(f"EXE_CFLAGS={exe_cflags}")
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 运行命令
        result = subprocess.run(
            cmd,
            env=env,
            check=False
        )
        
        return result.returncode
        
    except Exception as e:
        print(f"执行失败: {e}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Windows Visual Studio 测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s x64
  %(prog)s x86 "/Od /Zi" "/Od /Zi"
  %(prog)s arm64 "/O2" "/O2"
        """
    )
    
    parser.add_argument(
        "arch",
        choices=["x86", "x64", "arm64"],
        help="目标架构"
    )
    
    parser.add_argument(
        "dll_cflags",
        nargs="?",
        default="",
        help="DLL 编译选项"
    )
    
    parser.add_argument(
        "exe_cflags", 
        nargs="?",
        default="",
        help="EXE 编译选项"
    )
    
    args = parser.parse_args()
    
    print("Windows Visual Studio 测试脚本")
    print("==============================")
    print(f"架构: {args.arch}")
    if args.dll_cflags:
        print(f"DLL 编译选项: {args.dll_cflags}")
    if args.exe_cflags:
        print(f"EXE 编译选项: {args.exe_cflags}")
    print()
    
    return run_make_command(args.arch, args.dll_cflags, args.exe_cflags)


if __name__ == "__main__":
    sys.exit(main())
