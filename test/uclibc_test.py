#!/usr/bin/env python3
"""
uclibc 测试脚本 - Python实现
用于在 uclibc 环境下测试 PLTHook
"""

import os
import sys
import argparse
import subprocess
import urllib.request
import tarfile
import shutil
from pathlib import Path
from typing import Dict, Optional


class UclibcTester:
    """uclibc 测试器"""
    
    # 架构配置
    ARCH_CONFIGS = {
        "x86_64": {
            "arch": "x86-64-core-i7",
            "libc": "uclibc",
            "toolchain_ver": "stable-2018.11-1",
            "target_platform": "x86_64-buildroot-linux-uclibc"
        },
        "i686": {
            "arch": "x86-core2", 
            "libc": "uclibc",
            "toolchain_ver": "stable-2018.11-1",
            "target_platform": "i686-buildroot-linux-uclibc"
        }
    }
    
    def __init__(self, arch: str):
        if arch not in self.ARCH_CONFIGS:
            raise ValueError(f"不支持的架构: {arch}")
        
        self.arch = arch
        self.config = self.ARCH_CONFIGS[arch]
        self.script_dir = Path(__file__).parent.absolute()
        
        # 构建相关路径
        self.base_name = f"{self.config['arch']}--{self.config['libc']}--{self.config['toolchain_ver']}"
        self.toolchain_dir = self.script_dir / self.base_name
        self.sysroot = self.toolchain_dir / self.config['target_platform'] / "sysroot"
        self.tarball_path = self.script_dir / f"{self.base_name}.tar.bz2"
        
    def download_toolchain(self):
        """下载工具链"""
        if self.tarball_path.exists():
            print(f"发现 {self.tarball_path.name}")
            return
        
        url = f"https://toolchains.bootlin.com/downloads/releases/toolchains/{self.config['arch']}/tarballs/{self.base_name}.tar.bz2"
        print(f"下载 {self.tarball_path.name}")
        print(f"URL: {url}")
        
        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(self.tarball_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r下载进度: {percent:.1f}%", end='', flush=True)
                
                print(f"\n下载完成: {self.tarball_path}")
                
        except Exception as e:
            print(f"下载失败: {e}")
            if self.tarball_path.exists():
                self.tarball_path.unlink()
            raise
    
    def extract_toolchain(self):
        """解压工具链"""
        if self.toolchain_dir.exists():
            print(f"发现 {self.toolchain_dir.name}")
            return
        
        print(f"解压 {self.tarball_path.name}")
        try:
            with tarfile.open(self.tarball_path, 'r:bz2') as tar:
                tar.extractall(self.script_dir)
            print(f"解压完成: {self.toolchain_dir}")
        except Exception as e:
            print(f"解压失败: {e}")
            if self.toolchain_dir.exists():
                shutil.rmtree(self.toolchain_dir)
            raise
    
    def setup_sysroot(self):
        """设置 sysroot"""
        proc_self = self.sysroot / "proc" / "self"
        if proc_self.exists():
            print(f"发现 {proc_self}")
            return
        
        print(f"挂载 {self.sysroot}/proc")
        try:
            # 创建 proc 目录
            proc_dir = self.sysroot / "proc"
            proc_dir.mkdir(exist_ok=True)
            
            # 尝试挂载 proc 文件系统 (需要 sudo 权限)
            subprocess.run([
                "sudo", "mount", "-t", "proc", "none", str(proc_dir)
            ], check=True)
            
            print(f"挂载完成: {proc_dir}")
            
        except subprocess.CalledProcessError as e:
            print(f"挂载失败: {e}")
            print("注意: 这可能需要 sudo 权限")
            raise
        except Exception as e:
            print(f"设置 sysroot 失败: {e}")
            raise
    
    def run_make(self):
        """运行 make 构建"""
        print("运行 make relro_pie_tests...")
        
        # 设置环境变量
        env = os.environ.copy()
        env["SYSROOT"] = str(self.sysroot)
        env["PATH"] = f"{self.toolchain_dir}/bin:{env.get('PATH', '')}"
        env["RUN_AS_KICK_CMD"] = "1"
        
        # 构建 make 命令
        cmd = [
            "make", 
            "relro_pie_tests",
            f"TARGET_PLATFORM={self.config['target_platform']}",
            f"KICK_CMD={sys.argv[0]}"
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        print(f"工作目录: {self.script_dir}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.script_dir,
                env=env,
                check=True
            )
            
            print("构建完成")
            return result.returncode
            
        except subprocess.CalledProcessError as e:
            print(f"构建失败: {e}")
            return e.returncode
        except Exception as e:
            print(f"构建异常: {e}")
            return 1
    
    def kick_cmd(self):
        """kick 命令处理 - 在 chroot 环境中运行"""
        print("执行 kick 命令...")
        
        try:
            # 复制文件到 sysroot
            test_files = [
                ("testprog", "/usr/bin/testprog"),
                ("libtest.so", "/usr/lib/libtest.so")
            ]
            
            for src_name, dst_path in test_files:
                src_path = self.script_dir / src_name
                dst_full_path = self.sysroot / dst_path.lstrip('/')
                
                if src_path.exists():
                    dst_full_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_full_path)
                    print(f"复制: {src_name} -> {dst_path}")
                else:
                    print(f"警告: 源文件不存在: {src_path}")
            
            # 在 chroot 环境中运行测试
            chroot_cmd = [
                "sudo", "chroot", str(self.sysroot),
                "/usr/bin/testprog", "open"
            ]
            
            print(f"执行 chroot 命令: {' '.join(chroot_cmd)}")
            
            result = subprocess.run(chroot_cmd, check=True)
            print("测试完成")
            return result.returncode
            
        except subprocess.CalledProcessError as e:
            print(f"kick 命令失败: {e}")
            return e.returncode
        except Exception as e:
            print(f"kick 命令异常: {e}")
            return 1
    
    def cleanup(self):
        """清理资源"""
        try:
            # 卸载 proc 文件系统
            proc_dir = self.sysroot / "proc"
            if proc_dir.exists():
                print(f"卸载 {proc_dir}")
                subprocess.run([
                    "sudo", "umount", str(proc_dir)
                ], check=False)  # 不强制要求成功
        except Exception as e:
            print(f"清理失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="uclibc 测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s x86_64
  %(prog)s i686
        """
    )
    
    parser.add_argument(
        "arch",
        choices=["x86_64", "i686"],
        help="目标架构"
    )
    
    parser.add_argument(
        "--kick-cmd",
        action="store_true",
        help="执行 kick 命令 (内部使用)"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true", 
        help="清理资源"
    )
    
    args = parser.parse_args()
    
    print(f"uclibc 测试脚本 - {args.arch}")
    print("=" * 30)
    
    try:
        tester = UclibcTester(args.arch)
        
        if args.cleanup:
            tester.cleanup()
            return 0
        
        if args.kick_cmd:
            return tester.kick_cmd()
        
        # 正常流程
        tester.download_toolchain()
        tester.extract_toolchain()
        tester.setup_sysroot()
        return tester.run_make()
        
    except KeyboardInterrupt:
        print("\n用户中断")
        return 1
    except Exception as e:
        print(f"执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
