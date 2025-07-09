#!/usr/bin/env python3
"""
PLTHook 发布构建脚本
自动化构建多平台的 PLTHook 库和测试程序
"""

import os
import sys
import subprocess
import shutil
import argparse
import json
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime

class PLTHookBuilder:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.build_dir = self.root_dir / "build"
        self.output_dir = self.root_dir / "output"
        self.release_dir = self.root_dir / "release"
        
    def clean(self):
        """清理构建目录"""
        print("🧹 清理构建目录...")
        
        dirs_to_clean = [self.build_dir, self.output_dir, self.release_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   清理: {dir_path}")
        
        # 清理测试目录
        test_dir = self.root_dir / "test"
        patterns = ["*.dll", "*.exe", "*.so", "*.dylib", "*.lib", "*.obj", "testprog"]
        for pattern in patterns:
            for file_path in test_dir.glob(pattern):
                file_path.unlink()
                print(f"   删除: {file_path}")
                
        print("✅ 清理完成")
    
    def detect_platform(self):
        """检测当前平台"""
        import platform
        system = platform.system().lower()
        
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    def run_command(self, cmd, cwd=None, shell=False):
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                shell=shell, 
                capture_output=True, 
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ 命令执行失败: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            print(f"   错误输出: {e.stderr}")
            return False, e.stderr
    
    def build_windows(self, arch="x64"):
        """构建 Windows 版本"""
        print(f"🔨 构建 Windows {arch}...")
        
        # 使用 PowerShell 脚本构建
        build_script = self.root_dir / "build.ps1"
        if not build_script.exists():
            print("❌ 未找到 Windows 构建脚本")
            return False
        
        cmd = [
            "powershell", "-ExecutionPolicy", "Bypass", "-File", str(build_script),
            "-Platform", "windows", "-Architecture", arch
        ]
        
        success, output = self.run_command(cmd, cwd=self.root_dir)
        if success:
            print("✅ Windows 构建完成")
            return True
        else:
            print(f"❌ Windows 构建失败: {output}")
            return False
    
    def build_linux(self, arch="x86_64"):
        """构建 Linux 版本"""
        print(f"🔨 构建 Linux {arch}...")
        
        build_dir = self.build_dir / f"linux-{arch}"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用 CMake 构建
        cmake_cmd = [
            "cmake", str(self.root_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_TESTS=ON",
            f"-DCMAKE_INSTALL_PREFIX={self.output_dir / f'linux-{arch}'}"
        ]
        
        success, _ = self.run_command(cmake_cmd, cwd=build_dir)
        if not success:
            return False
        
        make_cmd = ["make", "-j", str(os.cpu_count() or 4)]
        success, _ = self.run_command(make_cmd, cwd=build_dir)
        if not success:
            return False
        
        install_cmd = ["make", "install"]
        success, _ = self.run_command(install_cmd, cwd=build_dir)
        
        if success:
            print("✅ Linux 构建完成")
            return True
        else:
            print("❌ Linux 构建失败")
            return False
    
    def build_android(self, ndk_path, arch="arm64"):
        """构建 Android 版本"""
        print(f"🔨 构建 Android {arch}...")
        
        if not ndk_path or not Path(ndk_path).exists():
            print("❌ Android NDK 路径无效")
            return False
        
        # 架构映射
        abi_map = {
            "arm64": "arm64-v8a",
            "armv7": "armeabi-v7a",
            "x86_64": "x86_64"
        }
        
        android_abi = abi_map.get(arch, "arm64-v8a")
        build_dir = self.build_dir / f"android-{arch}"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用 CMake + NDK
        cmake_cmd = [
            "cmake", str(self.root_dir),
            f"-DCMAKE_TOOLCHAIN_FILE={ndk_path}/build/cmake/android.toolchain.cmake",
            f"-DANDROID_ABI={android_abi}",
            "-DANDROID_PLATFORM=android-21",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_ANDROID=ON",
            "-DBUILD_TESTS=ON",
            f"-DCMAKE_INSTALL_PREFIX={self.output_dir / f'android-{arch}'}"
        ]
        
        success, _ = self.run_command(cmake_cmd, cwd=build_dir)
        if not success:
            return False
        
        make_cmd = ["make", "-j", str(os.cpu_count() or 4)]
        success, _ = self.run_command(make_cmd, cwd=build_dir)
        if not success:
            return False
        
        install_cmd = ["make", "install"]
        success, _ = self.run_command(install_cmd, cwd=build_dir)
        
        if success:
            print("✅ Android 构建完成")
            return True
        else:
            print("❌ Android 构建失败")
            return False
    
    def run_tests(self, platform, arch):
        """运行测试"""
        print(f"🧪 运行 {platform} {arch} 测试...")
        
        output_path = self.output_dir / f"{platform}-{arch}"
        if not output_path.exists():
            print(f"❌ 构建输出不存在: {output_path}")
            return False
        
        if platform == "windows":
            test_script = self.root_dir / "test" / "run_tests_windows.bat"
            if test_script.exists():
                success, _ = self.run_command([str(test_script)], cwd=output_path / "bin")
            else:
                # 直接运行测试程序
                testprog = output_path / "bin" / "testprog.exe"
                if testprog.exists():
                    success1, _ = self.run_command([str(testprog), "open"], cwd=output_path / "bin")
                    success2, _ = self.run_command([str(testprog), "open_by_handle"], cwd=output_path / "bin")
                    success = success1 and success2
                else:
                    success = False
        
        elif platform == "android":
            print("⚠️  Android 测试需要在设备上运行")
            return True
        
        else:  # Linux/macOS
            testprog = output_path / "bin" / "testprog"
            if testprog.exists():
                # 设置库路径
                lib_path = output_path / "lib"
                env = os.environ.copy()
                if platform == "linux":
                    env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
                elif platform == "macos":
                    env["DYLD_LIBRARY_PATH"] = f"{lib_path}:{env.get('DYLD_LIBRARY_PATH', '')}"
                
                # 运行测试
                tests = ["open", "open_by_handle", "open_by_address"]
                success = True
                for test in tests:
                    result = subprocess.run([str(testprog), test], cwd=output_path / "bin", env=env)
                    if result.returncode != 0:
                        success = False
                        break
            else:
                success = False
        
        if success:
            print("✅ 测试通过")
        else:
            print("❌ 测试失败")
        
        return success
    
    def create_release_package(self, platforms):
        """创建发布包"""
        print("📦 创建发布包...")
        
        self.release_dir.mkdir(exist_ok=True)
        version = "1.2.0"  # 可以从配置文件读取
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 创建每个平台的压缩包
        for platform_arch in platforms:
            parts = platform_arch.split("-")
            if len(parts) != 2:
                continue
                
            platform, arch = parts
            output_path = self.output_dir / platform_arch
            
            if not output_path.exists():
                print(f"⚠️  跳过不存在的构建: {platform_arch}")
                continue
            
            # 创建临时目录
            temp_dir = self.release_dir / f"plthook-{version}-{platform_arch}"
            temp_dir.mkdir(exist_ok=True)
            
            # 复制文件
            if (output_path / "lib").exists():
                shutil.copytree(output_path / "lib", temp_dir / "lib", dirs_exist_ok=True)
            if (output_path / "bin").exists():
                shutil.copytree(output_path / "bin", temp_dir / "bin", dirs_exist_ok=True)
            if (output_path / "include").exists():
                shutil.copytree(output_path / "include", temp_dir / "include", dirs_exist_ok=True)
            
            # 复制文档
            docs = ["README.md", "BUILD_GUIDE.md", "plthook.h"]
            for doc in docs:
                doc_path = self.root_dir / doc
                if doc_path.exists():
                    shutil.copy2(doc_path, temp_dir)
            
            # 创建压缩包
            if platform == "windows":
                archive_name = f"plthook-{version}-{platform_arch}-{date_str}.zip"
                archive_path = self.release_dir / archive_name
                
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in temp_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_dir)
                            zf.write(file_path, arcname)
            else:
                archive_name = f"plthook-{version}-{platform_arch}-{date_str}.tar.gz"
                archive_path = self.release_dir / archive_name
                
                with tarfile.open(archive_path, 'w:gz') as tf:
                    tf.add(temp_dir, arcname=f"plthook-{version}-{platform_arch}")
            
            print(f"   创建: {archive_name}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
        
        print("✅ 发布包创建完成")
    
    def generate_build_info(self, platforms):
        """生成构建信息文件"""
        build_info = {
            "version": "1.2.0",
            "build_date": datetime.now().isoformat(),
            "platforms": platforms,
            "builder": "PLTHook Release Builder",
            "source_commit": self.get_git_commit(),
        }
        
        info_file = self.release_dir / "build_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
        
        print(f"📋 构建信息已保存: {info_file}")
    
    def get_git_commit(self):
        """获取 Git 提交哈希"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                capture_output=True, 
                text=True, 
                cwd=self.root_dir
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

def main():
    parser = argparse.ArgumentParser(description="PLTHook 发布构建脚本")
    parser.add_argument("--platforms", nargs="+", 
                       help="要构建的平台 (格式: platform-arch)",
                       default=["windows-x64", "linux-x86_64", "android-arm64"])
    parser.add_argument("--android-ndk", help="Android NDK 路径")
    parser.add_argument("--clean", action="store_true", help="清理构建目录")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--package", action="store_true", help="创建发布包")
    parser.add_argument("--all", action="store_true", help="执行完整构建流程")
    
    args = parser.parse_args()
    
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    builder = PLTHookBuilder(script_dir)
    
    print("🚀 PLTHook 发布构建器启动")
    print("=" * 40)
    
    if args.clean or args.all:
        builder.clean()
    
    if args.all:
        args.test = True
        args.package = True
    
    success_builds = []
    
    for platform_arch in args.platforms:
        parts = platform_arch.split("-")
        if len(parts) != 2:
            print(f"❌ 无效的平台格式: {platform_arch}")
            continue
        
        platform, arch = parts
        
        print(f"\n📍 构建 {platform_arch}...")
        
        if platform == "windows":
            success = builder.build_windows(arch)
        elif platform == "linux":
            success = builder.build_linux(arch)
        elif platform == "android":
            if not args.android_ndk:
                print("❌ 构建 Android 需要指定 --android-ndk 参数")
                continue
            success = builder.build_android(args.android_ndk, arch)
        else:
            print(f"❌ 不支持的平台: {platform}")
            continue
        
        if success:
            success_builds.append(platform_arch)
            
            if args.test:
                builder.run_tests(platform, arch)
    
    if args.package and success_builds:
        builder.create_release_package(success_builds)
        builder.generate_build_info(success_builds)
    
    print("\n" + "=" * 40)
    print(f"🎉 构建完成! 成功构建了 {len(success_builds)} 个平台:")
    for platform_arch in success_builds:
        print(f"   ✅ {platform_arch}")
    
    if success_builds != args.platforms:
        failed = set(args.platforms) - set(success_builds)
        print(f"\n❌ 构建失败的平台: {', '.join(failed)}")

if __name__ == "__main__":
    main()
