#!/usr/bin/env python3
"""
PLTHook Windows 构建脚本 - Python 版本
支持多架构构建和自动化测试
"""

import os
import sys
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict

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
        vswhere_path = os.path.join(
            os.environ.get('PROGRAMFILES(X86)', ''),
            'Microsoft Visual Studio', 'Installer', 'vswhere.exe'
        )
        
        if not os.path.exists(vswhere_path):
            return None
        
        # 获取最新的 VS 安装信息
        cmd = [vswhere_path, '-latest', '-format', 'json']
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

def run_command(cmd: str, cwd: str = None, shell: bool = True) -> bool:
    """运行命令并返回成功状态"""
    print_colored(f"执行命令: {cmd}", Colors.CYAN)
    
    try:
        result = subprocess.run(cmd, shell=shell, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"命令执行失败，退出代码: {e.returncode}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"执行命令时出错: {e}", Colors.RED)
        return False

def clean_build_directories(root_dir: str) -> None:
    """清理构建目录"""
    print_colored("清理构建目录...", Colors.YELLOW)
    
    # 清理主构建目录
    build_dir = os.path.join(root_dir, "build")
    output_dir = os.path.join(root_dir, "output")
    
    for dir_path in [build_dir, output_dir]:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print_colored(f"已删除: {dir_path}", Colors.GRAY)
            except Exception as e:
                print_colored(f"删除目录失败 {dir_path}: {e}", Colors.RED)
    
    # 清理测试目录中的构建产物
    test_dir = os.path.join(root_dir, "test")
    if os.path.exists(test_dir):
        patterns = ["*.dll", "*.exe", "*.lib", "*.exp", "*.obj", "*.so"]
        
        for pattern in patterns:
            for file_path in Path(test_dir).glob(pattern):
                try:
                    file_path.unlink()
                    print_colored(f"已删除: {file_path}", Colors.GRAY)
                except Exception as e:
                    print_colored(f"删除文件失败 {file_path}: {e}", Colors.RED)
    
    print_colored("清理完成", Colors.GREEN)

def get_vcvars_arch(arch: str) -> str:
    """获取 vcvarsall.bat 的架构参数"""
    arch_map = {
        "x86": "x86",
        "x64": "x64", 
        "arm64": "arm64"
    }
    return arch_map.get(arch, "x64")

def build_windows(arch: str, vs_info: Dict[str, str], root_dir: str) -> bool:
    """构建 Windows 平台"""
    print_colored(f"构建 Windows {arch} 平台...", Colors.YELLOW)
    
    # 创建输出目录
    win_output_dir = os.path.join(root_dir, "output", "windows", arch)
    os.makedirs(win_output_dir, exist_ok=True)
    
    vcvars_path = vs_info['vcvarsPath']
    vcvars_arch = get_vcvars_arch(arch)
    
    print_colored(f"找到 Visual Studio: {vs_info['installPath']}", Colors.GREEN)
    
    test_dir = os.path.join(root_dir, "test")
    
    # 构建命令：先设置环境然后编译
    build_cmd = f'"{vcvars_path}" {vcvars_arch} && nmake /f Makefile.win32 all'
    
    print_colored(f"执行构建命令: {build_cmd}", Colors.CYAN)
    
    # 切换到测试目录执行构建
    success = run_command(build_cmd, cwd=test_dir)
    
    if not success:
        print_colored(f"Windows {arch} 构建失败", Colors.RED)
        return False
    
    # 复制构建产物
    try:
        artifacts = ["libtest.dll", "testprog.exe", "libtest.lib"]
        copied_files = []
        
        for artifact in artifacts:
            src_path = os.path.join(test_dir, artifact)
            if os.path.exists(src_path):
                dst_path = os.path.join(win_output_dir, artifact)
                shutil.copy2(src_path, dst_path)
                copied_files.append(artifact)
                print_colored(f"已复制: {artifact}", Colors.GRAY)
        
        if copied_files:
            print_colored(f"Windows {arch} 构建完成", Colors.GREEN)
            print_colored(f"输出目录: {win_output_dir}", Colors.GREEN)
            return True
        else:
            print_colored(f"警告: 没有找到构建产物", Colors.YELLOW)
            return False
            
    except Exception as e:
        print_colored(f"复制构建产物失败: {e}", Colors.RED)
        return False

def run_windows_tests(arch: str, root_dir: str) -> bool:
    """运行 Windows 测试"""
    win_output_dir = os.path.join(root_dir, "output", "windows", arch)
    
    if not os.path.exists(win_output_dir):
        print_colored(f"Windows {arch} 构建产物未找到，跳过测试", Colors.YELLOW)
        return False
    
    print_colored(f"运行 Windows {arch} 测试...", Colors.YELLOW)
    
    testprog_path = os.path.join(win_output_dir, "testprog.exe")
    if not os.path.exists(testprog_path):
        print_colored(f"测试程序不存在: {testprog_path}", Colors.RED)
        return False
    
    try:
        # 测试 open 模式
        print_colored("测试 open 模式...", Colors.CYAN)
        cmd = f'"{testprog_path}" open'
        if not run_command(cmd, cwd=win_output_dir):
            print_colored("open 模式测试失败", Colors.RED)
            return False
        
        # 测试 open_by_handle 模式
        print_colored("测试 open_by_handle 模式...", Colors.CYAN)
        cmd = f'"{testprog_path}" open_by_handle'
        if not run_command(cmd, cwd=win_output_dir):
            print_colored("open_by_handle 模式测试失败", Colors.RED)
            return False
        
        print_colored(f"Windows {arch} 测试通过", Colors.GREEN)
        return True
        
    except Exception as e:
        print_colored(f"Windows {arch} 测试失败: {e}", Colors.RED)
        return False

def show_build_results(output_dir: str) -> None:
    """显示构建结果"""
    print()
    print_colored("构建结果:", Colors.YELLOW)
    
    if not os.path.exists(output_dir):
        print_colored("  无构建输出", Colors.GRAY)
        return
    
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(output_dir, '').count(os.sep)
        
        if level == 0:
            continue
            
        if level == 1:
            platform_name = os.path.basename(root)
            print_colored(f"  📁 {platform_name}/", Colors.CYAN)
        elif level == 2:
            arch_name = os.path.basename(root)
            print_colored(f"    📁 {arch_name}/", Colors.CYAN)
        
        if level >= 2:
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size_kb = os.path.getsize(file_path) / 1024
                    indent = "      " if level == 2 else "        "
                    print_colored(f"{indent}📄 {file} ({size_kb:.2f} KB)", Colors.GRAY)
                except:
                    indent = "      " if level == 2 else "        "
                    print_colored(f"{indent}📄 {file}", Colors.GRAY)

def main():
    parser = argparse.ArgumentParser(description='PLTHook Windows 构建脚本')
    parser.add_argument('--platform', 
                       choices=['windows', 'all'],
                       default='windows',
                       help='构建平台')
    parser.add_argument('--arch', 
                       choices=['x86', 'x64', 'arm64'],
                       default='x64',
                       help='目标架构')
    parser.add_argument('--clean', action='store_true',
                       help='清理构建目录')
    parser.add_argument('--no-test', action='store_true',
                       help='不运行测试')
    
    args = parser.parse_args()
    
    print_colored("PLTHook Build Script", Colors.GREEN + Colors.BOLD)
    print_colored("===================", Colors.GREEN)
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(script_dir, "build")
    output_dir = os.path.join(script_dir, "output")
    
    try:
        if args.clean:
            clean_build_directories(script_dir)
            return
        
        # 创建构建目录
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        success = True
        
        if args.platform in ['windows', 'all']:
            # 查找 Visual Studio
            vs_info = find_visual_studio()
            if not vs_info:
                print_colored("错误: 未找到 Visual Studio。请安装 Visual Studio 2019 或更高版本", Colors.RED)
                sys.exit(1)
            
            # 构建 Windows
            build_success = build_windows(args.arch, vs_info, script_dir)
            success &= build_success
            
            # 运行测试
            if build_success and not args.no_test:
                test_success = run_windows_tests(args.arch, script_dir)
                success &= test_success
        
        # 显示构建结果
        show_build_results(output_dir)
        
        print()
        if success:
            print_colored("构建完成!", Colors.GREEN)
            print_colored(f"输出目录: {output_dir}", Colors.GREEN)
        else:
            print_colored("构建过程中有错误发生", Colors.RED)
            sys.exit(1)
        
    except KeyboardInterrupt:
        print_colored("\n构建被用户中断", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"构建失败: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
