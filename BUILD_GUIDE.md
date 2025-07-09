# PLTHook 构建指南

本文档详细介绍如何在不同平台上构建 PLTHook 库和测试程序。

## 目录

- [概述](#概述)
- [环境要求](#环境要求)
- [构建方法](#构建方法)
  - [Windows 平台](#windows-平台)
  - [Android 平台](#android-平台)
  - [Linux 平台](#linux-平台)
  - [macOS 平台](#macos-平台)
- [测试验证](#测试验证)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

## 概述

PLTHook 是一个用于钩取库函数调用的工具库，通过修改 PLT (Procedure Linkage Table) 或 IAT (Import Address Table) 条目来实现函数拦截。本项目提供了多种构建方式：

- **PowerShell 脚本** (`build.ps1`): 主要用于 Windows 平台
- **Bash 脚本** (`build.sh`): 跨平台支持，包括 Linux、macOS、Windows (WSL)
- **CMake** (`CMakeLists.txt`): 现代化的跨平台构建系统
- **传统 Makefile**: 原始的构建方式

## 环境要求

### Windows 平台
- **必需**: Visual Studio 2019 或更高版本 (包含 MSVC 编译器)
- **可选**: Windows SDK (通常随 Visual Studio 安装)
- **PowerShell**: 5.1 或更高版本

### Android 平台
- **Android NDK**: r21 或更高版本
- **CMake**: 3.16 或更高版本
- **平台支持**: 
  - ARM64 (arm64-v8a)
  - ARMv7 (armeabi-v7a)
  - x86_64

### Linux 平台
- **GCC**: 7.0 或更高版本
- **Glibc**: 2.17 或更高版本
- **Make**: GNU Make 4.0+
- **CMake**: 3.16+ (可选)

### macOS 平台
- **Xcode**: 12.0 或更高版本
- **macOS**: 10.15+ (Catalina)
- **架构支持**: Intel x86_64, Apple Silicon (arm64)

## 构建方法

### Windows 平台

#### 方法 1: 使用 PowerShell 脚本 (推荐)

```powershell
# 构建 x64 版本
.\build.ps1 -Platform windows -Architecture x64

# 构建 x86 版本
.\build.ps1 -Platform windows -Architecture x86

# 构建 ARM64 版本
.\build.ps1 -Platform windows -Architecture arm64

# 清理构建目录
.\build.ps1 -Clean
```

#### 方法 2: 使用 CMake

```powershell
# 创建构建目录
mkdir build-windows
cd build-windows

# 配置项目 (x64)
cmake .. -A x64 -DBUILD_TESTS=ON

# 或者配置 x86
cmake .. -A Win32 -DBUILD_TESTS=ON

# 构建
cmake --build . --config Release

# 运行测试
ctest --config Release
```

#### 方法 3: 使用原生 Makefile

```cmd
cd test
nmake /f Makefile.win32 all
```

#### 构建产物

Windows 构建完成后，在 `output/windows/{arch}/` 目录下可以找到：
- `libtest.dll` - 测试用的共享库
- `testprog.exe` - 测试程序
- `libtest.lib` - 导入库 (MSVC)

### Android 平台

#### 准备工作

1. 下载并安装 Android NDK:
   ```bash
   # 设置 NDK 路径环境变量
   export ANDROID_NDK_ROOT=/path/to/android-ndk
   ```

2. 确保 CMake 已安装并在 PATH 中。

#### 方法 1: 使用跨平台脚本

```bash
# 构建 ARM64 版本
./build.sh -p android -a arm64 -n /path/to/android-ndk

# 构建 ARMv7 版本
./build.sh -p android -a armv7 -n /path/to/android-ndk

# 构建 x86_64 版本 (用于模拟器)
./build.sh -p android -a x86_64 -n /path/to/android-ndk
```

#### 方法 2: 使用 CMake

```bash
mkdir build-android-arm64
cd build-android-arm64

cmake .. \
    -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake \
    -DANDROID_ABI=arm64-v8a \
    -DANDROID_PLATFORM=android-21 \
    -DBUILD_ANDROID=ON \
    -DBUILD_TESTS=ON

make -j$(nproc)
```

#### 方法 3: 使用 NDK-Build (传统方式)

```bash
cd test/android
$ANDROID_NDK_ROOT/ndk-build clean
$ANDROID_NDK_ROOT/ndk-build
```

#### 构建产物

Android 构建完成后，在相应的输出目录下可以找到：
- `lib/{abi}/libplthook.so` - PLTHook 共享库
- `lib/{abi}/libtest.so` - 测试用共享库
- `bin/testprog` - 测试程序

### Linux 平台

#### 方法 1: 使用跨平台脚本

```bash
# 自动检测并构建
./build.sh -p linux -r

# 指定架构构建
./build.sh -p linux -a x86_64 -r
./build.sh -p linux -a arm64 -r
```

#### 方法 2: 使用 CMake

```bash
mkdir build-linux
cd build-linux

cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON
make -j$(nproc)
make install

# 运行测试
ctest
```

#### 方法 3: 使用原生 Makefile

```bash
cd test
make all
make check
```

### macOS 平台

#### 方法 1: 使用跨平台脚本

```bash
# Intel Mac
./build.sh -p macos -a x86_64 -r

# Apple Silicon Mac
./build.sh -p macos -a arm64 -r

# 通用二进制 (需要额外配置)
./build.sh -p macos -r
```

#### 方法 2: 使用 CMake

```bash
mkdir build-macos
cd build-macos

# Intel 版本
cmake .. -DCMAKE_OSX_ARCHITECTURES=x86_64 -DBUILD_TESTS=ON

# Apple Silicon 版本
cmake .. -DCMAKE_OSX_ARCHITECTURES=arm64 -DBUILD_TESTS=ON

# 通用二进制
cmake .. -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" -DBUILD_TESTS=ON

make -j$(sysctl -n hw.ncpu)
```

## 测试验证

### 自动测试

大多数构建方法都支持自动运行测试：

```bash
# 使用构建脚本的测试选项
./build.sh -p auto -r

# 使用 CMake 的测试
cd build-directory
ctest --verbose

# 使用 Makefile 的测试
cd test
make check
```

### 手动测试

```bash
# 进入输出目录
cd output/{platform}-{arch}/bin

# 设置库路径 (Linux/macOS)
export LD_LIBRARY_PATH=../lib:$LD_LIBRARY_PATH  # Linux
export DYLD_LIBRARY_PATH=../lib:$DYLD_LIBRARY_PATH  # macOS

# 运行测试
./testprog open
./testprog open_by_handle
./testprog open_by_address  # Windows 下不支持
```

### 测试内容

测试程序验证以下功能：
1. **open**: 通过文件名打开库并钩取函数
2. **open_by_handle**: 通过句柄打开库并钩取函数
3. **open_by_address**: 通过地址打开库并钩取函数 (仅 Unix)

## 常见问题

### Windows 相关

**Q: 找不到 Visual Studio 或 MSVC 编译器**
```
A: 确保安装了 Visual Studio 2019+ 并包含 C++ 工具。
   运行 build.ps1 时会自动检测 VS 安装路径。
```

**Q: 链接错误 LNK2019**
```
A: 检查是否正确包含了 dbghelp.lib。
   在 CMake 中已自动处理此依赖。
```

### Android 相关

**Q: NDK 路径错误**
```
A: 确保 NDK 路径正确，并且版本 ≥ r21。
   检查路径中包含 ndk-build 和 cmake 工具链。
```

**Q: 不支持的 ABI**
```
A: 当前支持的 ABI:
   - arm64-v8a (推荐用于现代设备)
   - armeabi-v7a (兼容较老设备)
   - x86_64 (用于模拟器)
```

### Linux 相关

**Q: 共享库找不到**
```
A: 设置正确的库路径:
   export LD_LIBRARY_PATH=/path/to/libs:$LD_LIBRARY_PATH
   
   或者使用 RPATH (CMake 自动设置):
   cmake .. -DCMAKE_INSTALL_RPATH='$ORIGIN'
```

**Q: 权限错误**
```
A: 确保构建脚本有执行权限:
   chmod +x build.sh
```

### macOS 相关

**Q: 代码签名问题**
```
A: 对于开发测试，可以临时禁用代码签名:
   export CODESIGN_ALLOCATE=/usr/bin/codesign_allocate
   
   或在 CMake 中添加:
   set(CMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_REQUIRED NO)
```

**Q: 架构不匹配**
```
A: 确保目标架构与系统匹配:
   - Intel Mac: 使用 x86_64
   - Apple Silicon: 使用 arm64
   - 通用二进制: 同时构建两种架构
```

## 高级配置

### 交叉编译

#### Windows 到 Linux (WSL)

```bash
# 在 WSL 中安装交叉编译工具
sudo apt-get install gcc-mingw-w64

# 使用构建脚本
./build.sh -p windows -a x86_64
```

#### Linux 到 ARM

```bash
# 安装 ARM 交叉编译工具链
sudo apt-get install gcc-aarch64-linux-gnu

# 配置 CMake
cmake .. \
    -DCMAKE_SYSTEM_NAME=Linux \
    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc
```

### 自定义构建选项

#### CMake 选项

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \          # 调试版本
    -DBUILD_SHARED_LIBS=OFF \           # 静态库
    -DBUILD_TESTS=OFF \                 # 不构建测试
    -DCMAKE_C_FLAGS="-O3 -march=native" # 优化选项
```

#### 环境变量

```bash
# 编译器标志
export CFLAGS="-Wall -Wextra -O2"
export LDFLAGS="-Wl,--strip-all"

# Android 特定
export ANDROID_PLATFORM=android-28
export ANDROID_STL=c++_shared
```

### 打包发布

#### 使用 CPack

```bash
cd build-directory
cpack -G ZIP      # Windows
cpack -G TGZ      # Linux/macOS
cpack -G DEB      # Debian 包
```

#### 手动打包

```bash
# 创建发布目录
mkdir plthook-release
cp -r output/* plthook-release/
cp README.md plthook-release/
cp LICENSE plthook-release/

# 创建压缩包
tar -czf plthook-$(date +%Y%m%d).tar.gz plthook-release/
```

## 性能优化

### 编译优化

```bash
# 最大优化
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-O3 -DNDEBUG"

# 针对特定 CPU 优化
cmake .. -DCMAKE_C_FLAGS="-O3 -march=native -mtune=native"

# 链接时优化 (LTO)
cmake .. -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON
```

### Android 优化

```bash
# 启用 ARM NEON (ARM64)
cmake .. -DANDROID_ARM_NEON=ON

# 使用 Clang LLD 链接器
cmake .. -DANDROID_LD=lld
```

---

## 总结

本文档提供了 PLTHook 在各个平台上的完整构建指南。根据你的目标平台选择合适的构建方法：

- **快速开始**: 使用提供的构建脚本
- **灵活配置**: 使用 CMake
- **传统方式**: 使用原生 Makefile

如有问题，请参考常见问题部分或查看项目的 GitHub Issues。
