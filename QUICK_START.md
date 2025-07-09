# PLTHook 快速上手指南

## 项目概述

PLTHook 是一个跨平台的函数钩取库，可以拦截和修改动态链接库中的函数调用。本项目已经为 Windows 和 Android 平台提供了完整的构建解决方案。

## 快速开始

### Windows 平台构建

**前提条件**:
- Visual Studio 2019 或更高版本
- Windows 10/11
- PowerShell 5.1+

**构建步骤**:
```powershell
# 1. 克隆或下载项目
cd c:\path\to\plthook

# 2. 构建 x64 版本
.\build_windows.ps1 -Platform windows -Architecture x64

# 3. 查看构建结果
ls .\output\windows\x64\
```

**预期输出**:
- `libtest.dll` - 测试共享库
- `libtest.lib` - 导入库
- `testprog.exe` - 测试程序

**运行测试**:
```powershell
cd .\output\windows\x64\
.\testprog.exe open
.\testprog.exe open_by_handle
```

### Android 平台构建

**前提条件**:
- Android NDK r21+
- CMake 3.16+
- Linux/macOS/WSL 环境

**使用 NDK-Build**:
```bash
# 1. 设置 NDK 路径
export ANDROID_NDK_ROOT=/path/to/android-ndk

# 2. 进入 Android 项目目录
cd test/android

# 3. 构建
$ANDROID_NDK_ROOT/ndk-build clean
$ANDROID_NDK_ROOT/ndk-build

# 4. 查看结果
ls libs/
```

**使用 CMake (推荐)**:
```bash
# 1. 创建构建目录
mkdir build-android && cd build-android

# 2. 配置 CMake
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake \
    -DANDROID_ABI=arm64-v8a \
    -DANDROID_PLATFORM=android-21 \
    -DBUILD_TESTS=ON

# 3. 构建
make -j$(nproc)
```

## 使用示例

### 基本钩取示例

```c
#include <plthook.h>
#include <stdio.h>

// 原始函数指针
static int (*original_function)(int) = NULL;

// 钩子函数
static int hook_function(int arg) {
    printf("函数被调用，参数: %d\n", arg);
    return original_function(arg);
}

int main() {
    plthook_t *plthook;
    
    // 打开目标库
    if (plthook_open(&plthook, "target_library.so") != 0) {
        fprintf(stderr, "错误: %s\n", plthook_error());
        return 1;
    }
    
    // 替换函数
    if (plthook_replace(plthook, "target_function", 
                       (void*)hook_function, 
                       (void**)&original_function) != 0) {
        fprintf(stderr, "错误: %s\n", plthook_error());
        plthook_close(plthook);
        return 1;
    }
    
    // 清理
    plthook_close(plthook);
    return 0;
}
```

### 编译示例

**Windows**:
```cmd
cl /I. your_program.c plthook_win32.c /link dbghelp.lib
```

**Linux**:
```bash
gcc -I. -o your_program your_program.c plthook_elf.c -ldl
```

**Android**:
```bash
$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang \
    -I. -o your_program your_program.c plthook_elf.c -ldl
```

## 项目结构

```
plthook/
├── plthook.h              # 公共头文件
├── plthook_win32.c        # Windows 实现
├── plthook_elf.c          # Linux/Android 实现
├── plthook_osx.c          # macOS 实现
├── build_windows.ps1      # Windows 构建脚本
├── build.sh               # 跨平台构建脚本
├── CMakeLists.txt         # CMake 构建文件
├── release_builder.py     # 发布构建工具
├── test/                  # 测试程序
│   ├── testprog.c         # 测试程序源码
│   ├── libtest.c          # 测试库源码
│   ├── Makefile           # Unix Makefile
│   ├── Makefile.win32     # Windows Makefile
│   └── android/           # Android 专用配置
└── examples/              # 示例程序
    └── malloc_hook.c      # malloc 钩取示例
```

## 构建选项

### 所有平台支持的架构

| 平台 | 支持的架构 | 状态 |
|------|------------|------|
| Windows | x86, x64, ARM64 | ✅ 已验证 |
| Linux | x86_64, ARM64, ARMv7 | 🔄 准备就绪 |
| macOS | x86_64, ARM64 | 🔄 准备就绪 |
| Android | ARM64, ARMv7, x86_64 | 🔄 准备就绪 |

### 构建类型

- **Debug**: 包含调试信息，未优化
- **Release**: 优化版本，适合生产环境
- **RelWithDebInfo**: 优化 + 调试信息

### CMake 选项

```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \     # 构建类型
    -DBUILD_SHARED_LIBS=ON \         # 构建共享库
    -DBUILD_TESTS=ON \               # 构建测试程序
    -DBUILD_ANDROID=ON               # Android 特定选项
```

## 常见用途

### 1. 函数调用监控
监控特定函数的调用频率、参数和返回值。

### 2. 性能分析
测量函数执行时间，识别性能瓶颈。

### 3. 调试辅助
在不修改源码的情况下添加调试输出。

### 4. 安全研究
分析程序行为，检测恶意活动。

### 5. 兼容性处理
为旧版本 API 提供新的实现。

## 注意事项

### 安全考虑
- 钩取系统函数可能需要特殊权限
- 某些防病毒软件可能阻止钩取行为
- 在生产环境中使用需要充分测试

### 性能影响
- 每次函数调用都会增加一次间接跳转的开销
- 钩子函数的复杂性直接影响性能
- 建议对性能敏感的代码谨慎使用

### 兼容性
- Windows 平台不支持 `open_by_address` 模式
- Android 现代版本对动态链接有更严格的限制
- 静态链接的函数无法通过 PLT/IAT 钩取

## 故障排除

### 常见错误

**"plthook_open error: file not found"**
- 检查库文件路径是否正确
- 确认目标库已加载到进程中

**"plthook_replace error: function not found"**
- 确认函数名称正确（注意 C++ 名称修饰）
- 检查函数是否通过动态链接

**"Access denied" 或权限错误**
- 以管理员权限运行程序
- 检查目标进程的安全设置

### 调试技巧

1. **使用日志**: 在钩子函数中添加详细的日志输出
2. **检查返回值**: 始终检查 PLTHook API 的返回值
3. **函数枚举**: 使用 `plthook_enum` 列出所有可用函数
4. **分步测试**: 先测试简单函数，再处理复杂场景

## 获取帮助

- 查看 `BUILD_GUIDE.md` 获取详细构建说明
- 查看 `examples/` 目录获取更多示例
- 查看测试程序了解 API 使用方法
- 访问项目 GitHub 页面获取最新信息

## 许可证

本项目采用 BSD-2-Clause 许可证。详见 LICENSE 文件。
