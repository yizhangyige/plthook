#!/usr/bin/env python3
"""
内存监控构建脚本 - Python 版本
用于构建 Windows 平台的内存监控程序
"""

import os
import sys
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from typing import Optional, Dict

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

def find_visual_studio() -> Optional[Dict[str, str]]:
    """查找 Visual Studio 安装路径"""
    try:
        # 查找 vswhere.exe
        vswhere_paths = [
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft Visual Studio', 'Installer', 'vswhere.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft Visual Studio', 'Installer', 'vswhere.exe')
        ]
        
        vswhere_path = None
        for path in vswhere_paths:
            if os.path.exists(path):
                vswhere_path = path
                break
        
        if not vswhere_path:
            return None
        
        # 获取 VS 安装信息
        cmd = [
            vswhere_path, 
            '-latest', 
            '-products', '*',
            '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
            '-format', 'json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.returncode == 0 and result.stdout:
            installations = json.loads(result.stdout)
            if installations:
                install_path = installations[0].get('installationPath')
                if install_path:
                    vcvars_path = os.path.join(
                        install_path, 'VC', 'Auxiliary', 'Build', 'vcvarsall.bat'
                    )
                    if os.path.exists(vcvars_path):
                        return {
                            'installPath': install_path,
                            'vcvarsPath': vcvars_path
                        }
        
        return None
    except Exception as e:
        print_colored(f"查找 Visual Studio 时出错: {e}", Colors.RED)
        return None

def run_command_with_vcvars(vcvars_path: str, arch: str, command: str, cwd: str = None) -> bool:
    """使用 Visual Studio 环境运行命令"""
    full_cmd = f'"{vcvars_path}" {arch} && {command}'
    
    print_colored(f"执行命令: {full_cmd}", Colors.CYAN)
    
    try:
        result = subprocess.run(full_cmd, shell=True, cwd=cwd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_colored(f"命令执行失败，退出代码: {e.returncode}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"执行命令时出错: {e}", Colors.RED)
        return False

def build_memory_monitor(arch: str, vs_info: Dict[str, str], work_dir: str) -> bool:
    """构建内存监控程序"""
    print_colored(f"构建内存监控程序 ({arch})...", Colors.YELLOW)
    
    vcvars_path = vs_info['vcvarsPath']
    print_colored(f"找到 Visual Studio: {vs_info['installPath']}", Colors.YELLOW)
    
    # 检查源文件
    source_files = [
        "memory_monitor_win.c",
        "../plthook_win32.c"
    ]
    
    for source_file in source_files:
        source_path = os.path.join(work_dir, source_file)
        if not os.path.exists(source_path):
            print_colored(f"错误: 源文件不存在: {source_path}", Colors.RED)
            return False
    
    # 构建编译命令
    compile_cmd = (
        "cl /nologo /O2 /I.. memory_monitor_win.c ../plthook_win32.c "
        "/Fememory_monitor_win.exe dbghelp.lib psapi.lib kernel32.lib"
    )
    
    print_colored("设置 Visual Studio 环境并编译...", Colors.YELLOW)
    
    # 执行构建
    success = run_command_with_vcvars(vcvars_path, arch, compile_cmd, work_dir)
    
    if success:
        print_colored("构建成功!", Colors.GREEN)
        
        # 检查生成的可执行文件
        exe_path = os.path.join(work_dir, "memory_monitor_win.exe")
        if os.path.exists(exe_path):
            # 复制到输出目录
            root_dir = os.path.dirname(work_dir)
            output_dir = os.path.join(root_dir, "output", "windows", arch)
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                shutil.copy2(exe_path, output_dir)
                print_colored(f"已复制到输出目录: {output_dir}", Colors.GREEN)
                
                # 显示文件信息
                exe_size = os.path.getsize(exe_path) / 1024
                print_colored(f"生成文件: memory_monitor_win.exe ({exe_size:.2f} KB)", Colors.GRAY)
                
                return True
            except Exception as e:
                print_colored(f"复制文件失败: {e}", Colors.RED)
                return False
        else:
            print_colored("错误: 编译成功但未找到生成的可执行文件", Colors.RED)
            return False
    else:
        print_colored("构建失败!", Colors.RED)
        return False

def clean_build_artifacts(work_dir: str) -> None:
    """清理构建产物"""
    print_colored("清理构建产物...", Colors.YELLOW)
    
    patterns = ["*.exe", "*.obj", "*.pdb", "*.ilk"]
    
    for pattern in patterns:
        for file_path in Path(work_dir).glob(pattern):
            try:
                file_path.unlink()
                print_colored(f"已删除: {file_path}", Colors.GRAY)
            except Exception as e:
                print_colored(f"删除文件失败 {file_path}: {e}", Colors.RED)
    
    print_colored("清理完成", Colors.GREEN)

def show_usage_examples():
    """显示使用示例"""
    print()
    print_colored("使用示例:", Colors.YELLOW)
    print_colored("  # 监控指定进程", Colors.GRAY)
    print_colored("  memory_monitor_win.exe <process_name>", Colors.GRAY)
    print()
    print_colored("  # 监控系统内存", Colors.GRAY)
    print_colored("  memory_monitor_win.exe --system", Colors.GRAY)
    print()
    print_colored("  # 详细监控模式", Colors.GRAY)
    print_colored("  memory_monitor_win.exe --verbose <process_name>", Colors.GRAY)

def main():
    parser = argparse.ArgumentParser(description='Windows 内存监控构建脚本')
    parser.add_argument('--arch', 
                       choices=['x86', 'x64', 'arm64'],
                       default='x64',
                       help='目标架构')
    parser.add_argument('--clean', action='store_true',
                       help='清理构建产物')
    
    args = parser.parse_args()
    
    print_colored("Memory Monitor Build Script for Windows", Colors.GREEN + Colors.BOLD)
    print_colored("=======================================", Colors.GREEN)
    
    # 获取工作目录（脚本所在的 test 目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = script_dir if os.path.basename(script_dir) == 'test' else os.path.join(script_dir, 'test')
    
    if not os.path.exists(work_dir):
        print_colored(f"错误: 工作目录不存在: {work_dir}", Colors.RED)
        sys.exit(1)
    
    try:
        if args.clean:
            clean_build_artifacts(work_dir)
            return
        
        # 查找 Visual Studio
        vs_info = find_visual_studio()
        if not vs_info:
            print_colored("错误: 未找到 Visual Studio", Colors.RED)
            print_colored("请安装 Visual Studio 2019 或更高版本，并确保包含 C++ 工具", Colors.RED)
            sys.exit(1)
        
        # 构建内存监控程序
        success = build_memory_monitor(args.arch, vs_info, work_dir)
        
        if success:
            show_usage_examples()
            print()
            print_colored("构建完成!", Colors.GREEN)
        else:
            print_colored("构建失败!", Colors.RED)
            sys.exit(1)
        
    except KeyboardInterrupt:
        print_colored("\n构建被用户中断", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"构建失败: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
